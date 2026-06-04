"""Contrato de Node / NodeResult para Flowprint.

Modelo híbrido: Pydantic para pines de DATOS + declaración aparte de pines de
EJECUCIÓN. La firma es introspeccionable SIN ejecutar el nodo (describe()), lo
que necesita el editor visual y el validador de tipos en diseño.

NodeResult lleva una INSTRUCCIÓN DE CONTROL (no un string de pin): así el motor
interpreta un vocabulario cerrado y no conoce los nodos de control por tipo.

config: todos los nodos reciben config: dict en __init__ de forma uniforme. Es
el puente entre Instance.config del JSON y el nodo.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Contexto de ejecución: estado externo de una corrida (modelo Unreal/MFR-PDDL).
# ---------------------------------------------------------------------------
class ExecutionContext:
    def __init__(self) -> None:
        self._variables: dict[str, Any] = {}
        self._node_state: dict[str, dict] = {}

    def get_var(self, name: str) -> Any:
        return self._variables.get(name)

    def set_var(self, name: str, value: Any) -> None:
        self._variables[name] = value

    def node_state(self, instance_id: str) -> dict:
        return self._node_state.setdefault(instance_id, {})


# ---------------------------------------------------------------------------
# Vocabulario de control: lo único que el motor interpreta.
#   Goto(pins)   -> activar esos pines en orden serial (normal=1, Sequence=varios)
#   Repeat(pins) -> activar esos pines y REENCOLAR al nodo emisor (loops)
#   Stop()       -> esta rama termina aquí (End, loop agotado, nodos puros)
#   Fork(pins)   -> activar en paralelo (futuro: gather; no v1)
# ---------------------------------------------------------------------------
@dataclass
class Goto:
    pins: list[str]

@dataclass
class Repeat:
    pins: list[str]

@dataclass
class Stop:
    pass

@dataclass
class Fork:
    pins: list[str]

Control = Goto | Repeat | Stop | Fork


# ---------------------------------------------------------------------------
# NodeResult: data (salidas Pydantic) + control (instrucción para el motor).
# ---------------------------------------------------------------------------
@dataclass
class NodeResult:
    data: BaseModel
    control: Control = field(default_factory=Stop)


# ---------------------------------------------------------------------------
# Node: clase base. Firma declarativa e introspeccionable.
# ---------------------------------------------------------------------------
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
    async def execute(self, inputs: BaseModel, ctx: ExecutionContext) -> NodeResult:
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


# ---------------------------------------------------------------------------
# Ejemplos de referencia (forma final, con control y config uniforme).
# ---------------------------------------------------------------------------
class Branch(Node):
    class Inputs(BaseModel):
        condition: bool
    class Outputs(BaseModel):
        pass
    exec_inputs = ("in",)
    exec_outputs = ("true", "false")
    is_pure = False

    async def execute(self, inputs: "Branch.Inputs", ctx: ExecutionContext) -> NodeResult:
        pin = "true" if inputs.condition else "false"
        return NodeResult(self.Outputs(), Goto([pin]))


class Equals(Node):
    class Inputs(BaseModel):
        a: str
        b: str
    class Outputs(BaseModel):
        result: bool
    is_pure = True

    async def execute(self, inputs: "Equals.Inputs", ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.a == inputs.b), Stop())


class FlipFlop(Node):
    class Inputs(BaseModel):
        pass
    class Outputs(BaseModel):
        pass
    exec_inputs = ("in",)
    exec_outputs = ("a", "b")
    is_pure = False

    async def execute(self, inputs: "FlipFlop.Inputs", ctx: ExecutionContext) -> NodeResult:
        st = ctx.node_state(self.instance_id)
        nxt = "a" if st.get("last", "b") == "b" else "b"
        st["last"] = nxt
        return NodeResult(self.Outputs(), Goto([nxt]))


# ---------------------------------------------------------------------------
# Validación.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        ctx = ExecutionContext()
        d = Branch.describe()
        print("describe(Branch).exec_outputs:", d["exec_outputs"])
        print("describe(Equals).is_pure:", Equals.describe()["is_pure"])
        b = Branch("b1")
        r = await b.execute(Branch.Inputs(condition=True), ctx)
        print("Branch(True) -> control:", r.control)
        eq = Equals("eq1")
        r = await eq.execute(Equals.Inputs(a="x", b="x"), ctx)
        print("Equals -> data.result:", r.data.result, "| control:", r.control)
        ff = FlipFlop("ff1")
        salidas = []
        for _ in range(4):
            r = await ff.execute(FlipFlop.Inputs(), ctx)
            salidas.append(r.control.pins[0])
        print("FlipFlop x4 -> pins:", salidas)
        print("estado en ctx:", ctx.node_state("ff1"))

    asyncio.run(main())
