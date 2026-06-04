from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from flowprint.core.node import Node
from flowprint.nodes.agents.echo import AgentEcho
from flowprint.nodes.control.branch import Branch
from flowprint.nodes.control.doonce import DoOnce
from flowprint.nodes.control.end import End
from flowprint.nodes.control.flipflop import FlipFlop
from flowprint.nodes.control.foreach import ForEach
from flowprint.nodes.control.forloop import ForLoop
from flowprint.nodes.control.select import Select
from flowprint.nodes.control.sequence import Sequence
from flowprint.nodes.control.start import Start
from flowprint.nodes.control.switch import SwitchInt, SwitchString
from flowprint.nodes.control.whileloop import WhileLoop
from flowprint.nodes.data.arrays import AppendItem, GetIndex, ListContains, ListLength, MakeList
from flowprint.nodes.data.comparison import GreaterEqual, GreaterThan, LessEqual, LessThan, NotEqual
from flowprint.nodes.data.concat import Concat
from flowprint.nodes.data.const import Const
from flowprint.nodes.data.conversions import BoolToInt, IntToFloat, ToStr
from flowprint.nodes.data.equals import Equals
from flowprint.nodes.data.itemof import ItemOf
from flowprint.nodes.data.logic import And, IsValid, Not, Or
from flowprint.nodes.data.math_ops import (
    Abs, Add, Ceil, Clamp, Divide, Floor, Max, Min, Modulo, Multiply, Round, Subtract,
)
from flowprint.nodes.data.string_ops import (
    BuildString, Contains, Replace, Split, StringLength, Trim, ToLower, ToUpper,
)
from flowprint.nodes.data.structs import GetField, MakeDict, ParseJSON, SetField, ToJSON
from flowprint.nodes.utils.log import Log
from flowprint.nodes.variables.getvar import GetVar
from flowprint.nodes.variables.setvar import SetVar

NODE_REGISTRY: dict[str, type[Node]] = {
    # Control
    "Start": Start,
    "End": End,
    "Sequence": Sequence,
    "ForEach": ForEach,
    "ForLoop": ForLoop,
    "WhileLoop": WhileLoop,
    "Branch": Branch,
    "FlipFlop": FlipFlop,
    "DoOnce": DoOnce,
    "Select": Select,
    "SwitchString": SwitchString,
    "SwitchInt": SwitchInt,
    # Logic
    "And": And,
    "Or": Or,
    "Not": Not,
    "IsValid": IsValid,
    # Comparison
    "Equals": Equals,
    "NotEqual": NotEqual,
    "GreaterThan": GreaterThan,
    "LessThan": LessThan,
    "GreaterEqual": GreaterEqual,
    "LessEqual": LessEqual,
    # Math
    "Add": Add,
    "Subtract": Subtract,
    "Multiply": Multiply,
    "Divide": Divide,
    "Modulo": Modulo,
    "Abs": Abs,
    "Min": Min,
    "Max": Max,
    "Clamp": Clamp,
    "Round": Round,
    "Floor": Floor,
    "Ceil": Ceil,
    # Data
    "Const": Const,
    "Concat": Concat,
    "ItemOf": ItemOf,
    "IntToFloat": IntToFloat,
    "BoolToInt": BoolToInt,
    "ToStr": ToStr,
    # Strings
    "Contains": Contains,
    "Replace": Replace,
    "Split": Split,
    "ToUpper": ToUpper,
    "ToLower": ToLower,
    "Trim": Trim,
    "StringLength": StringLength,
    "BuildString": BuildString,
    # Arrays
    "MakeList": MakeList,
    "GetIndex": GetIndex,
    "AppendItem": AppendItem,
    "ListLength": ListLength,
    "ListContains": ListContains,
    # Structs / JSON
    "GetField": GetField,
    "MakeDict": MakeDict,
    "SetField": SetField,
    "ParseJSON": ParseJSON,
    "ToJSON": ToJSON,
    # Variables
    "GetVar": GetVar,
    "SetVar": SetVar,
    # Utils
    "Log": Log,
    # Agents
    "AgentEcho": AgentEcho,
}

BUILTIN_NODE_NAMES: frozenset[str] = frozenset(NODE_REGISTRY)
CUSTOM_NODES_DIR: Path = Path.cwd() / "custom_nodes"

_BUILTIN_NAMES = BUILTIN_NODE_NAMES
_CUSTOM_NODES_DIR = CUSTOM_NODES_DIR


def load_custom_nodes(folder: Path | str | None = None) -> dict[str, type[Node]]:
    """Escanea *folder* y registra todas las subclases de Node que encuentre.

    Reglas:
    - Solo archivos .py que no empiecen por '_'.
    - Solo clases definidas en ese módulo (no las importadas).
    - Si un nombre coincide con un built-in, lo sobreescribe y avisa.

    Devuelve el sub-diccionario {nombre: clase} de los nodos cargados.
    """
    folder = Path(folder) if folder else _CUSTOM_NODES_DIR
    if not folder.exists():
        return {}

    loaded: dict[str, type[Node]] = {}
    for py_file in sorted(folder.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            print(f"[registry] Error cargando {py_file.name}: {exc}")
            continue

        for name, cls in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(cls, Node)
                and cls is not Node
                and cls.__module__ == module.__name__
            ):
                if name in _BUILTIN_NAMES:
                    print(f"[registry] AVISO: '{name}' de {py_file.name} sobreescribe un built-in.")
                loaded[name] = cls

    NODE_REGISTRY.update(loaded)
    return loaded


def refresh_custom_nodes(folder: Path | str | None = None) -> dict[str, type[Node]]:
    """Recarga nodos custom eliminando primero los anteriores no built-in."""
    for key in list(NODE_REGISTRY):
        if key not in _BUILTIN_NAMES:
            del NODE_REGISTRY[key]
    return load_custom_nodes(folder)


# Auto-descubrimiento al importar.
load_custom_nodes()
