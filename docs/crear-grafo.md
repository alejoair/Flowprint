# Cómo crear un grafo en JSON

Un grafo es un archivo JSON que describe qué nodos hay y cómo están conectados.
Es la fuente de verdad: el motor lo carga, lo valida y lo ejecuta.

## Estructura raíz

```json
{
  "schema_version": "1.0",
  "signature": { "inputs": {}, "outputs": {} },
  "variables": [],
  "instances": [...],
  "connections": [...],
  "visual": { "positions": {}, "zoom": 1.0 }
}
```

| Campo | Qué es |
|---|---|
| `signature` | firma del grafo: qué recibe y qué devuelve (lo hace invocable como función) |
| `variables` | variables con nombre accesibles con `GetVar`/`SetVar` |
| `instances` | los nodos del grafo |
| `connections` | los cables entre nodos |
| `visual` | posiciones en el canvas (ignorado por el motor) |

---

## `instances` — los nodos

Cada instancia tiene tres campos:

```json
{
  "id":     "clasificador_1",
  "type":   "MiAgente",
  "config": { "model": "gpt-4o", "temperatura": 0.5 }
}
```

| Campo | Regla |
|---|---|
| `id` | nombre libre y único dentro del grafo; usa nombres descriptivos (`clasificador_1`, `branch_categoria`) |
| `type` | debe coincidir exactamente con la clave en `NODE_REGISTRY` |
| `config` | valores fijos de la instancia; llegan al nodo como `self.config` |

Para saber qué `type` usar, consulta `NODE_REGISTRY` o el nombre de la clase.
Para saber qué poner en `config`, mira `self.config.get(...)` en el `execute` del nodo.

---

## `connections` — los cables

Cada conexión tiene cinco campos:

```json
{
  "kind":      "exec",
  "from_node": "start",
  "from_pin":  "out",
  "to_node":   "mi_agente",
  "to_pin":    "in"
}
```

| Campo | Valores |
|---|---|
| `kind` | `"exec"` (orden de ejecución) o `"data"` (valor tipado) |
| `from_node` | `id` de la instancia origen |
| `from_pin` | nombre de pin de salida del nodo origen |
| `to_node` | `id` de la instancia destino |
| `to_pin` | nombre de pin de entrada del nodo destino |

Los nombres de pin vienen del contrato del nodo:
- Pines de ejecución → `exec_outputs` / `exec_inputs` de la clase
- Pines de datos → nombres de los campos de `Outputs` / `Inputs`

El validador rechaza el grafo si un pin no existe en el contrato.

---

## `signature` — la firma del grafo

Define qué entra y qué sale. Convierte el grafo en algo invocable como función.

```json
"signature": {
  "inputs":  { "texto": "str", "n": "int" },
  "outputs": { "respuesta": "str" }
}
```

- `inputs` → el nodo `Start` expone cada clave como un **pin de datos de salida** (conectables directamente a otros nodos)
- `outputs` → el nodo `End` expone cada clave como un **pin de datos de entrada** (recibe el valor por conexión directa)

Para pasar argumentos al grafo al ejecutarlo:

```python
resultado = await run_graph(graph, args={"texto": "hola", "n": 3})
```

---

## Ejemplos

### Ejemplo 1 — Nodo simple: entrada → agente → salida

```
Start → MiAgente → End
```

```json
{
  "schema_version": "1.0",
  "signature": {
    "inputs":  { "pregunta": "str" },
    "outputs": { "respuesta": "str" }
  },
  "variables": [],
  "instances": [
    { "id": "start",     "type": "Start",    "config": {} },
    { "id": "agente",    "type": "MiAgente", "config": { "model": "gpt-4o" } },
    { "id": "end",       "type": "End",      "config": {} }
  ],
  "connections": [
    { "kind": "exec", "from_node": "start",  "from_pin": "out", "to_node": "agente", "to_pin": "in" },
    { "kind": "exec", "from_node": "agente", "from_pin": "out", "to_node": "end",    "to_pin": "in" },
    { "kind": "data", "from_node": "start",  "from_pin": "pregunta", "to_node": "agente", "to_pin": "prompt" }
  ],
  "visual": { "positions": {}, "zoom": 1.0 }
}
```

> `start` expone los inputs de la `signature` como pines de datos de salida.
> Aquí `from_pin: "pregunta"` es el nombre del input declarado en `signature.inputs`.

---

### Ejemplo 2 — Bifurcación: Branch con dos ramas y dos End

```
Start → Clasificador → Branch → [Agente Soporte → End]
                              → [Agente Ventas  → End]
```

```json
{
  "schema_version": "1.0",
  "signature": {
    "inputs":  { "mensaje": "str" },
    "outputs": { "respuesta": "str" }
  },
  "variables": [],
  "instances": [
    { "id": "start",       "type": "Start",       "config": {} },
    { "id": "clasif",      "type": "Clasificador", "config": {} },
    { "id": "branch",      "type": "Branch",       "config": {} },
    { "id": "soporte",     "type": "AgenteEsp",    "config": { "rol": "soporte" } },
    { "id": "ventas",      "type": "AgenteEsp",    "config": { "rol": "ventas" } },
    { "id": "end_soporte", "type": "End",          "config": {} },
    { "id": "end_ventas",  "type": "End",          "config": {} }
  ],
  "connections": [
    { "kind": "exec", "from_node": "start",   "from_pin": "out",   "to_node": "clasif",  "to_pin": "in"  },
    { "kind": "exec", "from_node": "clasif",  "from_pin": "out",   "to_node": "branch",  "to_pin": "in"  },
    { "kind": "exec", "from_node": "branch",  "from_pin": "true",  "to_node": "soporte", "to_pin": "in"  },
    { "kind": "exec", "from_node": "branch",  "from_pin": "false", "to_node": "ventas",  "to_pin": "in"  },
    { "kind": "exec", "from_node": "soporte", "from_pin": "out",   "to_node": "end_soporte", "to_pin": "in" },
    { "kind": "exec", "from_node": "ventas",  "from_pin": "out",   "to_node": "end_ventas",  "to_pin": "in" },
    { "kind": "data", "from_node": "start",   "from_pin": "mensaje",   "to_node": "clasif",  "to_pin": "texto" },
    { "kind": "data", "from_node": "clasif",  "from_pin": "es_soporte","to_node": "branch",  "to_pin": "condition" },
    { "kind": "data", "from_node": "start",   "from_pin": "mensaje",   "to_node": "soporte", "to_pin": "texto" },
    { "kind": "data", "from_node": "start",   "from_pin": "mensaje",   "to_node": "ventas",  "to_pin": "texto" }
  ],
  "visual": { "positions": {}, "zoom": 1.0 }
}
```

---

### Ejemplo 3 — Loop: ForEach sobre una lista

```
Start → ForEach → [body]    → Agente → (vuelve al ForEach)
               → [completed]→ End
```

```json
{
  "schema_version": "1.0",
  "signature": { "inputs": {}, "outputs": {} },
  "variables": [],
  "instances": [
    { "id": "start",  "type": "Start",     "config": {} },
    { "id": "loop",   "type": "ForEach",   "config": {} },
    { "id": "item",   "type": "ItemOf",    "config": { "foreach_id": "loop" } },
    { "id": "agente", "type": "MiAgente",  "config": {} },
    { "id": "end",    "type": "End",       "config": {} }
  ],
  "connections": [
    { "kind": "exec", "from_node": "start",  "from_pin": "out",       "to_node": "loop",   "to_pin": "in" },
    { "kind": "exec", "from_node": "loop",   "from_pin": "body",      "to_node": "agente", "to_pin": "in" },
    { "kind": "exec", "from_node": "loop",   "from_pin": "completed", "to_node": "end",    "to_pin": "in" },
    { "kind": "data", "from_node": "item",   "from_pin": "value",     "to_node": "agente", "to_pin": "prompt" }
  ],
  "visual": { "positions": {}, "zoom": 1.0 }
}
```

> `ItemOf` es un nodo puro que lee el elemento actual del loop desde el contexto.
> `config.foreach_id` le dice de qué `ForEach` leer.

---

### Ejemplo 4 — Variables: evitar cable spaghetti con `SetVar`/`GetVar`

Cuando un resultado se necesita en varios nodos lejanos, evita cablearlo
a través de intermedios. Usa `SetVar` para guardarlo y `GetVar` para leerlo.

```json
"instances": [
  { "id": "set_plan", "type": "SetVar", "config": { "var": "plan" } },
  { "id": "get_plan", "type": "GetVar", "config": { "var": "plan" } }
],
"connections": [
  { "kind": "data", "from_node": "planificador", "from_pin": "resultado",
    "to_node": "set_plan", "to_pin": "value" },
  { "kind": "data", "from_node": "get_plan", "from_pin": "value",
    "to_node": "agente_paso_b", "to_pin": "contexto" }
]
```

---

## Cómo cargar y ejecutar un grafo

```python
import json
import asyncio
from flowprint.graph.schema import Graph
from flowprint.graph.loader import run_graph

with open("mi_grafo.json") as f:
    data = json.load(f)

graph = Graph.model_validate(data)   # valida la estructura
resultado = asyncio.run(run_graph(graph, args={"pregunta": "¿Qué es Flowprint?"}))
print(resultado)
```

Si el grafo tiene errores (pin inexistente, tipo desconocido, pin requerido sin
conexión), `build_engine` lanza `ValueError` con la lista de errores antes de
ejecutar nada.

---

## Tabla de pines por nodo

| Nodo | `exec_inputs` | `exec_outputs` | Inputs (datos) | Outputs (datos) |
|---|---|---|---|---|
| `Start` | — | `out` | — | los campos de `signature.inputs` (dinámicos) |
| `End` | `in` | — | los campos de `signature.outputs` (dinámicos) | — |
| `Sequence` | `in` | `1`, `2`, `3` | — | — |
| `ForEach` | `in` | `body`, `completed` | — | — |
| `Branch` | `in` | `true`, `false` | `condition: bool` | — |
| `FlipFlop` | `in` | `a`, `b` | — | — |
| `SetVar` | `in` | `out` | `value: Any` | — |
| `GetVar` | — (puro) | — | — | `value: Any` |
| `Const` | — (puro) | — | — | `value: str` |
| `Concat` | — (puro) | — | `a: str`, `b: str` | `value: str` |
| `Equals` | — (puro) | — | `a: str`, `b: str` | `result: bool` |
| `ItemOf` | — (puro) | — | — | `value: str` |
| `IntToFloat` | — (puro) | — | `value: int` | `value: float` |
| `BoolToInt` | — (puro) | — | `value: bool` | `value: int` |
| `ToStr` | — (puro) | — | `value: Any` | `value: str` |
