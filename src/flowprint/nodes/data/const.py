from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Const(Node):
    """Emite un valor constante definido en config.value. Output pin: value (str por defecto).

    config.value: el valor a emitir (string).
    """
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        value: str

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(value=self.config.get("value", "")), Stop())
