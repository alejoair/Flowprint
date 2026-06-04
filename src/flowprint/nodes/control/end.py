from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class End(Node):
    class Inputs(BaseModel):
        result: Any = None

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ()
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        names = self.config.get("output_names", [])
        if names:
            ctx.set_var("__result__", {n: ctx.get_var(n) for n in names})
        else:
            ctx.set_var("__result__", inputs.result)
        return NodeResult(self.Outputs(), Stop())
