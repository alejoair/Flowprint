from __future__ import annotations

import ast
import asyncio
import json
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
# Grafo: validación y ejecución
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


@app.post("/graph/run")
async def run(req: RunRequest):
    try:
        graph = Graph.model_validate(req.graph)
    except Exception as e:
        raise HTTPException(422, str(e))
    try:
        result = await run_graph(graph, req.args)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@app.post("/graph/run/stream")
async def run_stream(req: RunRequest):
    """Ejecuta el grafo y emite cada evento como SSE (text/event-stream)."""
    try:
        graph = Graph.model_validate(req.graph)
    except Exception as e:
        raise HTTPException(422, str(e))

    try:
        engine = build_engine(graph)
    except ValueError as e:
        raise HTTPException(400, str(e))

    queue: asyncio.Queue = asyncio.Queue()

    async def on_event(event: dict) -> None:
        await queue.put(event)

    engine._on_event = on_event

    async def generate() -> AsyncGenerator[str, None]:
        task = asyncio.create_task(engine.run(find_start(graph), req.args))
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("event") in ("graph_complete", "error", "cancelled"):
                    break
            except asyncio.TimeoutError:
                if task.done():
                    break
        await task

    return StreamingResponse(generate(), media_type="text/event-stream")
