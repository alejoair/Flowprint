from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.context import ContextProtocol
from flowprint.core.control import Goto, Repeat
from flowprint.core.node import Node, NodeResult


class ForLoop(Node):
    """Itera de start a end-1 (exclusive). Emite el índice actual por el pin 'index' en cada vuelta del 'body'."""
    class Inputs(BaseModel):
        start: int = 0
        end: int

    class Outputs(BaseModel):
        index: int = 0

    exec_inputs = ("in",)
    exec_outputs = ("body", "completed")
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ContextProtocol) -> NodeResult:
        st = await ctx.get_node_state(self.instance_id)
        # None sentinel means "not started yet" — use inputs.start
        i = st.get("index") if st.get("index") is not None else inputs.start
        if i < inputs.end:
            await ctx.update_node_state(self.instance_id, {"index": i + 1})
            return NodeResult(self.Outputs(index=i), Repeat(["body"]))
        await ctx.update_node_state(self.instance_id, {"index": None})
        return NodeResult(self.Outputs(index=i), Goto(["completed"]))
