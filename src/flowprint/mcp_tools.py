from __future__ import annotations

import re
from typing import Any

from flowprint.graph.loader import run_graph
from flowprint.graph.registry import NODE_REGISTRY
from flowprint.graph.schema import Graph
from flowprint.graph.validation import SAFE_CONVERSIONS, validate_graph


def _type_name(t: Any) -> str:
    return getattr(t, "__name__", str(t)) if t is not None else "Any"


def _node_description(cls) -> str:
    doc = (cls.__doc__ or "").strip()
    return doc.split("\n")[0] if doc else cls.__name__


def _node_config_hint(cls) -> str:
    doc = (cls.__doc__ or "").strip()
    lines = [ln.strip() for ln in doc.split("\n") if "config." in ln.lower()]
    return "; ".join(lines)


def _converter_pins(conv_type: str) -> tuple[str, str]:
    """Returns (input_pin, output_pin) for a converter node."""
    cls = NODE_REGISTRY.get(conv_type)
    if not cls:
        return ("value", "result")
    d = cls.describe()
    in_pins = list(d["data_inputs"].keys())
    out_pins = list(d["data_outputs"].keys())
    return (in_pins[0] if in_pins else "value", out_pins[0] if out_pins else "result")


def register(mcp) -> None:
    """Register curated MCP tools on a FastMCP server instance."""

    @mcp.tool
    def catalog() -> list[dict]:
        """
        Returns the full catalog of available Flowprint node types with descriptions,
        pin names and types, config hints, and pure/effect classification.

        Use this first to discover what nodes are available before building a graph.
        Pure nodes (is_pure=true) have no exec pins and are connected only via data.
        Effect nodes (is_pure=false) have exec_inputs and exec_outputs that define execution order.
        """
        result = []
        for name, cls in NODE_REGISTRY.items():
            d = cls.describe()
            result.append({
                "type": name,
                "description": _node_description(cls),
                "config_hint": _node_config_hint(cls),
                "is_pure": d["is_pure"],
                "data_inputs": {k: _type_name(v) for k, v in d["data_inputs"].items()},
                "data_outputs": {k: _type_name(v) for k, v in d["data_outputs"].items()},
                "exec_inputs": list(d["exec_inputs"]),
                "exec_outputs": list(d["exec_outputs"]),
            })
        return result

    @mcp.tool
    def graph_schema() -> dict:
        """
        Returns the JSON structure of a valid Flowprint graph with field descriptions,
        rules, and two ready-to-use examples (minimal and with signature).

        Use this as a reference when building or debugging a graph JSON.
        """
        return {
            "field_descriptions": {
                "schema_version": "Always '1.0'.",
                "signature.inputs": (
                    "Named inputs the graph accepts. Each key becomes an output pin of the Start node. "
                    "The value is the Python type name ('str', 'int', 'float', 'bool', 'list', 'dict', 'Any')."
                ),
                "signature.outputs": (
                    "Named outputs the graph returns. Each key becomes an input pin of the End node."
                ),
                "variables": "Named variables accessible via GetVar/SetVar nodes. Usually [].",
                "instances": (
                    "List of node instances. Each needs: "
                    "'id' (unique descriptive string), "
                    "'type' (name from catalog), "
                    "'config' (dict of fixed parameters for that instance)."
                ),
                "connections": (
                    "Cables between nodes. "
                    "'kind': 'exec' (control flow) or 'data' (values). "
                    "'from_node'/'to_node': instance ids. "
                    "'from_pin'/'to_pin': pin names from the catalog."
                ),
                "visual": "Canvas layout data. Use {} to ignore.",
            },
            "rules": [
                "Every graph needs exactly one Start and one End instance.",
                "Start has no exec input; its exec output pin is named 'out'.",
                "End has no exec output; its exec input pin is named 'in'.",
                "Most effect nodes have exec_input='in' and exec_output='out'. Always check the catalog for the exact pin names.",
                "Pure nodes (is_pure=true) have no exec pins — connect them only via data connections.",
                "Required data inputs (no default) must have a data connection.",
                "Data pin types must be compatible. Use converter nodes (IntToFloat, ToStr, BoolToInt) when needed.",
            ],
            "minimal_example": {
                "schema_version": "1.0",
                "signature": {"inputs": {}, "outputs": {}},
                "variables": [],
                "instances": [
                    {"id": "start", "type": "Start", "config": {}},
                    {"id": "end",   "type": "End",   "config": {}}
                ],
                "connections": [
                    {"kind": "exec", "from_node": "start", "from_pin": "out",
                     "to_node": "end", "to_pin": "in"}
                ],
                "visual": {}
            },
            "example_with_signature": {
                "description": "Graph that receives a 'name' string and returns a 'greeting' string.",
                "graph": {
                    "schema_version": "1.0",
                    "signature": {
                        "inputs":  {"name": "str"},
                        "outputs": {"greeting": "str"}
                    },
                    "variables": [],
                    "instances": [
                        {"id": "start",  "type": "Start",  "config": {}},
                        {"id": "concat", "type": "Concat", "config": {}},
                        {"id": "end",    "type": "End",    "config": {}}
                    ],
                    "connections": [
                        {"kind": "exec", "from_node": "start",  "from_pin": "out",
                         "to_node": "concat", "to_pin": "in"},
                        {"kind": "exec", "from_node": "concat", "from_pin": "out",
                         "to_node": "end", "to_pin": "in"},
                        {"kind": "data", "from_node": "start",  "from_pin": "name",
                         "to_node": "concat", "to_pin": "b"},
                        {"kind": "data", "from_node": "concat", "from_pin": "value",
                         "to_node": "end", "to_pin": "greeting"}
                    ],
                    "visual": {}
                }
            }
        }

    @mcp.tool
    def get_node_info(node_type: str) -> dict:
        """
        Returns detailed information about a specific node type: full description,
        all pin names and types, config keys, and an example instance snippet.

        Args:
            node_type: The node type name from the catalog (e.g. 'Branch', 'ForLoop', 'Const').
        """
        cls = NODE_REGISTRY.get(node_type)
        if not cls:
            return {
                "error": f"Node type '{node_type}' not found.",
                "available_types": sorted(NODE_REGISTRY.keys()),
            }
        d = cls.describe()
        return {
            "type": node_type,
            "description": (cls.__doc__ or "").strip(),
            "is_pure": d["is_pure"],
            "data_inputs":  {k: _type_name(v) for k, v in d["data_inputs"].items()},
            "data_outputs": {k: _type_name(v) for k, v in d["data_outputs"].items()},
            "exec_inputs":  list(d["exec_inputs"]),
            "exec_outputs": list(d["exec_outputs"]),
            "config_hint": _node_config_hint(cls),
            "example_instance": {
                "id": f"{node_type.lower()}_1",
                "type": node_type,
                "config": {}
            },
        }

    @mcp.tool
    async def validate_and_run(graph: dict, args: dict | None = None) -> dict:
        """
        Validates a graph and, if valid, runs it and returns the result.
        Use this instead of separate validate + run calls to save round-trips.

        Returns {status, errors, result} where status is one of:
        - 'ok': graph is valid and ran successfully; result contains the output.
        - 'schema_error': the graph JSON doesn't match the expected schema.
        - 'validation_errors': schema is valid but semantic checks failed (call explain_graph_errors for fix hints).
        - 'runtime_error': graph ran but raised an exception.

        Args:
            graph: The graph definition dict.
            args: Optional dict of input arguments matching graph.signature.inputs.
        """
        try:
            g = Graph.model_validate(graph)
        except Exception as e:
            return {"status": "schema_error", "errors": [str(e)], "result": None}

        errors = validate_graph(g)
        if errors:
            return {"status": "validation_errors", "errors": errors, "result": None}

        try:
            result = await run_graph(g, args)
            return {"status": "ok", "errors": [], "result": result}
        except Exception as e:
            return {"status": "runtime_error", "errors": [str(e)], "result": None}

    @mcp.tool
    def explain_graph_errors(graph: dict) -> list[dict]:
        """
        Validates a graph and returns enriched errors with actionable fix suggestions.
        Each item includes the original error message, an error type classification,
        a human-readable suggestion, and when possible a concrete JSON snippet to apply.

        Returns an empty list if the graph is valid.

        Args:
            graph: The graph definition dict to validate.
        """
        try:
            g = Graph.model_validate(graph)
        except Exception as e:
            return [{
                "error": str(e),
                "type": "schema_error",
                "suggestion": "Fix the graph JSON structure. Call graph_schema for the correct format.",
                "fix_json": None,
            }]

        raw_errors = validate_graph(g)
        if not raw_errors:
            return []

        # Pre-index instances by id for quick lookup
        inst_by_id = {inst.id: inst for inst in g.instances}

        # Regex patterns for known error shapes
        _conv_re = re.compile(
            r"Falta conversión: inserta nodo '(\w+)' entre (\S+)\.(\S+) y (\S+)\.(\S+)\."
        )
        _req_re = re.compile(r"'(\w+)\.(\w+)' es un pin de datos requerido")
        _incompat_re = re.compile(
            r"Tipos incompatibles (\S+)\.(\S+) \((\w+)\) -> (\S+)\.(\S+) \((\w+)\)\."
        )
        _unknown_type_re = re.compile(r"tipo desconocido '(\w+)'")

        result = []
        for error in raw_errors:
            # --- Missing converter ---
            m = _conv_re.search(error)
            if m:
                conv_type, from_node, from_pin, to_node, to_pin = m.groups()
                conv_id = f"conv_{from_node}_{to_node}"
                in_pin, out_pin = _converter_pins(conv_type)
                result.append({
                    "error": error,
                    "type": "missing_converter",
                    "suggestion": (
                        f"Insert a '{conv_type}' node between {from_node}.{from_pin} "
                        f"and {to_node}.{to_pin}, then update the connections to route through it."
                    ),
                    "fix_json": {
                        "add_instance": {"id": conv_id, "type": conv_type, "config": {}},
                        "remove_connection": {
                            "kind": "data", "from_node": from_node, "from_pin": from_pin,
                            "to_node": to_node, "to_pin": to_pin,
                        },
                        "add_connections": [
                            {"kind": "data", "from_node": from_node, "from_pin": from_pin,
                             "to_node": conv_id, "to_pin": in_pin},
                            {"kind": "data", "from_node": conv_id, "from_pin": out_pin,
                             "to_node": to_node, "to_pin": to_pin},
                        ],
                    },
                })
                continue

            # --- Required pin without connection ---
            m = _req_re.search(error)
            if m:
                node_id, pin_name = m.groups()
                pin_type = "Any"
                inst = inst_by_id.get(node_id)
                if inst:
                    cls = NODE_REGISTRY.get(inst.type)
                    if cls and hasattr(cls, "Inputs"):
                        field = cls.Inputs.model_fields.get(pin_name)
                        if field:
                            pin_type = _type_name(field.annotation)
                result.append({
                    "error": error,
                    "type": "missing_required_input",
                    "suggestion": (
                        f"Connect a data source of type '{pin_type}' to {node_id}.{pin_name}, "
                        f"or add a Const node with the desired value."
                    ),
                    "fix_json": {
                        "option_const_node": {
                            "add_instance": {
                                "id": f"const_{pin_name}",
                                "type": "Const",
                                "config": {"value": f"<{pin_type} value here>"},
                            },
                            "add_connection": {
                                "kind": "data",
                                "from_node": f"const_{pin_name}", "from_pin": "value",
                                "to_node": node_id, "to_pin": pin_name,
                            },
                        }
                    },
                })
                continue

            # --- Incompatible types ---
            m = _incompat_re.search(error)
            if m:
                from_node, from_pin, src_type, to_node, to_pin, dst_type = m.groups()
                converters = [
                    {"from": _type_name(s), "to": _type_name(d), "converter": c}
                    for (s, d), c in SAFE_CONVERSIONS.items()
                ]
                result.append({
                    "error": error,
                    "type": "incompatible_types",
                    "suggestion": (
                        f"'{src_type}' and '{dst_type}' have no safe automatic converter. "
                        f"Redesign the graph to use compatible types. "
                        f"Available safe converters are listed in fix_json."
                    ),
                    "fix_json": {"available_converters": converters},
                })
                continue

            # --- Unknown node type ---
            m = _unknown_type_re.search(error)
            if m:
                unknown = m.group(1)
                result.append({
                    "error": error,
                    "type": "unknown_node_type",
                    "suggestion": (
                        f"'{unknown}' is not registered. Call catalog() to see all available types, "
                        f"or create it as a custom node via POST /nodes/custom/{{name}}."
                    ),
                    "fix_json": None,
                })
                continue

            # --- Generic fallback ---
            result.append({
                "error": error,
                "type": "other",
                "suggestion": error,
                "fix_json": None,
            })

        return result
