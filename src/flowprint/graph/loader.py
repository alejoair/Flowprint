from __future__ import annotations

import ray

from flowprint.core.node import Node
from flowprint.core.ray_context import RayContextProxy, _ContextActor
from flowprint.engine import Engine
from flowprint.graph.registry import NODE_REGISTRY
from flowprint.graph.schema import Graph
from flowprint.graph.validation import validate_graph


def _ensure_ray() -> None:
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)


def build_engine(graph: Graph, on_event=None) -> Engine:
    errors = validate_graph(graph)
    if errors:
        raise ValueError("Grafo inválido:\n  - " + "\n  - ".join(errors))

    nodes: dict[str, Node] = {}
    input_names = list(graph.signature.inputs.keys())
    output_names = list(graph.signature.outputs.keys())
    for inst in graph.instances:
        cls = NODE_REGISTRY[inst.type]
        config = dict(inst.config)
        if inst.type == "Start":
            config.setdefault("input_names", input_names)
        elif inst.type == "End":
            config.setdefault("output_names", output_names)
        nodes[inst.id] = cls(inst.id, config)

    exec_edges = [
        (c.from_node, c.from_pin, c.to_node, c.to_pin)
        for c in graph.exec_connections()
    ]
    data_edges = [
        (c.from_node, c.from_pin, c.to_node, c.to_pin)
        for c in graph.data_connections()
    ]

    _ensure_ray()
    actor = _ContextActor.remote()
    ctx = RayContextProxy(actor)
    return Engine(nodes, exec_edges, data_edges, on_event=on_event, ctx=ctx)


def find_start(graph: Graph) -> str:
    starts = [i.id for i in graph.instances if i.type == "Start"]
    if len(starts) != 1:
        raise ValueError(f"El grafo debe tener exactamente un Start; encontrados: {starts}")
    return starts[0]


async def run_graph(graph: Graph | dict, args: dict | None = None):
    if isinstance(graph, dict):
        graph = Graph.model_validate(graph)
    engine = build_engine(graph)
    return await engine.run(find_start(graph), args)
