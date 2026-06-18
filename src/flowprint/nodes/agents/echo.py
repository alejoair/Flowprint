from __future__ import annotations

import asyncio

from pydantic import BaseModel

from flowprint.core.context import ContextProtocol
from flowprint.core.control import Goto
from flowprint.core.node import Node, NodeResult


class AgentEcho(Node):
    """Agente de ejemplo que devuelve 'echo:{text}'. Útil para pruebas y demos."""
    class Inputs(BaseModel):
        text: str

    class Outputs(BaseModel):
        reply: str

    exec_inputs = ("in",)
    exec_outputs = ("out",)
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ContextProtocol) -> NodeResult:
        await ctx.append_to_list("__log__", "calls", f"agent({inputs.text})")
        await asyncio.sleep(0)
        return NodeResult(self.Outputs(reply=f"echo:{inputs.text}"), Goto(["out"]))
