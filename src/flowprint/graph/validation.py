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


def _effective_exec_outputs(cls, inst) -> tuple[str, ...]:
    """Exec output pins for a node, resolving dynamic configs (Switch*)."""
    if getattr(cls, "_dynamic_exec", False):
        try:
            return cls(inst.id, inst.config).exec_outputs
        except Exception:
            pass
    return cls.exec_outputs


def _effective_output_pins(cls, inst, graph: Graph) -> set[str]:
    """Pin names a node exposes as data outputs, accounting for dynamic models."""
    if cls.__name__ == "Start":
        names = inst.config.get("input_names") or list(graph.signature.inputs.keys())
        if names:
            return set(names)
    return set(cls.Outputs.model_fields.keys()) if hasattr(cls, "Outputs") else set()


def _effective_input_pins(cls, inst, graph: Graph) -> set[str]:
    """Pin names a node accepts as data inputs, accounting for dynamic models."""
    if cls.__name__ == "End":
        names = inst.config.get("output_names") or list(graph.signature.outputs.keys())
        if names:
            return set(names)
    return set(cls.Inputs.model_fields.keys()) if hasattr(cls, "Inputs") else set()


def validate_graph(graph: Graph) -> list[str]:
    errors: list[str] = []
    ids = {inst.id for inst in graph.instances}
    inst_by_id = {inst.id: inst for inst in graph.instances}

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
            src_inst = inst_by_id[c.from_node]
            dst_inst = inst_by_id[c.to_node]
            src = NODE_REGISTRY.get(src_inst.type)
            dst = NODE_REGISTRY.get(dst_inst.type)
            if src and dst:
                if c.kind == "exec":
                    if c.from_pin not in _effective_exec_outputs(src, src_inst):
                        errors.append(f"'{c.from_node}' no tiene pin exec de salida '{c.from_pin}'.")
                    if c.to_pin not in dst.exec_inputs:
                        errors.append(f"'{c.to_node}' no tiene pin exec de entrada '{c.to_pin}'.")
                else:
                    out_pins = _effective_output_pins(src, src_inst, graph)
                    in_pins = _effective_input_pins(dst, dst_inst, graph)
                    if c.from_pin not in out_pins:
                        errors.append(f"'{c.from_node}' no tiene pin de datos de salida '{c.from_pin}'.")
                    elif c.to_pin not in in_pins:
                        errors.append(f"'{c.to_node}' no tiene pin de datos de entrada '{c.to_pin}'.")
                    else:
                        # Type check — Any on dynamic pins skips check
                        src_fields = src.Outputs.model_fields if hasattr(src, "Outputs") else {}
                        dst_fields = dst.Inputs.model_fields if hasattr(dst, "Inputs") else {}
                        if c.from_pin in src_fields and c.to_pin in dst_fields:
                            st = src_fields[c.from_pin].annotation
                            dt = dst_fields[c.to_pin].annotation
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
        # Dynamic pins (Start/End) are all optional — skip required-pin check for them
        if cls.__name__ in ("Start", "End"):
            continue
        for pin_name, f in cls.Inputs.model_fields.items():
            if f.is_required() and not incoming.get((inst.id, pin_name)):
                errors.append(
                    f"'{inst.id}.{pin_name}' es un pin de datos requerido sin conexión "
                    f"y sin valor por defecto."
                )

    return errors
