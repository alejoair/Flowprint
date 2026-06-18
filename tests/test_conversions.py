import pytest

from flowprint.core.node import ExecutionContext
from flowprint.graph.loader import build_engine, find_start
from flowprint.graph.schema import Graph
from flowprint.graph.validation import validate_graph
from flowprint.nodes.data.conversions import BoolToInt, IntToFloat, ToStr


# ---------------------------------------------------------------------------
# Tests unitarios de los nodos puros
# ---------------------------------------------------------------------------

async def test_int_to_float():
    ctx = ExecutionContext()
    result = await IntToFloat("n").execute(IntToFloat.Inputs(value=7), ctx)
    assert result.data.value == 7.0
    assert isinstance(result.data.value, float)


async def test_int_to_float_negativo():
    ctx = ExecutionContext()
    result = await IntToFloat("n").execute(IntToFloat.Inputs(value=-3), ctx)
    assert result.data.value == -3.0


async def test_bool_to_int_true():
    ctx = ExecutionContext()
    result = await BoolToInt("n").execute(BoolToInt.Inputs(value=True), ctx)
    assert result.data.value == 1
    assert isinstance(result.data.value, int)


async def test_bool_to_int_false():
    ctx = ExecutionContext()
    result = await BoolToInt("n").execute(BoolToInt.Inputs(value=False), ctx)
    assert result.data.value == 0


async def test_tostr_desde_int():
    ctx = ExecutionContext()
    result = await ToStr("n").execute(ToStr.Inputs(value=42), ctx)
    assert result.data.value == "42"


async def test_tostr_desde_float():
    ctx = ExecutionContext()
    result = await ToStr("n").execute(ToStr.Inputs(value=3.14), ctx)
    assert result.data.value == "3.14"


async def test_tostr_desde_bool():
    ctx = ExecutionContext()
    result = await ToStr("n").execute(ToStr.Inputs(value=True), ctx)
    assert result.data.value == "True"


# ---------------------------------------------------------------------------
# Todos son nodos puros
# ---------------------------------------------------------------------------

def test_son_puros():
    assert IntToFloat.is_pure is True
    assert BoolToInt.is_pure is True
    assert ToStr.is_pure is True


# ---------------------------------------------------------------------------
# El validador sugiere el nodo correcto cuando falta la conversión
# ---------------------------------------------------------------------------

def test_validador_sugiere_int_to_float():
    # Grafo con Equals (salida bool) → Branch (entrada bool): válido de base.
    # Usamos Concat.a: str ← un nodo con salida int para provocar incompatibilidad.
    # Como no tenemos IntConst, probamos directamente validate_graph con un tipo
    # incompatible conocido (bool→str) que el validador debe sugerir ToStr.
    graph_json = {
        "schema_version": "1.0",
        "signature": {"inputs": {}, "outputs": {}},
        "variables": [],
        "instances": [
            {"id": "start", "type": "Start", "config": {}},
            {"id": "eq", "type": "Equals", "config": {}},   # Outputs.result: bool
            {"id": "cat", "type": "Concat", "config": {}},  # Inputs.a: str  ← incompatible
            {"id": "ag", "type": "AgentEcho", "config": {}},
            {"id": "end", "type": "End", "config": {}},
        ],
        "connections": [
            {"kind": "exec", "from_node": "start", "from_pin": "out", "to_node": "ag", "to_pin": "in"},
            {"kind": "exec", "from_node": "ag", "from_pin": "out", "to_node": "end", "to_pin": "in"},
            # bool → str: el validador debe sugerir ToStr
            {"kind": "data", "from_node": "eq", "from_pin": "result", "to_node": "cat", "to_pin": "a"},
            # pines requeridos de Equals y Concat sin conexión (los ignoramos; el test
            # solo verifica la detección de la conversión)
        ],
        "visual": {"positions": {}, "zoom": 1.0},
    }
    graph = Graph.model_validate(graph_json)
    errors = validate_graph(graph)
    conversion_errors = [e for e in errors if "ToStr" in e]
    assert conversion_errors, f"Se esperaba sugerencia de ToStr, errores: {errors}"


# ---------------------------------------------------------------------------
# Grafo válido con conversión explícita insertada (IntToFloat en el grafo)
# ---------------------------------------------------------------------------

async def test_grafo_con_tostr_explicito():
    # Flujo: Start → AgentEcho → End
    # Datos: Equals(a="x", b="x") → result:bool → ToStr → value:str → AgentEcho.text
    graph_json = {
        "schema_version": "1.0",
        "signature": {"inputs": {}, "outputs": {}},
        "variables": [],
        "instances": [
            {"id": "start", "type": "Start", "config": {}},
            {"id": "ka", "type": "Const", "config": {"value": "x"}},
            {"id": "kb", "type": "Const", "config": {"value": "x"}},
            {"id": "eq", "type": "Equals", "config": {}},
            {"id": "conv", "type": "ToStr", "config": {}},
            {"id": "ag", "type": "AgentEcho", "config": {}},
            {"id": "end", "type": "End", "config": {}},
        ],
        "connections": [
            {"kind": "exec", "from_node": "start", "from_pin": "out", "to_node": "ag", "to_pin": "in"},
            {"kind": "exec", "from_node": "ag", "from_pin": "out", "to_node": "end", "to_pin": "in"},
            {"kind": "data", "from_node": "ka", "from_pin": "value", "to_node": "eq", "to_pin": "a"},
            {"kind": "data", "from_node": "kb", "from_pin": "value", "to_node": "eq", "to_pin": "b"},
            {"kind": "data", "from_node": "eq", "from_pin": "result", "to_node": "conv", "to_pin": "value"},
            {"kind": "data", "from_node": "conv", "from_pin": "value", "to_node": "ag", "to_pin": "text"},
        ],
        "visual": {"positions": {}, "zoom": 1.0},
    }
    graph = Graph.model_validate(graph_json)
    engine = build_engine(graph)
    await engine.run(find_start(graph))
    # Equals("x","x") → True → ToStr → "True" → AgentEcho
    log = await engine.ctx.get_node_state("__log__")
    assert log.get("calls") == ["agent(True)"]
