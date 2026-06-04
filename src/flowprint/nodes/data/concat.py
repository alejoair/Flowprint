from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Concat(Node):
    """Concatena dos strings (a + b). Output pin: value."""
    class Inputs(BaseModel):
        a: str
        b: str

    class Outputs(BaseModel):
        value: str

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(value=inputs.a + inputs.b), Stop())
