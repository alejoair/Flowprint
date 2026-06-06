from __future__ import annotations

from typing import Any

from pydantic import BaseModel, create_model

from flowprint.core.control import Goto
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Start(Node):
    """Punto de entrada del grafo. Expone los argumentos de invocación como pines de datos de salida. Los nombres vienen de graph.signature.inputs."""
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        pass

    exec_inputs = ()
    exec_outputs = ("out",)
    is_pure = False

    def __init__(self, instance_id: str, config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        names = self.config.get("input_names", [])
        if names:
            # Expose one output pin per declared input — no GetVar needed
            self.Outputs = create_model(
                "StartOutputs",
                **{n: (Any, None) for n in names},
            )

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        args = ctx.get_var("__args__") or {}
        names = self.config.get("input_names", [])
        outputs = {n: args.get(n) for n in names}
        return NodeResult(self.Outputs(**outputs), Goto(["out"]))
