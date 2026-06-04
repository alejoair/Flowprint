"""Registro ÚNICO de tipos de nodo: nombre -> clase Node.

Es la fuente única de verdad que comparten:
  - el validador del esquema (comprueba pines contra el contrato real),
  - el cargador (instancia los nodos por nombre),
  - el motor (ejecuta esas instancias).

Antes había dos universos de nodos sin unificar (Branch/Equals/FlipFlop en el
esquema; Start/End/Sequence/... en el motor). Aquí se juntan.
"""

from __future__ import annotations

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

NODE_REGISTRY: dict[str, type[Node]] = {
    # control / entrada-salida (motor)
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
    # variables (Get/Set, sección 3b)
    "GetVar": GetVar,
    "SetVar": SetVar,
    # agentes
    "AgentEcho": AgentEcho,
}
