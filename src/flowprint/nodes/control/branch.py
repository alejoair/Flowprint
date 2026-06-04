from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Goto
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Branch(Node):
    class Inputs(BaseModel):
        condition: bool

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("true", "false")
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        pin = "true" if inputs.condition else "false"
        return NodeResult(self.Outputs(), Goto([pin]))
