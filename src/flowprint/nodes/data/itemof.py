from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.context import ContextProtocol
from flowprint.core.control import Stop
from flowprint.core.node import Node, NodeResult


class ItemOf(Node):
    """Devuelve el elemento actual de una iteración ForEach.

    config.foreach_id: id de instancia del nodo ForEach al que está ligado.
    """
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        value: str

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ContextProtocol) -> NodeResult:
        fid = self.config.get("foreach_id")
        st = await ctx.get_node_state(fid)
        return NodeResult(self.Outputs(value=st.get("current", "")), Stop())
