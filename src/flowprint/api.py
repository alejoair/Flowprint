from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from flowprint.graph.loader import build_engine, find_start, run_graph
from flowprint.graph.registry import (
    BUILTIN_NODE_NAMES,
    CUSTOM_NODES_DIR,
    NODE_REGISTRY,
    refresh_custom_nodes,
)
from flowprint.graph.schema import Graph
from flowprint.graph.validation import SAFE_CONVERSIONS, validate_graph

app = FastAPI(title="Flowprint API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GRAPHS_DIR: Path = Path.cwd() / "graphs"


def _type_name(t: Any) -> str:
    return getattr(t, "__name__", str(t)) if t is not None else "Any"


# ---------------------------------------------------------------------------
# Catálogo de nodos
# ---------------------------------------------------------------------------


@app.get("/nodes")
def list_nodes():
    result = []
    for name, cls in NODE_REGISTRY.items():
        d = cls.describe()
        result.append({
            "type": d["type"],
            "is_pure": d["is_pure"],
            "data_inputs": {k: _type_name(v) for k, v in d["data_inputs"].items()},
            "data_outputs": {k: _type_name(v) for k, v in d["data_outputs"].items()},
            "exec_inputs": list(d["exec_inputs"]),
            "exec_outputs": list(d["exec_outputs"]),
            "is_custom": name not in BUILTIN_NODE_NAMES,
        })
    return result


# ---------------------------------------------------------------------------
# CRUD de custom nodes
# ---------------------------------------------------------------------------


class NodeSource(BaseModel):
    source: str


def _node_path(name: str) -> Path:
    if not name.isidentifier():
        raise HTTPException(400, f"Nombre de nodo inválido: '{name}'.")
    return CUSTOM_NODES_DIR / f"{name}.py"


def _parse_source(source: str):
    try:
        ast.parse(source)
    except SyntaxError as e:
        raise HTTPException(422, f"Error de sintaxis en línea {e.lineno}: {e.msg}")


@app.get("/nodes/custom")
def list_custom_nodes():
    if not CUSTOM_NODES_DIR.exists():
        return []
    return [
        {"name": f.stem, "source": f.read_text()}
        for f in sorted(CUSTOM_NODES_DIR.glob("*.py"))
        if not f.name.startswith("_")
    ]


@app.get("/nodes/custom/{name}")
def get_custom_node(name: str):
    path = _node_path(name)
    if not path.exists():
        raise HTTPException(404, f"Nodo '{name}' no encontrado.")
    return {"name": name, "source": path.read_text()}


@app.post("/nodes/custom/{name}", status_code=201)
def create_custom_node(name: str, body: NodeSource):
    path = _node_path(name)
    if path.exists():
        raise HTTPException(409, f"Ya existe un nodo con el nombre '{name}'.")
    _parse_source(body.source)
    CUSTOM_NODES_DIR.mkdir(exist_ok=True)
    path.write_text(body.source)
    loaded = refresh_custom_nodes()
    return {"registered": list(loaded.keys())}


@app.put("/nodes/custom/{name}")
def update_custom_node(name: str, body: NodeSource):
    path = _node_path(name)
    if not path.exists():
        raise HTTPException(404, f"Nodo '{name}' no encontrado.")
    _parse_source(body.source)
    path.write_text(body.source)
    loaded = refresh_custom_nodes()
    return {"registered": list(loaded.keys())}


@app.delete("/nodes/custom/{name}", status_code=204)
def delete_custom_node(name: str):
    path = _node_path(name)
    if not path.exists():
        raise HTTPException(404, f"Nodo '{name}' no encontrado.")
    path.unlink()
    refresh_custom_nodes()


# ---------------------------------------------------------------------------
# Compatibilidad de tipos
# ---------------------------------------------------------------------------


@app.get("/types/compatibility")
def type_compatibility():
    return [
        {"from": _type_name(src), "to": _type_name(dst), "converter": conv}
        for (src, dst), conv in SAFE_CONVERSIONS.items()
    ]


# ---------------------------------------------------------------------------
# CRUD de grafos persistidos
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _graph_path(name: str) -> Path:
    if not _SLUG_RE.match(name):
        raise HTTPException(
            400,
            f"Nombre de grafo inválido: '{name}'. "
            "Usa solo letras minúsculas, números, guiones y guiones bajos."
        )
    return GRAPHS_DIR / f"{name}.json"


def _load_graph_file(name: str) -> dict:
    path = _graph_path(name)
    if not path.exists():
        raise HTTPException(404, f"Grafo '{name}' no encontrado.")
    return json.loads(path.read_text())


class SaveGraphRequest(BaseModel):
    graph: dict


@app.get("/graphs")
def list_graphs():
    if not GRAPHS_DIR.exists():
        return []
    return [
        {"name": f.stem}
        for f in sorted(GRAPHS_DIR.glob("*.json"))
    ]


@app.get("/graphs/{name}")
def get_graph(name: str):
    return _load_graph_file(name)


@app.post("/graphs/{name}", status_code=201)
def create_graph(name: str, body: SaveGraphRequest):
    path = _graph_path(name)
    if path.exists():
        raise HTTPException(409, f"Ya existe un grafo con el nombre '{name}'.")
    try:
        Graph.model_validate(body.graph)
    except Exception as e:
        raise HTTPException(422, str(e))
    GRAPHS_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps({"name": name, "graph": body.graph}, indent=2))
    return {"name": name}


@app.put("/graphs/{name}")
def update_graph(name: str, body: SaveGraphRequest):
    path = _graph_path(name)
    if not path.exists():
        raise HTTPException(404, f"Grafo '{name}' no encontrado.")
    try:
        Graph.model_validate(body.graph)
    except Exception as e:
        raise HTTPException(422, str(e))
    path.write_text(json.dumps({"name": name, "graph": body.graph}, indent=2))
    return {"name": name}


@app.delete("/graphs/{name}", status_code=204)
def delete_graph(name: str):
    path = _graph_path(name)
    if not path.exists():
        raise HTTPException(404, f"Grafo '{name}' no encontrado.")
    path.unlink()


# ---------------------------------------------------------------------------
# Ejecución de grafo inline (canvas abierto)
# ---------------------------------------------------------------------------


class ValidateRequest(BaseModel):
    graph: dict


class RunRequest(BaseModel):
    graph: dict
    args: dict | None = None


@app.post("/graph/validate")
def validate(req: ValidateRequest):
    try:
        graph = Graph.model_validate(req.graph)
    except Exception as e:
        return {"errors": [str(e)]}
    return {"errors": validate_graph(graph)}


@app.websocket("/graph/run/ws")
async def run_ws(ws: WebSocket):
    """Ejecuta un grafo inline (enviado en el mensaje) via WebSocket."""
    await ws.accept()
    try:
        payload = await ws.receive_json()
    except WebSocketDisconnect:
        return
    await _execute_ws(ws, payload.get("graph", {}), payload.get("args"))


# ---------------------------------------------------------------------------
# Ejecución de grafo guardado por nombre
# ---------------------------------------------------------------------------


@app.websocket("/graphs/{name}/run/ws")
async def run_saved_ws(name: str, ws: WebSocket):
    """Ejecuta un grafo guardado. El cliente solo envía { args: {...} }."""
    await ws.accept()
    try:
        payload = await ws.receive_json()
    except WebSocketDisconnect:
        return
    try:
        stored = _load_graph_file(name)
    except HTTPException as e:
        await ws.send_json({"event": "error", "error": e.detail})
        await ws.close()
        return
    await _execute_ws(ws, stored["graph"], payload.get("args"))


@app.post("/graphs/{name}/run")
async def run_saved(name: str, body: dict | None = None):
    """Ejecuta un grafo guardado y devuelve el resultado final."""
    stored = _load_graph_file(name)
    try:
        graph = Graph.model_validate(stored["graph"])
    except Exception as e:
        raise HTTPException(422, str(e))
    try:
        return await run_graph(graph, (body or {}).get("args"))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# Helper compartido de ejecución WebSocket
# ---------------------------------------------------------------------------


async def _execute_ws(ws: WebSocket, graph_dict: dict, args: dict | None):
    try:
        graph = Graph.model_validate(graph_dict)
    except Exception as e:
        await ws.send_json({"event": "error", "error": str(e)})
        await ws.close()
        return

    try:
        engine = build_engine(graph)
    except ValueError as e:
        await ws.send_json({"event": "error", "error": str(e)})
        await ws.close()
        return

    async def on_event(event: dict) -> None:
        try:
            await ws.send_json(event)
        except Exception:
            engine.cancel()

    engine._on_event = on_event

    try:
        await engine.run(find_start(graph), args)
    except Exception as e:
        await ws.send_json({"event": "error", "error": repr(e)})
    finally:
        await ws.close()
