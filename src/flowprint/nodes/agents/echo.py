from __future__ import annotations

import asyncio

from pydantic import BaseModel

from flowprint.core.control import Goto
from flowprint.core.node import ExecutionContext, Node, NodeResult


class AgentEcho(Node):
    class Inputs(BaseModel):
        text: str

    class Outputs(BaseModel):
        reply: str

    exec_inputs = ("in",)
    exec_outputs = ("out",)
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        ctx.node_state("__log__").setdefault("calls", []).append(f"agent({inputs.text})")
        await asyncio.sleep(0)
        return NodeResult(self.Outputs(reply=f"echo:{inputs.text}"), Goto(["out"]))
