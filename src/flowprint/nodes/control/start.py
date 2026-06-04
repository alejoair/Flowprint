from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Goto
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Start(Node):
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        pass

    exec_inputs = ()
    exec_outputs = ("out",)
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        args = ctx.get_var("__args__") or {}
        for name in self.config.get("input_names", []):
            ctx.set_var(name, args.get(name))
        return NodeResult(self.Outputs(), Goto(["out"]))
