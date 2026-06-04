"""Cargador: el puente que faltaba.

    Graph (JSON validado)  ->  instancias de Node (vía NODE_REGISTRY, con config)
                           ->  exec_edges / data_edges (tuplas que el motor consume)
                           ->  Engine listo para .run()

Decisiones que cierra:
- `config` uniforme: Instance.config se pasa tal cual a Node(instance_id, config).
  Los nodos leen sus parámetros de self.config (Const -> config['value'], etc.).
- Sin nodos a mano: el motor ya no recibe diccionarios construidos manualmente;
  todo sale del Graph.
- Validación antes de instanciar: se rechaza un grafo inválido (pin inexistente,
  tipo desconocido) ANTES de tocar el motor.
"""

from __future__ import annotations

from flowprint_engine import Engine
from flowprint_graph_schema import Graph, validate_graph
from flowprint_node_contract import Node
from flowprint_registry import NODE_REGISTRY


def build_engine(graph: Graph) -> Engine:
    """Instancia los nodos del grafo y produce un Engine listo para correr."""
    errors = validate_graph(graph)
    if errors:
        raise ValueError("Grafo inválido:\n  - " + "\n  - ".join(errors))

    # 1) Instanciar cada nodo vía el registro, pasando su config tal cual.
    #    Start/End reciben además la firma del grafo (signature) en su config,
    #    para exponer inputs / componer el resultado tipado.
    nodes: dict[str, Node] = {}
    input_names = list(graph.signature.inputs.keys())
    output_names = list(graph.signature.outputs.keys())
    for inst in graph.instances:
        cls = NODE_REGISTRY[inst.type]      # validado: el tipo existe
        config = dict(inst.config)
        if inst.type == "Start":
            config.setdefault("input_names", input_names)
        elif inst.type == "End":
            config.setdefault("output_names", output_names)
        nodes[inst.id] = cls(inst.id, config)

    # 2) Traducir conexiones a las tuplas que el motor consume.
    exec_edges = [
        (c.from_node, c.from_pin, c.to_node, c.to_pin)
        for c in graph.exec_connections()
    ]
    data_edges = [
        (c.from_node, c.from_pin, c.to_node, c.to_pin)
        for c in graph.data_connections()
    ]
    return Engine(nodes, exec_edges, data_edges)


def find_start(graph: Graph) -> str:
    """Localiza el nodo de arranque (tipo Start) del grafo."""
    starts = [i.id for i in graph.instances if i.type == "Start"]
    if len(starts) != 1:
        raise ValueError(f"El grafo debe tener exactamente un Start; encontrados: {starts}")
    return starts[0]


async def run_graph(graph: Graph, args: dict | None = None):
    """Conveniencia: construye el motor y ejecuta desde el Start con args opcionales."""
    engine = build_engine(graph)
    return await engine.run(find_start(graph), args)
