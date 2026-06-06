from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from flowprint.core.control import Goto
from flowprint.core.node import ExecutionContext, Node, NodeResult


class SetVar(Node):
    """Escribe un valor en una variable nombrada del contexto de ejecución.

    config.var: nombre de la variable a escribir.
    """
    class Inputs(BaseModel):
        value: Any = None

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("out",)
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        ctx.set_var(self.config.get("var"), inputs.value)
        return NodeResult(self.Outputs(), Goto(["out"]))
