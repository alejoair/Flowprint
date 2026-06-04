from __future__ import annotations

from typing import Any

from pydantic import BaseModel, create_model

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class MakeList(Node):
    """Construye una lista desde pines individuales.

    config.n: número de elementos (por defecto 2).
    Pines de entrada: item_0, item_1, ..., item_{n-1}.
    """

    class Inputs(BaseModel):
        item_0: Any = None
        item_1: Any = None

    class Outputs(BaseModel):
        value: list = []

    is_pure = True

    def __init__(self, instance_id: str, config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        n = self.config.get("n", 2)
        self.Inputs = create_model(
            "MakeListInputs",
            **{f"item_{i}": (Any, None) for i in range(n)},
        )

    async def execute(self, inputs, ctx: ExecutionContext) -> NodeResult:
        n = self.config.get("n", 2)
        items = [getattr(inputs, f"item_{i}") for i in range(n)]
        return NodeResult(self.Outputs(value=items), Stop())


class GetIndex(Node):
    class Inputs(BaseModel):
        array: list = []
        index: int = 0

    class Outputs(BaseModel):
        value: Any = None

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        try:
            value = inputs.array[inputs.index]
        except IndexError:
            value = None
        return NodeResult(self.Outputs(value=value), Stop())


class AppendItem(Node):
    class Inputs(BaseModel):
        array: list = []
        item: Any = None

    class Outputs(BaseModel):
        result: list = []

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=[*inputs.array, inputs.item]), Stop())


class ListLength(Node):
    class Inputs(BaseModel):
        array: list = []

    class Outputs(BaseModel):
        length: int = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(length=len(inputs.array)), Stop())


class ListContains(Node):
    class Inputs(BaseModel):
        array: list = []
        item: Any = None

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.item in inputs.array), Stop())
