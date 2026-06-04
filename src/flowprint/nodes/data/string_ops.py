from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, create_model

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class Contains(Node):
    class Inputs(BaseModel):
        text: str = ""
        substring: str = ""

    class Outputs(BaseModel):
        result: bool = False

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.substring in inputs.text), Stop())


class Replace(Node):
    class Inputs(BaseModel):
        text: str = ""
        old: str = ""
        new: str = ""

    class Outputs(BaseModel):
        result: str = ""

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.text.replace(inputs.old, inputs.new)), Stop())


class Split(Node):
    class Inputs(BaseModel):
        text: str = ""
        separator: str = ","

    class Outputs(BaseModel):
        result: list = []

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        parts = inputs.text.split(inputs.separator) if inputs.separator else list(inputs.text)
        return NodeResult(self.Outputs(result=parts), Stop())


class ToUpper(Node):
    class Inputs(BaseModel):
        text: str = ""

    class Outputs(BaseModel):
        result: str = ""

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.text.upper()), Stop())


class ToLower(Node):
    class Inputs(BaseModel):
        text: str = ""

    class Outputs(BaseModel):
        result: str = ""

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.text.lower()), Stop())


class Trim(Node):
    class Inputs(BaseModel):
        text: str = ""

    class Outputs(BaseModel):
        result: str = ""

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.text.strip()), Stop())


class StringLength(Node):
    class Inputs(BaseModel):
        text: str = ""

    class Outputs(BaseModel):
        length: int = 0

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(length=len(inputs.text)), Stop())


class BuildString(Node):
    """Interpola variables en una plantilla usando sintaxis {variable}.

    config.template: "Hola {nombre}, tienes {n} mensajes."
    Los nombres entre llaves se convierten en pines de entrada.
    """

    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        result: str = ""

    is_pure = True

    def __init__(self, instance_id: str, config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        template = self.config.get("template", "")
        vars_ = re.findall(r'\{(\w+)\}', template)
        if vars_:
            self.Inputs = create_model(
                "BuildStringInputs",
                **{v: (Any, None) for v in dict.fromkeys(vars_)},
            )

    async def execute(self, inputs, ctx: ExecutionContext) -> NodeResult:
        template = self.config.get("template", "")
        result = template.format(**{k: (v if v is not None else "") for k, v in inputs.model_dump().items()})
        return NodeResult(self.Outputs(result=result), Stop())
