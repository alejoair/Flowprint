from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class GetVar(Node):
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        value: Any = None

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(value=ctx.get_var(self.config.get("var"))), Stop())
