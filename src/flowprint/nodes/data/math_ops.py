from __future__ import annotations

import math

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Add(Node):
    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a + inputs.b), Stop())


class Subtract(Node):
    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a - inputs.b), Stop())


class Multiply(Node):
    class Inputs(BaseModel):
        a: float = 1
        b: float = 1

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a * inputs.b), Stop())


class Divide(Node):
    class Inputs(BaseModel):
        a: float = 0
        b: float = 1

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        result = inputs.a / inputs.b if inputs.b != 0 else 0.0
        return NodeResult(self.Outputs(result=result), Stop())


class Modulo(Node):
    class Inputs(BaseModel):
        a: int = 0
        b: int = 1

    class Outputs(BaseModel):
        result: int = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        result = inputs.a % inputs.b if inputs.b != 0 else 0
        return NodeResult(self.Outputs(result=result), Stop())


class Abs(Node):
    class Inputs(BaseModel):
        value: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=abs(inputs.value)), Stop())


class Min(Node):
    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=min(inputs.a, inputs.b)), Stop())


class Max(Node):
    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=max(inputs.a, inputs.b)), Stop())


class Clamp(Node):
    class Inputs(BaseModel):
        value: float = 0
        min_val: float = 0
        max_val: float = 1

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        result = max(inputs.min_val, min(inputs.max_val, inputs.value))
        return NodeResult(self.Outputs(result=result), Stop())


class Round(Node):
    class Inputs(BaseModel):
        value: float = 0

    class Outputs(BaseModel):
        result: int = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=round(inputs.value)), Stop())


class Floor(Node):
    class Inputs(BaseModel):
        value: float = 0

    class Outputs(BaseModel):
        result: int = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=math.floor(inputs.value)), Stop())


class Ceil(Node):
    class Inputs(BaseModel):
        value: float = 0

    class Outputs(BaseModel):
        result: int = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=math.ceil(inputs.value)), Stop())
