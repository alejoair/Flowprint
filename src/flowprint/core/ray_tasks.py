from __future__ import annotations

import asyncio
from pathlib import Path

import ray

from flowprint.graph.registry import NODE_REGISTRY


@ray.remote
def run_branch(
    nodes_serialised: dict[str, tuple[str, str, dict]],
    exec_edges: list,
    data_edges: list,
    start_id: str,
    actor_handle: ray.actor.ActorHandle,
    custom_nodes_dir: str | None,
) -> list[dict]:
    """Execute one Fork branch as a Ray task, sharing the parent's context actor.

    Returns the list of events emitted during execution so the parent engine
    can re-emit them in order after all branches complete.
    """
    from flowprint.core.ray_context import RayContextProxy
    from flowprint.engine import Engine
    from flowprint.graph.registry import NODE_REGISTRY, load_custom_nodes

    if custom_nodes_dir:
        load_custom_nodes(Path(custom_nodes_dir))

    nodes = {}
    for nid, (type_name, instance_id, config) in nodes_serialised.items():
        cls = NODE_REGISTRY[type_name]
        nodes[nid] = cls(instance_id, config)

    events: list[dict] = []

    async def on_event(event: dict) -> None:
        events.append(event)

    ctx = RayContextProxy(actor_handle)
    engine = Engine(nodes, exec_edges, data_edges, ctx=ctx, on_event=on_event)

    asyncio.run(engine.run(start_id))
    return events
