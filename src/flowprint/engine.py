from __future__ import annotations

from flowprint.core.control import Fork, Goto, Repeat, Stop
from flowprint.core.node import ExecutionContext, Node


class Engine:
    def __init__(self, nodes: dict[str, Node], exec_edges: list, data_edges: list) -> None:
        self.nodes = nodes
        self.exec_edges = exec_edges
        self.data_edges = data_edges
        self.ctx = ExecutionContext()

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
        produced = self.ctx.node_state(node_id).get("__out__")
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
            self.ctx.set_var("__args__", args)
        stack = [start_id]
        while stack:
            node_id = stack.pop()
            node = self.nodes[node_id]
            try:
                inputs = await self._resolve_inputs(node_id)
                result = await node.execute(node.Inputs(**inputs), self.ctx)
            except Exception as exc:
                self.ctx.set_var("__error__", {"node": node_id, "error": repr(exc)})
                return {"__error__": {"node": node_id, "error": repr(exc)}}
            self.ctx.node_state(node_id)["__out__"] = result.data

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
        return self.ctx.get_var("__result__")
