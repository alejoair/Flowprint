from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.context import ContextProtocol
from flowprint.core.control import Fork
from flowprint.core.node import Node, NodeResult


class Parallel(Node):
    """Activa N salidas de ejecución en paralelo (Fork real con Ray).

    config.n: número de ramas (default 2). Las salidas se llaman "1", "2", ..., "N".
    """
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("1", "2")
    is_pure = False
    _dynamic_exec = True

    def __init__(self, instance_id: str, config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        n = max(2, int(self.config.get("n", 2)))
        self.exec_outputs = tuple(str(i) for i in range(1, n + 1))

    async def execute(self, inputs: Inputs, ctx: ContextProtocol) -> NodeResult:
        return NodeResult(self.Outputs(), Fork(list(self.exec_outputs)))
