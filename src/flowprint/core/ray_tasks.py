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
) -> None:
    """Execute one Fork branch as a Ray task, sharing the parent's context actor.

    Events are pushed directly to the actor's event queue instead of being
    returned, so nested forks and deeply-pipelined branches all funnel through
    the same queue without extra coordination.
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

    ctx = RayContextProxy(actor_handle)

    async def on_event(event: dict) -> None:
        await ctx.push_event(event)

    engine = Engine(nodes, exec_edges, data_edges, ctx=ctx, on_event=on_event)
    asyncio.run(engine.run(start_id))
