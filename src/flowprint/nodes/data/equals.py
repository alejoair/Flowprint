from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Equals(Node):
    class Inputs(BaseModel):
        a: str
        b: str

    class Outputs(BaseModel):
        result: bool

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a == inputs.b), Stop())
