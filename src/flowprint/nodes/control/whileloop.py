from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Goto, Repeat
from flowprint.core.node import ExecutionContext, Node, NodeResult


class WhileLoop(Node):
    class Inputs(BaseModel):
        condition: bool = False

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("body", "completed")
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        if inputs.condition:
            return NodeResult(self.Outputs(), Repeat(["body"]))
        return NodeResult(self.Outputs(), Goto(["completed"]))
