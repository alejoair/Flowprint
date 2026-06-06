from pydantic import BaseModel
from flowprint.core.control import Stop
from flowprint.core.node import Node, NodeResult

class UpperCase(Node):
    class Inputs(BaseModel):
        text: str
    class Outputs(BaseModel):
        value: str
    is_pure = True
    async def execute(self, inputs, ctx) -> NodeResult:
        return NodeResult(self.Outputs(value=inputs.text.upper()), Stop())
