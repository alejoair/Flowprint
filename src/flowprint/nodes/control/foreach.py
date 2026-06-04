from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Goto, Repeat
from flowprint.core.node import ExecutionContext, Node, NodeResult


class ForEach(Node):
    """Itera sobre la lista en la variable 'foreach_items'. Activa 'body' por cada elemento, luego 'completed'. Usa ItemOf para leer el elemento actual."""
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("body", "completed")
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        st = ctx.node_state(self.instance_id)
        if "items" not in st:
            st["items"] = ctx.get_var("foreach_items") or []
            st["idx"] = 0
        idx, items = st["idx"], st["items"]
        if idx < len(items):
            st["current"] = items[idx]
            st["idx"] = idx + 1
            return NodeResult(self.Outputs(), Repeat(["body"]))
        return NodeResult(self.Outputs(), Goto(["completed"]))
