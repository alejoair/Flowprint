from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.context import ContextProtocol
from flowprint.core.control import Goto
from flowprint.core.node import Node, NodeResult


class FlipFlop(Node):
    """Alterna entre salidas 'a' y 'b' en cada ejecución."""
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("a", "b")
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ContextProtocol) -> NodeResult:
        st = await ctx.get_node_state(self.instance_id)
        nxt = "a" if st.get("last", "b") == "b" else "b"
        await ctx.update_node_state(self.instance_id, {"last": nxt})
        return NodeResult(self.Outputs(), Goto([nxt]))
