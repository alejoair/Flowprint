"""Esquema JSON del grafo de Flowprint + validador.

Diseño orientado a que un LLM pueda leer y modificar el grafo de forma fiable:
- Lista ÚNICA de conexiones, cada una con campo `kind` ("exec" | "data").
- Identificadores de instancia legibles (clasificador_1, branch_categoria...).
- Pines referenciados por NOMBRE (los del contrato de Node), no por índice.
- Lo visual (posición, zoom) va en una sección APARTE: ruido para el LLM, no
  afecta la ejecución.

Este archivo define el esquema (modelos Pydantic) y un validador que comprueba
un grafo de ejemplo contra el contrato de Node (flowprint_node_contract.py).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# Reutilizamos el contrato de nodos y el registro unificado.
from flowprint_node_contract import Node
from flowprint_registry import NODE_REGISTRY


# ---------------------------------------------------------------------------
# Esquema del grafo
# ---------------------------------------------------------------------------
class Instance(BaseModel):
    """Una instancia de nodo colocada en el grafo."""
    id: str                       # id legible: "clasificador_1"
    type: str                     # nombre del tipo de nodo: "Branch"
    config: dict[str, Any] = Field(default_factory=dict)  # parámetros fijos (modelo, prompt...)


class Connection(BaseModel):
    """Una arista. kind decide si conecta pines de ejecución o de datos."""
    kind: Literal["exec", "data"]
    from_node: str                # id de instancia origen
    from_pin: str                 # nombre de pin de salida (del contrato)
    to_node: str                  # id de instancia destino
    to_pin: str                   # nombre de pin de entrada (del contrato)


class Variable(BaseModel):
    """Variable nombrada del grafo (nodos Get/Set)."""
    name: str
    type: str                     # nombre de tipo, p.ej. "str"


class GraphSignature(BaseModel):
    """Firma del grafo: qué expone Start (entradas) y End (salidas)."""
    inputs: dict[str, str] = Field(default_factory=dict)   # nombre -> tipo
    outputs: dict[str, str] = Field(default_factory=dict)  # nombre -> tipo


class VisualMeta(BaseModel):
    """Metadatos visuales, SEPARADOS de lo semántico. Opcional para el LLM."""
    positions: dict[str, list[float]] = Field(default_factory=dict)  # id -> [x, y]
    zoom: float = 1.0


class Graph(BaseModel):
    schema_version: str = "1.0"
    signature: GraphSignature = Field(default_factory=GraphSignature)
    variables: list[Variable] = Field(default_factory=list)
    instances: list[Instance]
    connections: list[Connection]
    visual: VisualMeta = Field(default_factory=VisualMeta)

    # Conveniencia para el motor: filtrar por tipo en memoria (línea trivial).
    def exec_connections(self) -> list[Connection]:
        return [c for c in self.connections if c.kind == "exec"]

    def data_connections(self) -> list[Connection]:
        return [c for c in self.connections if c.kind == "data"]


# ---------------------------------------------------------------------------
# Compatibilidad de tipos (decisión 4.2): igualdad | subtipo | conversión segura.
# El catálogo de conversiones son NODOS PUROS explícitos (honestidad visual).
# ---------------------------------------------------------------------------
SAFE_CONVERSIONS: dict[tuple[type, type], str] = {
    (int, float): "IntToFloat",
    (int, str): "ToStr",
    (float, str): "ToStr",
    (bool, str): "ToStr",
    (bool, int): "BoolToInt",
}


def check_type_compat(src_t: type, dst_t: type) -> tuple[str, str | None]:
    """('ok'|'convert'|'incompatible', nodo_conversion|None)."""
    # Any es comodín: compatible con cualquier tipo en ambas direcciones.
    if src_t is Any or dst_t is Any:
        return ("ok", None)
    if src_t == dst_t:
        return ("ok", None)
    if isinstance(src_t, type) and isinstance(dst_t, type) and issubclass(src_t, dst_t):
        return ("ok", None)
    if (src_t, dst_t) in SAFE_CONVERSIONS:
        return ("convert", SAFE_CONVERSIONS[(src_t, dst_t)])
    return ("incompatible", None)


# ---------------------------------------------------------------------------
# Validador: comprueba que el grafo es coherente con el contrato de Node.
# (NODE_REGISTRY se importa de flowprint_registry: fuente única.)
# ---------------------------------------------------------------------------
def validate_graph(graph: Graph) -> list[str]:
    errors: list[str] = []
    ids = {inst.id for inst in graph.instances}

    # ids únicos
    if len(ids) != len(graph.instances):
        errors.append("Hay ids de instancia duplicados.")

    # cada instancia usa un tipo conocido
    for inst in graph.instances:
        if inst.type not in NODE_REGISTRY:
            errors.append(f"Instancia '{inst.id}': tipo desconocido '{inst.type}'.")

    # cada conexión referencia instancias y pines que existen, del kind correcto
    for c in graph.connections:
        for role, nid in (("origen", c.from_node), ("destino", c.to_node)):
            if nid not in ids:
                errors.append(f"Conexión {c.kind}: instancia {role} '{nid}' no existe.")
        if c.from_node in ids and c.to_node in ids:
            src = NODE_REGISTRY.get(next(i.type for i in graph.instances if i.id == c.from_node))
            dst = NODE_REGISTRY.get(next(i.type for i in graph.instances if i.id == c.to_node))
            if src and dst:
                if c.kind == "exec":
                    if c.from_pin not in src.exec_outputs:
                        errors.append(f"'{c.from_node}' no tiene pin exec de salida '{c.from_pin}'.")
                    if c.to_pin not in dst.exec_inputs:
                        errors.append(f"'{c.to_node}' no tiene pin exec de entrada '{c.to_pin}'.")
                else:  # data
                    if c.from_pin not in src.Outputs.model_fields:
                        errors.append(f"'{c.from_node}' no tiene pin de datos de salida '{c.from_pin}'.")
                    elif c.to_pin not in dst.Inputs.model_fields:
                        errors.append(f"'{c.to_node}' no tiene pin de datos de entrada '{c.to_pin}'.")
                    else:
                        st = src.Outputs.model_fields[c.from_pin].annotation
                        dt = dst.Inputs.model_fields[c.to_pin].annotation
                        estado, conv = check_type_compat(st, dt)
                        if estado == "incompatible":
                            errors.append(
                                f"Tipos incompatibles {c.from_node}.{c.from_pin} "
                                f"({getattr(st,'__name__',st)}) -> {c.to_node}.{c.to_pin} "
                                f"({getattr(dt,'__name__',dt)})."
                            )
                        elif estado == "convert":
                            errors.append(
                                f"Falta conversión: inserta nodo '{conv}' entre "
                                f"{c.from_node}.{c.from_pin} y {c.to_node}.{c.to_pin}."
                            )


    # Pines de datos de entrada REQUERIDOS (sin default) deben tener conexión.
    # Si el campo tiene default, la ausencia de conexión es válida (usa el default).
    incoming: dict[tuple[str, str], bool] = {}
    for c in graph.connections:
        if c.kind == "data":
            incoming[(c.to_node, c.to_pin)] = True
    for inst in graph.instances:
        cls = NODE_REGISTRY.get(inst.type)
        if not cls or not hasattr(cls, "Inputs"):
            continue
        for pin_name, field in cls.Inputs.model_fields.items():
            if field.is_required() and not incoming.get((inst.id, pin_name)):
                errors.append(
                    f"'{inst.id}.{pin_name}' es un pin de datos requerido sin conexión "
                    f"y sin valor por defecto."
                )

    return errors


# ---------------------------------------------------------------------------
# Grafo de ejemplo (en dict, como lo produciría/editaría un LLM).
# Flujo: Equals compara dos strings (puro) -> Branch ramifica por el resultado.
# ---------------------------------------------------------------------------
EXAMPLE = {
    "schema_version": "1.0",
    "signature": {
        "inputs": {"texto": "str"},
        "outputs": {"resultado": "str"},
    },
    "variables": [],
    "instances": [
        {"id": "ka", "type": "Const", "config": {"value": "soporte"}},
        {"id": "kb", "type": "Const", "config": {"value": "soporte"}},
        {"id": "comparar_1", "type": "Equals", "config": {}},
        {"id": "branch_categoria", "type": "Branch", "config": {}},
    ],
    "connections": [
        {"kind": "data", "from_node": "ka", "from_pin": "value",
         "to_node": "comparar_1", "to_pin": "a"},
        {"kind": "data", "from_node": "kb", "from_pin": "value",
         "to_node": "comparar_1", "to_pin": "b"},
        # dato: salida 'result' de Equals -> entrada 'condition' de Branch
        {"kind": "data", "from_node": "comparar_1", "from_pin": "result",
         "to_node": "branch_categoria", "to_pin": "condition"},
    ],
    "visual": {
        "positions": {"comparar_1": [100, 100], "branch_categoria": [400, 100]},
        "zoom": 1.0,
    },
}


if __name__ == "__main__":
    import json

    # 1) Parseo: el JSON valida estructuralmente vía Pydantic.
    g = Graph.model_validate(EXAMPLE)
    print("Parseo OK. Instancias:", [i.id for i in g.instances])
    print("Conexiones exec:", len(g.exec_connections()), "| data:", len(g.data_connections()))

    # 2) Validación semántica contra el contrato de Node.
    errs = validate_graph(g)
    print("Errores grafo válido:", errs if errs else "ninguno")

    # 3) Grafo inválido: pin de datos que no existe.
    bad = json.loads(json.dumps(EXAMPLE))
    bad["connections"][0]["to_pin"] = "no_existe"
    gb = Graph.model_validate(bad)
    print("Errores grafo inválido:", validate_graph(gb))

    # 4) Round-trip a JSON (lo que persiste / edita el LLM).
    print("\nJSON serializado (extracto):")
    print(json.dumps(g.model_dump(), indent=2, ensure_ascii=False)[:400], "...")
