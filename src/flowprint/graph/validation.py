from __future__ import annotations

from typing import Any

from flowprint.graph.registry import NODE_REGISTRY
from flowprint.graph.schema import Graph

SAFE_CONVERSIONS: dict[tuple[type, type], str] = {
    (int, float): "IntToFloat",
    (int, str): "ToStr",
    (float, str): "ToStr",
    (bool, str): "ToStr",
    (bool, int): "BoolToInt",
}


def check_type_compat(src_t: type, dst_t: type) -> tuple[str, str | None]:
    if src_t is Any or dst_t is Any:
        return ("ok", None)
    if src_t == dst_t:
        return ("ok", None)
    if isinstance(src_t, type) and isinstance(dst_t, type) and issubclass(src_t, dst_t):
        return ("ok", None)
    if (src_t, dst_t) in SAFE_CONVERSIONS:
        return ("convert", SAFE_CONVERSIONS[(src_t, dst_t)])
    return ("incompatible", None)


def validate_graph(graph: Graph) -> list[str]:
    errors: list[str] = []
    ids = {inst.id for inst in graph.instances}

    if len(ids) != len(graph.instances):
        errors.append("Hay ids de instancia duplicados.")

    for inst in graph.instances:
        if inst.type not in NODE_REGISTRY:
            errors.append(f"Instancia '{inst.id}': tipo desconocido '{inst.type}'.")

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
                else:
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
                                f"({getattr(st, '__name__', st)}) -> {c.to_node}.{c.to_pin} "
                                f"({getattr(dt, '__name__', dt)})."
                            )
                        elif estado == "convert":
                            errors.append(
                                f"Falta conversión: inserta nodo '{conv}' entre "
                                f"{c.from_node}.{c.from_pin} y {c.to_node}.{c.to_pin}."
                            )

    incoming: dict[tuple[str, str], bool] = {}
    for c in graph.connections:
        if c.kind == "data":
            incoming[(c.to_node, c.to_pin)] = True
    for inst in graph.instances:
        cls = NODE_REGISTRY.get(inst.type)
        if not cls or not hasattr(cls, "Inputs"):
            continue
        for pin_name, f in cls.Inputs.model_fields.items():
            if f.is_required() and not incoming.get((inst.id, pin_name)):
                errors.append(
                    f"'{inst.id}.{pin_name}' es un pin de datos requerido sin conexión "
                    f"y sin valor por defecto."
                )

    return errors
