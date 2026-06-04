from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, create_model

from flowprint.core.control import Stop
from flowprint.core.node import ExecutionContext, Node, NodeResult


class GetField(Node):
    """Lee un campo de un dict o objeto.

    config.field: nombre del campo a leer.
    """

    class Inputs(BaseModel):
        obj: Any = None

    class Outputs(BaseModel):
        value: Any = None

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        field = self.config.get("field", "")
        obj = inputs.obj
        if isinstance(obj, dict):
            value = obj.get(field)
        else:
            value = getattr(obj, field, None)
        return NodeResult(self.Outputs(value=value), Stop())


class MakeDict(Node):
    """Construye un dict desde pines individuales.

    config.keys: lista de claves, e.g. ["nombre", "edad", "rol"].
    Cada clave se convierte en un pin de entrada.
    """

    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        value: dict = {}

    is_pure = True

    def __init__(self, instance_id: str, config: dict | None = None) -> None:
        super().__init__(instance_id, config)
        keys = self.config.get("keys", [])
        if keys:
            self.Inputs = create_model(
                "MakeDictInputs",
                **{k: (Any, None) for k in keys},
            )

    async def execute(self, inputs, ctx: ExecutionContext) -> NodeResult:
        keys = self.config.get("keys", [])
        d = {k: getattr(inputs, k, None) for k in keys}
        return NodeResult(self.Outputs(value=d), Stop())


class SetField(Node):
    """Devuelve una copia del dict con un campo actualizado.

    config.field: nombre del campo a escribir.
    """

    class Inputs(BaseModel):
        obj: Any = None
        value: Any = None

    class Outputs(BaseModel):
        result: dict = {}

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        field = self.config.get("field", "")
        base = dict(inputs.obj) if isinstance(inputs.obj, dict) else {}
        base[field] = inputs.value
        return NodeResult(self.Outputs(result=base), Stop())


class ParseJSON(Node):
    class Inputs(BaseModel):
        text: str = ""

    class Outputs(BaseModel):
        value: Any = None

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        try:
            value = json.loads(inputs.text)
        except Exception:
            value = None
        return NodeResult(self.Outputs(value=value), Stop())


class ToJSON(Node):
    class Inputs(BaseModel):
        value: Any = None

    class Outputs(BaseModel):
        text: str = ""

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        try:
            text = json.dumps(inputs.value, ensure_ascii=False)
        except Exception:
            text = str(inputs.value)
        return NodeResult(self.Outputs(text=text), Stop())
