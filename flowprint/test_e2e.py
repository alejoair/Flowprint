"""Prueba de extremo a extremo: JSON -> validador -> cargador -> motor.

Replica el Caso 1 (Sequence con 3 agentes, cada uno con su texto por Const)
pero partiendo de un grafo JSON, sin construir nodos a mano. Esto ejercita
exactamente el puente que faltaba.
"""

import asyncio
import json

from flowprint_graph_schema import Graph
from flowprint_loader import build_engine, find_start, run_graph

GRAPH_JSON = {
    "schema_version": "1.0",
    "signature": {"inputs": {}, "outputs": {"resultado": "str"}},
    "variables": [],
    "instances": [
        {"id": "start", "type": "Start", "config": {}},
        {"id": "seq", "type": "Sequence", "config": {}},
        {"id": "a1", "type": "AgentEcho", "config": {}},
        {"id": "a2", "type": "AgentEcho", "config": {}},
        {"id": "a3", "type": "AgentEcho", "config": {}},
        {"id": "c1", "type": "Const", "config": {"value": "uno"}},
        {"id": "c2", "type": "Const", "config": {"value": "dos"}},
        {"id": "c3", "type": "Const", "config": {"value": "tres"}},
        {"id": "end", "type": "End", "config": {}},
    ],
    "connections": [
        {"kind": "exec", "from_node": "start", "from_pin": "out", "to_node": "seq", "to_pin": "in"},
        {"kind": "exec", "from_node": "seq", "from_pin": "1", "to_node": "a1", "to_pin": "in"},
        {"kind": "exec", "from_node": "seq", "from_pin": "2", "to_node": "a2", "to_pin": "in"},
        {"kind": "exec", "from_node": "seq", "from_pin": "3", "to_node": "a3", "to_pin": "in"},
        {"kind": "exec", "from_node": "a3", "from_pin": "out", "to_node": "end", "to_pin": "in"},
        {"kind": "data", "from_node": "c1", "from_pin": "value", "to_node": "a1", "to_pin": "text"},
        {"kind": "data", "from_node": "c2", "from_pin": "value", "to_node": "a2", "to_pin": "text"},
        {"kind": "data", "from_node": "c3", "from_pin": "value", "to_node": "a3", "to_pin": "text"},
    ],
    "visual": {"positions": {}, "zoom": 1.0},
}

# Grafo INVÁLIDO: pin de ejecución que no existe en Sequence ("9").
BAD_JSON = json.loads(json.dumps(GRAPH_JSON))
BAD_JSON["connections"].append(
    {"kind": "exec", "from_node": "seq", "from_pin": "9", "to_node": "a1", "to_pin": "in"}
)


async def main():
    # 1) Grafo válido, recorrido completo por el puente.
    graph = Graph.model_validate(GRAPH_JSON)
    engine = build_engine(graph)
    await engine.run(find_start(graph))
    print("E2E Sequence desde JSON:", engine.ctx.node_state("__log__").get("calls"))

    # 2) Grafo inválido: el cargador lo rechaza ANTES de ejecutar.
    bad = Graph.model_validate(BAD_JSON)
    try:
        build_engine(bad)
        print("ERROR: el grafo inválido no fue rechazado")
    except ValueError as e:
        print("Grafo inválido rechazado correctamente:")
        print("  ", str(e).replace(chr(10), chr(10) + "   "))


asyncio.run(main())
