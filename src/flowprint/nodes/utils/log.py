from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from flowprint.core.control import Goto
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Log(Node):
    """Emite el mensaje en el evento node_complete y lo acumula en el contexto.

    El mensaje aparece en outputs.message del evento WebSocket, visible
    en tiempo real en el editor.
    """

    class Inputs(BaseModel):
        message: Any = None

    class Outputs(BaseModel):
        message: Any = None

    exec_inputs = ("in",)
    exec_outputs = ("out",)
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        ctx.node_state("__logs__").setdefault("entries", []).append(str(inputs.message))
        return NodeResult(self.Outputs(message=inputs.message), Goto(["out"]))
