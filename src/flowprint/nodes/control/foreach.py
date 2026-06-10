from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.context import ContextProtocol
from flowprint.core.control import Goto, Repeat
from flowprint.core.node import Node, NodeResult


class ForEach(Node):
    """Itera sobre la lista en la variable 'foreach_items'. Activa 'body' por cada elemento, luego 'completed'. Usa ItemOf para leer el elemento actual."""
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("body", "completed")
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ContextProtocol) -> NodeResult:
        st = await ctx.get_node_state(self.instance_id)
        if "items" not in st:
            items = await ctx.get_var("foreach_items") or []
            await ctx.update_node_state(self.instance_id, {"items": items, "idx": 0})
            st = {"items": items, "idx": 0}
        idx, items = st["idx"], st["items"]
        if idx < len(items):
            await ctx.update_node_state(self.instance_id, {"current": items[idx], "idx": idx + 1})
            return NodeResult(self.Outputs(), Repeat(["body"]))
        return NodeResult(self.Outputs(), Goto(["completed"]))
