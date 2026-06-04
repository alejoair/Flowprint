from __future__ import annotations

import json
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from flowprint.graph.loader import build_engine, find_start, run_graph
from flowprint.graph.schema import Graph
from flowprint.graph.validation import validate_graph

router = APIRouter()

GRAPHS_DIR: Path = Path.cwd() / "graphs"
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _graph_path(name: str) -> Path:
    if not _SLUG_RE.match(name):
        raise HTTPException(
            400,
            f"Nombre de grafo inválido: '{name}'. "
            "Usa solo letras minúsculas, números, guiones y guiones bajos.",
        )
    return GRAPHS_DIR / f"{name}.json"


def _load_graph_file(name: str) -> dict:
    path = _graph_path(name)
    if not path.exists():
        raise HTTPException(404, f"Grafo '{name}' no encontrado.")
    return json.loads(path.read_text())


def _parse_graph(graph_dict: dict) -> Graph:
    try:
        return Graph.model_validate(graph_dict)
    except Exception as e:
        raise HTTPException(422, str(e))


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class SaveGraphRequest(BaseModel):
    graph: dict


class ValidateRequest(BaseModel):
    graph: dict


class RunRequest(BaseModel):
    graph: dict
    args: dict | None = None


# ---------------------------------------------------------------------------
# Graph CRUD
# ---------------------------------------------------------------------------


@router.get("/graphs")
def list_graphs():
    if not GRAPHS_DIR.exists():
        return []
    return [{"name": f.stem} for f in sorted(GRAPHS_DIR.glob("*.json"))]


@router.get("/graphs/{name}")
def get_graph(name: str):
    return _load_graph_file(name)


@router.post("/graphs/{name}", status_code=201)
def create_graph(name: str, body: SaveGraphRequest):
    path = _graph_path(name)
    if path.exists():
        raise HTTPException(409, f"Ya existe un grafo con el nombre '{name}'.")
    _parse_graph(body.graph)
    GRAPHS_DIR.mkdir(exist_ok=True)
    path.write_text(json.dumps({"name": name, "graph": body.graph}, indent=2))
    return {"name": name}


@router.put("/graphs/{name}")
def update_graph(name: str, body: SaveGraphRequest):
    path = _graph_path(name)
    if not path.exists():
        raise HTTPException(404, f"Grafo '{name}' no encontrado.")
    _parse_graph(body.graph)
    path.write_text(json.dumps({"name": name, "graph": body.graph}, indent=2))
    return {"name": name}


@router.delete("/graphs/{name}", status_code=204)
def delete_graph(name: str):
    path = _graph_path(name)
    if not path.exists():
        raise HTTPException(404, f"Grafo '{name}' no encontrado.")
    path.unlink()


# ---------------------------------------------------------------------------
# Inline graph execution  (/graph/*)
# ---------------------------------------------------------------------------


@router.post("/graph/validate")
def graph_validate(req: ValidateRequest):
    try:
        graph = Graph.model_validate(req.graph)
    except Exception as e:
        return {"errors": [str(e)]}
    return {"errors": validate_graph(graph)}


@router.post("/graph/run")
async def graph_run(req: RunRequest):
    graph = _parse_graph(req.graph)
    try:
        return await run_graph(graph, req.args)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.websocket("/graph/run/ws")
async def graph_run_ws(ws: WebSocket):
    await ws.accept()
    try:
        payload = await ws.receive_json()
    except WebSocketDisconnect:
        return
    await _execute_ws(ws, payload.get("graph", {}), payload.get("args"))


# ---------------------------------------------------------------------------
# Saved graph execution  (/graphs/{name}/run*)
# ---------------------------------------------------------------------------


@router.post("/graphs/{name}/run")
async def saved_graph_run(name: str, body: dict | None = None):
    stored = _load_graph_file(name)
    graph = _parse_graph(stored["graph"])
    try:
        return await run_graph(graph, (body or {}).get("args"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.websocket("/graphs/{name}/run/ws")
async def saved_graph_run_ws(name: str, ws: WebSocket):
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


# ---------------------------------------------------------------------------
# Shared WebSocket execution helper
# ---------------------------------------------------------------------------


async def _execute_ws(ws: WebSocket, graph_dict: dict, args: dict | None) -> None:
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
