from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class And(Node):
    class Inputs(BaseModel):
        a: bool = False
        b: bool = False

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a and inputs.b), Stop())


class Or(Node):
    class Inputs(BaseModel):
        a: bool = False
        b: bool = False

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a or inputs.b), Stop())


class Not(Node):
    class Inputs(BaseModel):
        value: bool = False

    class Outputs(BaseModel):
        result: bool = True

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=not inputs.value), Stop())


class IsValid(Node):
    """Devuelve True si el valor no es None ni string vacío."""

    class Inputs(BaseModel):
        value: Any = None

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        v = inputs.value
        valid = v is not None and v != ""
        return NodeResult(self.Outputs(result=valid), Stop())
