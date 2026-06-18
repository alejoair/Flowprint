# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install all dependencies (includes Ray)
pip install -e ".[dev]"

# Run all tests (must use python -m pytest, not bare pytest)
python -m pytest

# Run a single test file
python -m pytest tests/test_e2e.py

# Run a single test by name
python -m pytest tests/test_e2e.py::test_sequence_serial

# Launch editor (backend + frontend, opens browser, binds to localhost)
# No build step needed — frontend is plain HTML/JS served directly.
flowprint editor [--host 127.0.0.1] [--port 8000] [--reload]

# Launch API only, no browser (production / headless)
flowprint serve [--host 0.0.0.0] [--port 8000] [--reload]

# Build the package
hatch build
```

Both CLI commands must be run from the user's **project folder** — `graphs/` and `custom_nodes/` are created relative to `cwd`.

## Architecture

Flowprint is a multi-agent orchestration engine inspired by Unreal Engine's Blueprint execution model. It separates explicit **execution flow** (which node runs next) from **data flow** (values between nodes), both modeled as typed pins on nodes.

### Execution Model

The engine (`src/flowprint/engine.py`) maintains a LIFO stack of "execution fronts." On each step, it pops a node, resolves its data inputs via **pull evaluation**, executes the node, and pushes the resulting output pins back onto the stack.

**Execution context.** The engine uses a `ContextProtocol` interface backed by a Ray Actor (`_ContextActor`) in production and `LocalContext` in tests. All context methods are `async`. The Ray Actor is the authoritative store for variables and node state — thread-safe by Ray's single-threaded actor design.

**Two node categories:**
- **Effect nodes** (`is_pure=False`): Executed once when reached by execution flow; output stored in context via `set_node_output`.
- **Pure nodes** (`is_pure=True`): Evaluated on-demand (pull mechanism) each time an effect node reads their output. Not cached — this is intentional to support correct loop semantics (e.g., `ItemOf` returning a different element each iteration).

**Control instructions** (returned by every node in `NodeResult.control`):
- `Goto(pins)` — activate listed execution pins in serial order
- `Repeat(pins)` — activate pins AND re-enqueue the current node (used by `ForEach`)
- `Stop()` — terminate this execution path (all pure nodes return this)
- `Fork(pins)` — launch branches as parallel Ray tasks; engine waits for all to complete

### Graph Lifecycle

```
JSON graph → Graph.model_validate() → validate_graph() → build_engine() → engine.run()
```

1. `graph/schema.py` — Pydantic models for the JSON graph format (`Graph`, `Instance`, `Connection`, `PinDef`)
2. `graph/validation.py` — checks pin references, type compatibility, and missing required inputs before execution
3. `graph/loader.py` — `build_engine()` instantiates nodes from `NODE_REGISTRY`; `run_graph()` is the top-level entry point
4. `graph/registry.py` — `NODE_REGISTRY` maps string type names to `Node` classes; `load_custom_nodes()` scans `custom_nodes/*.py` at startup; both `CUSTOM_NODES_DIR` and `GRAPHS_DIR` resolve from `Path.cwd()`

### Start and End pins

`Start` and `End` expose **dynamic pins** based on `graph.signature`. The loader injects `input_names`/`output_names` into their config from the signature — no `GetVar`/`SetVar` needed to access graph inputs/outputs. Validation resolves their effective pins from the signature, not from the class-level Pydantic models.

### Type System

Data pins carry Python types (primitives or Pydantic `BaseModel` subclasses). `check_type_compat()` in `validation.py` returns:
- `"ok"` — same type or subtype
- `"convert"` — a known safe conversion exists (see `SAFE_CONVERSIONS`); the validator suggests a converter node
- `"incompatible"` — rejected at design time, before execution

### Adding a Node

1. Create a class inheriting from `Node` in `src/flowprint/nodes/`.
2. Define inner `Inputs`/`Outputs` Pydantic models and `exec_inputs`/`exec_outputs` tuples.
3. Set `is_pure = True` for data-only nodes (no side effects, no execution pins).
4. Implement `async execute(inputs, ctx) -> NodeResult`.
5. Register it in `src/flowprint/graph/registry.py`.

See `docs/crear-nodo.md` for examples (pure node, stateful node, branching node).

### Custom Nodes

Drop a `.py` file in the `custom_nodes/` directory (relative to cwd). Any class that inherits from `Node` and is defined in that module is auto-discovered on import. Custom nodes can shadow built-in types (a warning is printed). Use `refresh_custom_nodes()` to hot-reload without restarting.

### Graph Persistence

Graphs are stored as JSON files in `graphs/` (relative to cwd), one file per graph named `{name}.json`. Both `graphs/` and `custom_nodes/` are meant to be committed to git alongside the project.

### HTTP API (`src/flowprint/api.py`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/nodes` | All node types with pin metadata |
| GET/POST/PUT/DELETE | `/nodes/custom/{name}` | CRUD of custom node source files |
| GET | `/types/compatibility` | Safe type conversions |
| POST | `/graph/validate` | Validate a graph inline |
| WS | `/graph/run/ws` | Execute inline graph, stream events |
| GET/POST/PUT/DELETE | `/graphs/{name}` | CRUD of persisted graphs |
| POST | `/graphs/{name}/run` | Execute saved graph, returns final result |
| WS | `/graphs/{name}/run/ws` | Execute saved graph, stream events |

WebSocket protocol: client sends `{ graph?, args? }`, server emits `node_start`, `node_complete`, `error`, `cancelled`, `graph_complete` and closes.

### Public API

```python
from flowprint import run_graph, Graph

result = await run_graph(graph_dict_or_Graph, initial_args)
```

`Graph` is the Pydantic model for the full graph definition. See `docs/crear-grafo.md` for JSON graph examples.
