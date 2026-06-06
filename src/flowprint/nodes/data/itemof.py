from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class ItemOf(Node):
    """Devuelve el elemento actual de una iteración ForEach.

    config.foreach_id: id de instancia del nodo ForEach al que está ligado.
    """
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        value: str

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        fid = self.config.get("foreach_id")
        return NodeResult(self.Outputs(value=ctx.node_state(fid).get("current", "")), Stop())
