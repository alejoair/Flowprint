from __future__ import annotations

from pydantic import BaseModel

from flowprint.core.control import Goto
from flowprint.core.node import ExecutionContext, Node, NodeResult


class SwitchString(Node):
    """Enruta la ejecución según el valor de un string.

    config.cases: lista de strings. Se añade "default" automáticamente.
    Cada valor se convierte en un pin exec de salida.
    """

    class Inputs(BaseModel):
        value: str = ""

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("default",)
    is_pure = False
    _dynamic_exec = True

    def __init__(self, instance_id: str, config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        cases = list(self.config.get("cases", []))
        if "default" not in cases:
            cases.append("default")
        self.exec_outputs = tuple(cases)

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        cases = self.config.get("cases", [])
        pin = inputs.value if inputs.value in cases else "default"
        return NodeResult(self.Outputs(), Goto([pin]))


class SwitchInt(Node):
    """Enruta la ejecución según el valor de un entero.

    config.cases: lista de enteros. Pin de salida = str(valor). Se añade "default".
    """

    class Inputs(BaseModel):
        value: int = 0

    class Outputs(BaseModel):
        pass

    exec_inputs = ("in",)
    exec_outputs = ("default",)
    is_pure = False
    _dynamic_exec = True

    def __init__(self, instance_id: str, config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        cases = [str(c) for c in self.config.get("cases", [])]
        if "default" not in cases:
            cases.append("default")
        self.exec_outputs = tuple(cases)

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        cases = [str(c) for c in self.config.get("cases", [])]
        key = str(inputs.value)
        pin = key if key in cases else "default"
        return NodeResult(self.Outputs(), Goto([pin]))
