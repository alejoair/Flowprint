# Flowprint

A visual editor for building and running multi-agent workflows — drag, connect, run.

Flowprint separates **execution flow** (which node runs next) from **data flow** (values between nodes), both represented as typed pins on each node. The model is inspired by Unreal Engine's Blueprint system.

---

## Quick Start

```bash
pip install -e ".[dev]"
flowprint editor
```

This starts the editor and opens a browser at `http://localhost:8000/ui/`. Both the `graphs/` and `custom_nodes/` directories are created in your current working directory — commit them alongside your project.

---

## Editor Walkthrough

### Layout

```
┌─────────────────────────────────────────────┐
│  Toolbar: New · Open · Save · Signature · ▶ │
├──────────┬───────────────────────┬──────────┤
│          │                       │  Config  │
│ Nodes    │       Canvas          │  Panel   │
│ palette  │                       │ (on sel) │
│          │                       │          │
├──────────┴───────────────────────┴──────────┤
│  Execution log (opens on Run)               │
└─────────────────────────────────────────────┘
```

### Building a graph

1. **Drag** a node from the left palette onto the canvas.
2. **Connect pins** by dragging from one handle to another.
   - Gray square pins = execution flow (what runs next).
   - Colored circle pins = data (typed values: str, int, float, bool, list, dict, Any).
3. **Click a node** to open the Config Panel on the right and set parameters (e.g. model name, temperature).
4. Define what your graph accepts and returns with the **Signature** button — this configures the `Start` and `End` nodes.

### Running

Click **▶ Run**. The Execution Panel opens at the bottom and streams live events:

| Badge | Meaning |
|-------|---------|
| `node_start` | Node began executing |
| `node_complete` | Node finished, output available |
| `graph_complete` | All done — final result shown as JSON |
| `error` | Node threw an exception |
| `cancelled` | You clicked Stop |

Click **■ Stop** at any time to cancel.

### Saving and opening graphs

- **Save** (or `Ctrl+S`) — prompts for a name and persists to `graphs/<name>.json`.
- **Open** — dropdown of all saved graphs; click to load.
- **New** (or `Ctrl+N`) — blank canvas with a wired `Start → End`.
- **Delete** — removes the currently open graph file.

---

## Execution Model

Every node has optional **exec pins** (in/out) that control order, and **data pins** that carry typed values.

- **Effect nodes** (`is_pure=False`) — run once when execution reaches them; output is stored in context for downstream nodes.
- **Pure nodes** (`is_pure=True`) — evaluated on demand each time a downstream node reads their output. Not cached, so they re-evaluate on every read (important for loops like `ForEach`).

Control is returned by every node as part of its result:

| Instruction | Effect |
|-------------|--------|
| `Goto(pins)` | Activate the listed exec output pins in order |
| `Repeat(pins)` | Activate pins and re-enqueue this node (used by `ForEach`) |
| `Stop()` | End this execution path |

---

## Custom Nodes

### In the editor

Click **⚙ Nodes** in the toolbar to open the Custom Node Editor. Click **+ New node**, choose a name, and edit the generated Python template directly in the browser. Hit **Save** — the node type appears in the palette immediately.

### In code

Drop a `.py` file in `custom_nodes/` (in your project folder). Any class that inherits from `Node` is auto-discovered on startup. Use `refresh_custom_nodes()` to hot-reload without restarting the server.

```python
from pydantic import BaseModel
from flowprint.core.node import Node, NodeResult, ExecutionContext
from flowprint.core.control import Stop

class UpperCase(Node):
    """Converts a string to uppercase."""

    class Inputs(BaseModel):
        text: str = ""

    class Outputs(BaseModel):
        result: str = ""

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(result=inputs.text.upper()), Stop())
```

See [`docs/crear-nodo.md`](docs/crear-nodo.md) for examples with execution pins, branching, and stateful nodes.

---

## Python API

```python
from flowprint import run_graph, Graph

result = await run_graph(graph_dict_or_Graph, initial_args)
```

`Graph` is the Pydantic model for the full graph definition. See [`docs/crear-grafo.md`](docs/crear-grafo.md) for JSON graph examples.

---

## HTTP API

Run headless (no browser) with:

```bash
flowprint serve [--host 0.0.0.0] [--port 8000]
```

Key endpoints:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/nodes` | All node types with pin metadata |
| `GET/POST/PUT/DELETE` | `/graphs/{name}` | CRUD for saved graphs |
| `POST` | `/graphs/{name}/run` | Execute a saved graph, returns final result |
| `WS` | `/graphs/{name}/run/ws` | Execute and stream events |
| `GET/POST/PUT/DELETE` | `/nodes/custom/{name}` | CRUD for custom node source files |
| `POST` | `/graph/validate` | Validate a graph before running |

WebSocket protocol: client sends `{ "graph"?: {...}, "args"?: {...} }`, server emits `node_start`, `node_complete`, `error`, `cancelled`, `graph_complete` and closes.

Full reference: [`docs/api.md`](docs/api.md).

---

## Development

```bash
pip install -e ".[dev]"

# Run tests
python -m pytest

# Run a single test
python -m pytest tests/test_e2e.py::test_sequence_serial

# Build package
hatch build
```

**Requirements:** Python 3.11+

The frontend is plain HTML/JS (React via ESM import map, no build step). Changes to `src/flowprint/static/` are served directly — refresh the browser.

---

## Docs

- [`docs/crear-nodo.md`](docs/crear-nodo.md) — How to write a node (pure, effect, branching, stateful)
- [`docs/crear-grafo.md`](docs/crear-grafo.md) — Graph JSON format and examples
- [`docs/api.md`](docs/api.md) — Full HTTP/WS API reference
- [`docs/spec.md`](docs/spec.md) — Engine design specification
