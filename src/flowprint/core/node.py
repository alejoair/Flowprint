from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel

from flowprint.core.context import ContextProtocol, LocalContext
from flowprint.core.control import Control, Stop

# Backward-compat alias — existing imports of ExecutionContext keep working
ExecutionContext = LocalContext


@dataclass
class NodeResult:
    data: BaseModel
    control: Control = field(default_factory=Stop)


class Node(ABC):
    Inputs: ClassVar[type[BaseModel]]
    Outputs: ClassVar[type[BaseModel]]

    exec_inputs: ClassVar[tuple[str, ...]] = ("in",)
    exec_outputs: ClassVar[tuple[str, ...]] = ("out",)
    is_pure: ClassVar[bool] = False

    def __init__(self, instance_id: str, config: dict[str, Any] | None = None) -> None:
        self.instance_id = instance_id
        self.config = config or {}

    @abstractmethod
    async def execute(self, inputs: BaseModel, ctx: ContextProtocol) -> NodeResult:
        ...

    @classmethod
    def describe(cls) -> dict:
        return {
            "type": cls.__name__,
            "is_pure": cls.is_pure,
            "data_inputs": {n: f.annotation for n, f in cls.Inputs.model_fields.items()}
                if hasattr(cls, "Inputs") else {},
            "data_outputs": {n: f.annotation for n, f in cls.Outputs.model_fields.items()}
                if hasattr(cls, "Outputs") else {},
            "exec_inputs": () if cls.is_pure else cls.exec_inputs,
            "exec_outputs": () if cls.is_pure else cls.exec_outputs,
        }
