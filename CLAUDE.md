# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_e2e.py

# Run a single test by name
pytest tests/test_e2e.py::test_sequence_serial

# Build the package
hatch build
```

## Architecture

Flowprint is a multi-agent orchestration engine inspired by Unreal Engine's Blueprint execution model. It separates explicit **execution flow** (which node runs next) from **data flow** (values between nodes), both modeled as typed pins on nodes.

### Execution Model

The engine (`src/flowprint/engine.py`) maintains a LIFO stack of "execution fronts." On each step, it pops a node, resolves its data inputs via **pull evaluation**, executes the node, and pushes the resulting output pins back onto the stack.

**Two node categories:**
- **Effect nodes** (`is_pure=False`): Executed once when reached by execution flow; output stored in `ExecutionContext`.
- **Pure nodes** (`is_pure=True`): Evaluated on-demand (pull mechanism) each time an effect node reads their output. Not cached — this is intentional to support correct loop semantics (e.g., `ItemOf` returning a different element each iteration).

**Control instructions** (returned by every node in `NodeResult.control`):
- `Goto(pins)` — activate listed execution pins in serial order
- `Repeat(pins)` — activate pins AND re-enqueue the current node (used by `ForEach`)
- `Stop()` — terminate this execution path (all pure nodes return this)
- `Fork(pins)` — parallel activation (reserved, not yet used)

### Graph Lifecycle

```
JSON graph → Graph.model_validate() → validate_graph() → build_engine() → engine.run()
```

1. `graph/schema.py` — Pydantic models for the JSON graph format (`Graph`, `Instance`, `Connection`, `PinDef`)
2. `graph/validation.py` — checks pin references, type compatibility, and missing required inputs before execution
3. `graph/loader.py` — `build_engine()` instantiates nodes from `NODE_REGISTRY`; `run_graph()` is the top-level entry point
4. `graph/registry.py` — `NODE_REGISTRY` maps string type names to `Node` classes; `load_custom_nodes()` scans `custom_nodes/*.py` at startup

### Type System

Data pins carry Python types (primitives or Pydantic `BaseModel` subclasses). `check_type_compat()` in `validation.py` returns:
- `"ok"` — same type or subtype
- `"convert"` — a known safe conversion exists (see `SAFE_CONVERSIONS`); the validator suggests a converter node
- `"incompatible"` — rejected at design time, before execution

### Adding a Node

1. Create a class inheriting from `Node` in `src/flowprint/nodes/`.
2. Define `INPUT_PINS`, `OUTPUT_PINS`, `EXEC_IN_PINS`, `EXEC_OUT_PINS` as class-level `PinDef` lists.
3. Set `is_pure = True` for data-only nodes (no side effects, no execution pins).
4. Implement `async execute(inputs, ctx) -> NodeResult`.
5. Register it in `src/flowprint/graph/registry.py`.

See `docs/crear-nodo.md` for examples (pure node, stateful node, branching node).

### Custom Nodes

Drop a `.py` file in the `custom_nodes/` directory. Any class that inherits from `Node` and is defined in that module is auto-discovered on import. Custom nodes can shadow built-in types (a warning is printed).

### Public API

```python
from flowprint import run_graph, Graph

result = await run_graph(graph_dict_or_Graph, initial_args)
```

`Graph` is the Pydantic model for the full graph definition. See `docs/crear-grafo.md` for JSON graph examples.
