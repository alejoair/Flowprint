"""Tests para Fork/Parallel: ejecución paralela real con Ray."""
from __future__ import annotations

import tempfile
from pathlib import Path

from flowprint.graph.loader import build_engine, find_start
from flowprint.graph.schema import Graph


def _parallel_graph(n: int = 2) -> dict:
    """Grafo: Start → Parallel → N ramas AgentEcho independientes."""
    instances = [
        {"id": "start", "type": "Start", "config": {}},
        {"id": "par", "type": "Parallel", "config": {"n": n}},
    ]
    connections = [
        {"kind": "exec", "from_node": "start", "from_pin": "out", "to_node": "par", "to_pin": "in"},
    ]
    for i in range(1, n + 1):
        agent_id = f"ag{i}"
        const_id = f"c{i}"
        end_id = f"end{i}"
        instances += [
            {"id": agent_id, "type": "AgentEcho", "config": {}},
            {"id": const_id, "type": "Const", "config": {"value": f"rama{i}"}},
            {"id": end_id, "type": "End", "config": {}},
        ]
        connections += [
            {"kind": "exec", "from_node": "par", "from_pin": str(i), "to_node": agent_id, "to_pin": "in"},
            {"kind": "exec", "from_node": agent_id, "from_pin": "out", "to_node": end_id, "to_pin": "in"},
            {"kind": "data", "from_node": const_id, "from_pin": "value", "to_node": agent_id, "to_pin": "text"},
        ]
    return {
        "schema_version": "1.0",
        "signature": {"inputs": {}, "outputs": {}},
        "variables": [],
        "instances": instances,
        "connections": connections,
        "visual": {"positions": {}, "zoom": 1.0},
    }


async def test_parallel_dos_ramas():
    graph = Graph.model_validate(_parallel_graph(2))
    engine = build_engine(graph)
    await engine.run(find_start(graph))
    log = await engine.ctx.get_node_state("__log__")
    calls = set(log.get("calls", []))
    assert calls == {"agent(rama1)", "agent(rama2)"}


async def test_parallel_tres_ramas():
    graph = Graph.model_validate(_parallel_graph(3))
    engine = build_engine(graph)
    await engine.run(find_start(graph))
    log = await engine.ctx.get_node_state("__log__")
    calls = set(log.get("calls", []))
    assert calls == {"agent(rama1)", "agent(rama2)", "agent(rama3)"}


async def test_parallel_emite_eventos():
    """Verifica que los eventos de branches paralelas llegan al on_event del engine."""
    eventos = []

    async def capturar(event):
        eventos.append(event)

    graph = Graph.model_validate(_parallel_graph(2))
    engine = build_engine(graph, on_event=capturar)
    await engine.run(find_start(graph))

    tipos = [e["event"] for e in eventos]
    assert "node_start" in tipos
    assert "node_complete" in tipos
    assert "graph_complete" in tipos
    # Las dos ramas deben haber emitido node_complete para sus AgentEcho
    agent_completes = [e for e in eventos if e.get("event") == "node_complete" and e.get("node", "").startswith("ag")]
    assert len(agent_completes) == 2


async def test_custom_node_en_parallel():
    """Custom node definido en custom_nodes/ funciona dentro de una rama Fork."""
    custom_src = """\
from pydantic import BaseModel
from flowprint.core.context import ContextProtocol
from flowprint.core.control import Goto
from flowprint.core.node import Node, NodeResult

class MiNodoCustom(Node):
    class Inputs(BaseModel):
        text: str
    class Outputs(BaseModel):
        reply: str
    exec_inputs = ("in",)
    exec_outputs = ("out",)
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ContextProtocol) -> NodeResult:
        await ctx.append_to_list("__log__", "calls", f"custom({inputs.text})")
        return NodeResult(self.Outputs(reply=f"custom:{inputs.text}"), Goto(["out"]))
"""
    with tempfile.TemporaryDirectory() as tmp:
        custom_dir = Path(tmp) / "custom_nodes"
        custom_dir.mkdir()
        (custom_dir / "mi_nodo.py").write_text(custom_src)

        # Cargar el nodo custom en el proceso principal
        from flowprint.graph.registry import load_custom_nodes, NODE_REGISTRY
        load_custom_nodes(custom_dir)
        assert "MiNodoCustom" in NODE_REGISTRY

        graph_dict = {
            "schema_version": "1.0",
            "signature": {"inputs": {}, "outputs": {}},
            "variables": [],
            "instances": [
                {"id": "start", "type": "Start", "config": {}},
                {"id": "par", "type": "Parallel", "config": {"n": 2}},
                {"id": "c1", "type": "Const", "config": {"value": "hola"}},
                {"id": "custom1", "type": "MiNodoCustom", "config": {}},
                {"id": "end1", "type": "End", "config": {}},
                {"id": "c2", "type": "Const", "config": {"value": "mundo"}},
                {"id": "ag2", "type": "AgentEcho", "config": {}},
                {"id": "end2", "type": "End", "config": {}},
            ],
            "connections": [
                {"kind": "exec", "from_node": "start", "from_pin": "out", "to_node": "par", "to_pin": "in"},
                {"kind": "exec", "from_node": "par", "from_pin": "1", "to_node": "custom1", "to_pin": "in"},
                {"kind": "exec", "from_node": "custom1", "from_pin": "out", "to_node": "end1", "to_pin": "in"},
                {"kind": "exec", "from_node": "par", "from_pin": "2", "to_node": "ag2", "to_pin": "in"},
                {"kind": "exec", "from_node": "ag2", "from_pin": "out", "to_node": "end2", "to_pin": "in"},
                {"kind": "data", "from_node": "c1", "from_pin": "value", "to_node": "custom1", "to_pin": "text"},
                {"kind": "data", "from_node": "c2", "from_pin": "value", "to_node": "ag2", "to_pin": "text"},
            ],
            "visual": {"positions": {}, "zoom": 1.0},
        }

        # Usar el directorio temporal como custom_nodes_dir para el worker
        import flowprint.graph.registry as reg
        original_dir = reg.CUSTOM_NODES_DIR
        reg.CUSTOM_NODES_DIR = custom_dir
        try:
            graph = Graph.model_validate(graph_dict)
            engine = build_engine(graph)
            await engine.run(find_start(graph))
        finally:
            reg.CUSTOM_NODES_DIR = original_dir
            # Limpiar el nodo custom del registry
            NODE_REGISTRY.pop("MiNodoCustom", None)

    log = await engine.ctx.get_node_state("__log__")
    calls = set(log.get("calls", []))
    assert "custom(hola)" in calls
    assert "agent(mundo)" in calls
