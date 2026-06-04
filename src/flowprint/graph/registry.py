from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from flowprint.core.node import Node
from flowprint.nodes.agents.echo import AgentEcho
from flowprint.nodes.control.branch import Branch
from flowprint.nodes.control.end import End
from flowprint.nodes.control.flipflop import FlipFlop
from flowprint.nodes.control.foreach import ForEach
from flowprint.nodes.control.sequence import Sequence
from flowprint.nodes.control.start import Start
from flowprint.nodes.data.concat import Concat
from flowprint.nodes.data.const import Const
from flowprint.nodes.data.conversions import BoolToInt, IntToFloat, ToStr
from flowprint.nodes.data.equals import Equals
from flowprint.nodes.data.itemof import ItemOf
from flowprint.nodes.variables.getvar import GetVar
from flowprint.nodes.variables.setvar import SetVar

NODE_REGISTRY: dict[str, type[Node]] = {
    "Start": Start,
    "End": End,
    "Sequence": Sequence,
    "ForEach": ForEach,
    "Branch": Branch,
    "FlipFlop": FlipFlop,
    "Const": Const,
    "Concat": Concat,
    "ItemOf": ItemOf,
    "Equals": Equals,
    "IntToFloat": IntToFloat,
    "BoolToInt": BoolToInt,
    "ToStr": ToStr,
    "GetVar": GetVar,
    "SetVar": SetVar,
    "AgentEcho": AgentEcho,
}

BUILTIN_NODE_NAMES: frozenset[str] = frozenset(NODE_REGISTRY)
CUSTOM_NODES_DIR: Path = Path(__file__).parent.parent.parent.parent / "custom_nodes"

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
