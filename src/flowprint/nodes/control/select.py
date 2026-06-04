from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Select(Node):
    """Ternario: devuelve `a` si condition es True, `b` si es False."""

    class Inputs(BaseModel):
        condition: bool = False
        a: Any = None
        b: Any = None

    class Outputs(BaseModel):
        value: Any = None

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(value=inputs.a if inputs.condition else inputs.b), Stop())
