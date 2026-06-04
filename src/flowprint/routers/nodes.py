from __future__ import annotations

import ast
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from flowprint.graph.registry import (
    BUILTIN_NODE_NAMES,
    CUSTOM_NODES_DIR,
    NODE_REGISTRY,
    refresh_custom_nodes,
)
from flowprint.graph.validation import SAFE_CONVERSIONS

router = APIRouter()


def _type_name(t: Any) -> str:
    return getattr(t, "__name__", str(t)) if t is not None else "Any"


def _node_path(name: str):
    if not name.isidentifier():
        raise HTTPException(400, f"Nombre de nodo inválido: '{name}'.")
    return CUSTOM_NODES_DIR / f"{name}.py"


def _parse_source(source: str) -> None:
    try:
        ast.parse(source)
    except SyntaxError as e:
        raise HTTPException(422, f"Error de sintaxis en línea {e.lineno}: {e.msg}")


class NodeSource(BaseModel):
    source: str


@router.get("/nodes")
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


@router.get("/nodes/custom")
def list_custom_nodes():
    if not CUSTOM_NODES_DIR.exists():
        return []
    return [
        {"name": f.stem, "source": f.read_text()}
        for f in sorted(CUSTOM_NODES_DIR.glob("*.py"))
        if not f.name.startswith("_")
    ]


@router.get("/nodes/custom/{name}")
def get_custom_node(name: str):
    path = _node_path(name)
    if not path.exists():
        raise HTTPException(404, f"Nodo '{name}' no encontrado.")
    return {"name": name, "source": path.read_text()}


@router.post("/nodes/custom/{name}", status_code=201)
def create_custom_node(name: str, body: NodeSource):
    path = _node_path(name)
    if path.exists():
        raise HTTPException(409, f"Ya existe un nodo con el nombre '{name}'.")
    _parse_source(body.source)
    CUSTOM_NODES_DIR.mkdir(exist_ok=True)
    path.write_text(body.source)
    loaded = refresh_custom_nodes()
    return {"registered": list(loaded.keys())}


@router.put("/nodes/custom/{name}")
def update_custom_node(name: str, body: NodeSource):
    path = _node_path(name)
    if not path.exists():
        raise HTTPException(404, f"Nodo '{name}' no encontrado.")
    _parse_source(body.source)
    path.write_text(body.source)
    loaded = refresh_custom_nodes()
    return {"registered": list(loaded.keys())}


@router.delete("/nodes/custom/{name}", status_code=204)
def delete_custom_node(name: str):
    path = _node_path(name)
    if not path.exists():
        raise HTTPException(404, f"Nodo '{name}' no encontrado.")
    path.unlink()
    refresh_custom_nodes()


@router.get("/types/compatibility")
def type_compatibility():
    return [
        {"from": _type_name(src), "to": _type_name(dst), "converter": conv}
        for (src, dst), conv in SAFE_CONVERSIONS.items()
    ]
