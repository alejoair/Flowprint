from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class IntToFloat(Node):
    """Convierte int a float."""
    class Inputs(BaseModel):
        value: int

    class Outputs(BaseModel):
        value: float

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(value=float(inputs.value)), Stop())


class BoolToInt(Node):
    """Convierte bool a int (True → 1, False → 0)."""
    class Inputs(BaseModel):
        value: bool

    class Outputs(BaseModel):
        value: int

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(value=int(inputs.value)), Stop())


class ToStr(Node):
    """Convierte int, float o bool a str. El validador lo sugiere para esos pares."""

    class Inputs(BaseModel):
        value: Any = None

    class Outputs(BaseModel):
        value: str

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(value=str(inputs.value)), Stop())
