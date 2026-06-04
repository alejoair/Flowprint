from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Goto, Repeat
from flowprint.core.node import ExecutionContext, Node, NodeResult


class ForLoop(Node):
    class Inputs(BaseModel):
        start: int = 0
        end: int

    class Outputs(BaseModel):
        index: int = 0

    exec_inputs = ("in",)
    exec_outputs = ("body", "completed")
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        st = ctx.node_state(self.instance_id)
        i = st.get("index", inputs.start)
        if i < inputs.end:
            st["index"] = i + 1
            return NodeResult(self.Outputs(index=i), Repeat(["body"]))
        st.pop("index", None)
        return NodeResult(self.Outputs(index=i), Goto(["completed"]))
