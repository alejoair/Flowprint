"""Registro ÚNICO de tipos de nodo: nombre -> clase Node.

Es la fuente única de verdad que comparten:
  - el validador del esquema (comprueba pines contra el contrato real),
  - el cargador (instancia los nodos por nombre),
  - el motor (ejecuta esas instancias).

Los nodos built-in están hardcodeados abajo. Los nodos custom se descubren
automáticamente desde la carpeta `custom_nodes/` al lado de este archivo:
cualquier .py que defina una subclase de Node queda disponible en el registro.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

from flowprint_node_contract import Branch, Equals, FlipFlop, Node
from flowprint_engine import (
    AgentEcho,
    Concat,
    Const,
    End,
    ForEach,
    GetVar,
    ItemOf,
    Sequence,
    SetVar,
    Start,
)

# ---------------------------------------------------------------------------
# Nodos built-in (hardcodeados, siempre disponibles)
# ---------------------------------------------------------------------------
NODE_REGISTRY: dict[str, type[Node]] = {
    # control / entrada-salida
    "Start": Start,
    "End": End,
    "Sequence": Sequence,
    "ForEach": ForEach,
    "Branch": Branch,
    # puros
    "Const": Const,
    "Concat": Concat,
    "ItemOf": ItemOf,
    "Equals": Equals,
    # estado
    "FlipFlop": FlipFlop,
    # variables
    "GetVar": GetVar,
    "SetVar": SetVar,
    # agentes
    "AgentEcho": AgentEcho,
}


# ---------------------------------------------------------------------------
# Descubrimiento dinámico de nodos custom
# ---------------------------------------------------------------------------
_CUSTOM_NODES_DIR = Path(__file__).parent / "custom_nodes"


def load_custom_nodes(folder: Path | str | None = None) -> dict[str, type[Node]]:
    """Escanea *folder* y registra todas las subclases de Node que encuentre.

    Reglas:
    - Solo archivos .py que no empiecen por '_'.
    - Solo clases definidas en ese módulo (no las que importa de flowprint_*).
    - Si un nombre ya existe en NODE_REGISTRY (built-in), el custom lo
      sobreescribe y se emite un aviso.

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
            print(f"[flowprint_registry] Error cargando {py_file.name}: {exc}")
            continue

        for name, cls in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(cls, Node)
                and cls is not Node
                and cls.__module__ == module.__name__
            ):
                if name in NODE_REGISTRY:
                    print(
                        f"[flowprint_registry] AVISO: '{name}' de {py_file.name} "
                        f"sobreescribe un nodo built-in."
                    )
                loaded[name] = cls

    NODE_REGISTRY.update(loaded)
    return loaded


def refresh_custom_nodes(folder: Path | str | None = None) -> dict[str, type[Node]]:
    """Recarga los nodos custom (útil en desarrollo o cuando el frontend
    guarda un nuevo archivo en custom_nodes/)."""
    # Limpia las entradas previas que no sean built-in antes de reimportar.
    _BUILTIN_NAMES = {
        "Start", "End", "Sequence", "ForEach", "Branch",
        "Const", "Concat", "ItemOf", "Equals", "FlipFlop",
        "GetVar", "SetVar", "AgentEcho",
    }
    for key in list(NODE_REGISTRY):
        if key not in _BUILTIN_NAMES:
            del NODE_REGISTRY[key]
    return load_custom_nodes(folder)


# Auto-descubrimiento al importar el módulo.
load_custom_nodes()
