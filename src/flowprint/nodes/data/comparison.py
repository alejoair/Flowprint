from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class GreaterThan(Node):
    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a > inputs.b), Stop())


class LessThan(Node):
    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a < inputs.b), Stop())


class GreaterEqual(Node):
    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a >= inputs.b), Stop())


class LessEqual(Node):
    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a <= inputs.b), Stop())


class NotEqual(Node):
    class Inputs(BaseModel):
        a: Any = None
        b: Any = None

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a != inputs.b), Stop())
