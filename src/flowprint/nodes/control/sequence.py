from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Goto
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Sequence(Node):
    """Activa las salidas 1, 2 y 3 en orden serial. La rama 1 se agota antes de activar la 2."""
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("1", "2", "3")
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(), Goto(["1", "2", "3"]))
