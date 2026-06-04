from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class ItemOf(Node):
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        value: str

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        fid = self.config.get("foreach_id")
        return NodeResult(self.Outputs(value=ctx.node_state(fid).get("current", "")), Stop())
