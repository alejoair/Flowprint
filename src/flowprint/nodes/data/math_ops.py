from __future__ import annotations

import math

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Add(Node):
    """Suma dos floats (a + b)."""

    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a + inputs.b), Stop())


class Subtract(Node):
    """Resta dos floats (a - b)."""

    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a - inputs.b), Stop())


class Multiply(Node):
    """Multiplica dos floats (a * b)."""

    class Inputs(BaseModel):
        a: float = 1
        b: float = 1

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a * inputs.b), Stop())


class Divide(Node):
    """Divide a entre b. Devuelve 0.0 si b == 0."""

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
    """Resto de la división entera (a % b). Devuelve 0 si b == 0."""

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
    """Valor absoluto de un float."""

    class Inputs(BaseModel):
        value: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=abs(inputs.value)), Stop())


class Min(Node):
    """Devuelve el menor de dos floats."""

    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=min(inputs.a, inputs.b)), Stop())


class Max(Node):
    """Devuelve el mayor de dos floats."""

    class Inputs(BaseModel):
        a: float = 0
        b: float = 0

    class Outputs(BaseModel):
        result: float = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=max(inputs.a, inputs.b)), Stop())


class Clamp(Node):
    """Limita value al rango [min_val, max_val]."""

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
    """Redondea un float al entero más cercano."""

    class Inputs(BaseModel):
        value: float = 0

    class Outputs(BaseModel):
        result: int = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=round(inputs.value)), Stop())


class Floor(Node):
    """Redondea un float hacia abajo (entero inferior)."""

    class Inputs(BaseModel):
        value: float = 0

    class Outputs(BaseModel):
        result: int = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=math.floor(inputs.value)), Stop())


class Ceil(Node):
    """Redondea un float hacia arriba (entero superior)."""

    class Inputs(BaseModel):
        value: float = 0

    class Outputs(BaseModel):
        result: int = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=math.ceil(inputs.value)), Stop())
