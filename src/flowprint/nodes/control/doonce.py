from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Goto, Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class DoOnce(Node):
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("out",)
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        st = ctx.node_state(self.instance_id)
        if st.get("done"):
            return NodeResult(self.Outputs(), Stop())
        st["done"] = True
        return NodeResult(self.Outputs(), Goto(["out"]))
