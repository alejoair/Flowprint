from __future__ import annotations

import ray

from flowprint.core.context import ContextProtocol, LocalContext
from flowprint.core.control import Fork, Goto, Repeat, Stop
from flowprint.core.node import Node


class Engine:
    def __init__(
        self,
        nodes: dict[str, Node],
        exec_edges: list,
        data_edges: list,
        on_event=None,
        ctx: ContextProtocol | None = None,
    ) -> None:
        self.nodes = nodes
        self.exec_edges = exec_edges
        self.data_edges = data_edges
        self.ctx: ContextProtocol = ctx if ctx is not None else LocalContext()
        self._on_event = on_event   # async callable(dict) | None
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
        if hasattr(self.ctx, "_actor"):
            ray.get(self.ctx._actor.set_cancelled.remote())

    async def _emit(self, event: dict) -> None:
        if self._on_event:
            await self._on_event(event)

    async def _resolve_inputs(self, node_id: str) -> dict:
        values = {}
        for (fn, fp, tn, tp) in self.data_edges:
            if tn == node_id:
                values[tp] = await self._produce_output(fn, fp)
        return values

    async def _produce_output(self, node_id: str, pin: str):
        node = self.nodes[node_id]
        if node.is_pure:
            sub = await self._resolve_inputs(node_id)
            res = await node.execute(node.Inputs(**sub), self.ctx)
            return getattr(res.data, pin)
        produced = await self.ctx.get_node_output(node_id)
        return getattr(produced, pin) if produced is not None else None

    def _targets(self, node_id: str, pins: list[str]) -> list[str]:
        out = []
        for pin in pins:
            for (fn, fp, tn, tp) in self.exec_edges:
                if fn == node_id and fp == pin:
                    out.append(tn)
        return out

    async def run(self, start_id: str, args: dict | None = None):
        if args:
            await self.ctx.set_var("__args__", args)
        stack = [start_id]
        while stack:
            if self._cancelled:
                await self._emit({"event": "cancelled"})
                return {"__cancelled__": True}

            node_id = stack.pop()
            node = self.nodes[node_id]

            await self._emit({"event": "node_start", "node": node_id})
            try:
                inputs = await self._resolve_inputs(node_id)
                result = await node.execute(node.Inputs(**inputs), self.ctx)
            except Exception as exc:
                error = {"node": node_id, "error": repr(exc)}
                await self.ctx.set_var("__error__", error)
                await self._emit({"event": "error", **error})
                return {"__error__": error}

            await self.ctx.set_node_output(node_id, result.data)
            await self._emit({
                "event": "node_complete",
                "node": node_id,
                "outputs": result.data.model_dump(),
            })

            ctrl = result.control
            if isinstance(ctrl, Stop):
                continue
            elif isinstance(ctrl, Goto):
                for nxt in reversed(self._targets(node_id, ctrl.pins)):
                    stack.append(nxt)
            elif isinstance(ctrl, Repeat):
                stack.append(node_id)
                for nxt in reversed(self._targets(node_id, ctrl.pins)):
                    stack.append(nxt)
            elif isinstance(ctrl, Fork):
                for nxt in reversed(self._targets(node_id, ctrl.pins)):
                    stack.append(nxt)

        result = await self.ctx.get_var("__result__")
        await self._emit({"event": "graph_complete", "result": result})
        return result
