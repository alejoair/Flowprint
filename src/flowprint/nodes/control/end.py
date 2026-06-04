from __future__ import annotations

from typing import Any

from pydantic import BaseModel, create_model

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

    def __init__(self, instance_id: str, config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        names = self.config.get("output_names", [])
        if names:
            # Expose one input pin per declared output — no SetVar needed
            self.Inputs = create_model(
                "EndInputs",
                **{n: (Any, None) for n in names},
            )

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        names = self.config.get("output_names", [])
        if names:
            ctx.set_var("__result__", {n: getattr(inputs, n) for n in names})
        else:
            ctx.set_var("__result__", inputs.result)
        return NodeResult(self.Outputs(), Stop())
