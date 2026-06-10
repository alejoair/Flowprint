import json

import pytest

from flowprint.graph.loader import build_engine, find_start
from flowprint.graph.schema import Graph

SEQUENCE_JSON = {
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


async def test_sequence_serial():
    graph = Graph.model_validate(SEQUENCE_JSON)
    engine = build_engine(graph)
    await engine.run(find_start(graph))
    assert engine.ctx.node_state("__log__").get("calls") == ["agent(uno)", "agent(dos)", "agent(tres)"]


async def test_invalid_exec_pin_rejected():
    bad = json.loads(json.dumps(SEQUENCE_JSON))
    bad["connections"].append(
        {"kind": "exec", "from_node": "seq", "from_pin": "9", "to_node": "a1", "to_pin": "in"}
    )
    with pytest.raises(ValueError, match="Grafo inválido"):
        build_engine(Graph.model_validate(bad))


async def test_required_data_pin_without_connection_rejected():
    no_data = json.loads(json.dumps(SEQUENCE_JSON))
    no_data["connections"] = [c for c in no_data["connections"] if c["kind"] == "exec"]
    with pytest.raises(ValueError):
        build_engine(Graph.model_validate(no_data))


async def test_pull_puro_recursivo():
    graph_json = {
        "schema_version": "1.0",
        "signature": {"inputs": {}, "outputs": {}},
        "variables": [],
        "instances": [
            {"id": "start", "type": "Start", "config": {}},
            {"id": "ca", "type": "Const", "config": {"value": "hola_"}},
            {"id": "cb", "type": "Const", "config": {"value": "mundo"}},
            {"id": "cat", "type": "Concat", "config": {}},
            {"id": "ag", "type": "AgentEcho", "config": {}},
            {"id": "end", "type": "End", "config": {}},
        ],
        "connections": [
            {"kind": "exec", "from_node": "start", "from_pin": "out", "to_node": "ag", "to_pin": "in"},
            {"kind": "exec", "from_node": "ag", "from_pin": "out", "to_node": "end", "to_pin": "in"},
            {"kind": "data", "from_node": "ca", "from_pin": "value", "to_node": "cat", "to_pin": "a"},
            {"kind": "data", "from_node": "cb", "from_pin": "value", "to_node": "cat", "to_pin": "b"},
            {"kind": "data", "from_node": "cat", "from_pin": "value", "to_node": "ag", "to_pin": "text"},
        ],
        "visual": {"positions": {}, "zoom": 1.0},
    }
    graph = Graph.model_validate(graph_json)
    engine = build_engine(graph)
    await engine.run(find_start(graph))
    assert engine.ctx.node_state("__log__").get("calls") == ["agent(hola_mundo)"]


async def test_foreach_con_itemof():
    graph_json = {
        "schema_version": "1.0",
        "signature": {"inputs": {}, "outputs": {}},
        "variables": [],
        "instances": [
            {"id": "start", "type": "Start", "config": {}},
            {"id": "fe", "type": "ForEach", "config": {}},
            {"id": "item", "type": "ItemOf", "config": {"foreach_id": "fe"}},
            {"id": "ag", "type": "AgentEcho", "config": {}},
            {"id": "end", "type": "End", "config": {}},
        ],
        "connections": [
            {"kind": "exec", "from_node": "start", "from_pin": "out", "to_node": "fe", "to_pin": "in"},
            {"kind": "exec", "from_node": "fe", "from_pin": "body", "to_node": "ag", "to_pin": "in"},
            {"kind": "exec", "from_node": "fe", "from_pin": "completed", "to_node": "end", "to_pin": "in"},
            {"kind": "data", "from_node": "item", "from_pin": "value", "to_node": "ag", "to_pin": "text"},
        ],
        "visual": {"positions": {}, "zoom": 1.0},
    }
    graph = Graph.model_validate(graph_json)
    engine = build_engine(graph)
    await engine.ctx.set_var("foreach_items", ["x", "y", "z"])
    await engine.run(find_start(graph))
    assert engine.ctx.node_state("__log__").get("calls") == ["agent(x)", "agent(y)", "agent(z)"]
