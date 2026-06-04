# API HTTP de Flowprint

La API está disponible en `http://localhost:8000` cuando el servidor está corriendo con
`flowprint serve` o `flowprint editor`. La documentación interactiva (Swagger UI) está en
`/docs` y la versión alternativa (ReDoc) en `/redoc`.

No hay autenticación. Todos los endpoints aceptan y devuelven `application/json`.

---

## Nodos

### `GET /nodes`

Devuelve el catálogo completo de nodos registrados (built-in + custom).

**Respuesta**

```json
[
  {
    "type": "Branch",
    "is_pure": false,
    "data_inputs":  { "condition": "bool" },
    "data_outputs": {},
    "exec_inputs":  ["exec"],
    "exec_outputs": ["true", "false"],
    "is_custom": false
  },
  {
    "type": "Add",
    "is_pure": true,
    "data_inputs":  { "a": "float", "b": "float" },
    "data_outputs": { "result": "float" },
    "exec_inputs":  [],
    "exec_outputs": [],
    "is_custom": false
  }
]
```

---

### `GET /nodes/custom`

Lista los nodos custom (archivos `.py` en `custom_nodes/`).

**Respuesta**

```json
[
  { "name": "MiAgente", "source": "from flowprint.core.node import ..." }
]
```

---

### `GET /nodes/custom/{name}`

Devuelve el código fuente de un nodo custom.

| Código | Motivo |
|--------|--------|
| `200` | OK |
| `404` | No existe un nodo con ese nombre |

---

### `POST /nodes/custom/{name}` `201`

Crea un nuevo nodo custom. El nombre debe ser un identificador Python válido
(`name.isidentifier()`). La fuente se valida sintácticamente antes de guardar.

**Body**

```json
{ "source": "from flowprint.core.node import Node, NodeResult\n..." }
```

**Respuesta**

```json
{ "registered": ["MiAgente", "OtroNodo"] }
```

| Código | Motivo |
|--------|--------|
| `201` | Creado; nodo registrado en `NODE_REGISTRY` |
| `400` | Nombre inválido |
| `409` | Ya existe un nodo con ese nombre |
| `422` | Error de sintaxis en el código fuente |

---

### `PUT /nodes/custom/{name}`

Actualiza el código de un nodo existente y recarga el registro.

**Body** igual que `POST`.

| Código | Motivo |
|--------|--------|
| `200` | Actualizado |
| `400` | Nombre inválido |
| `404` | El nodo no existe |
| `422` | Error de sintaxis |

---

### `DELETE /nodes/custom/{name}` `204`

Elimina el archivo del nodo y lo desregistra.

---

### `GET /types/compatibility`

Lista las conversiones de tipo seguras disponibles (las que el validador sugiere insertar).

**Respuesta**

```json
[
  { "from": "int",  "to": "float", "converter": "IntToFloat" },
  { "from": "int",  "to": "str",   "converter": "ToStr" },
  { "from": "bool", "to": "int",   "converter": "BoolToInt" }
]
```

---

## Grafos (persistencia)

Los grafos se guardan como archivos JSON en `graphs/` relativo al directorio de trabajo.
Los nombres solo pueden contener letras minúsculas, números, guiones (`-`) y guiones bajos
(`_`), y deben empezar por letra o número (`^[a-z0-9][a-z0-9_-]{0,63}$`).

### `GET /graphs`

Lista los grafos guardados.

**Respuesta**

```json
[{ "name": "clasificador" }, { "name": "pipeline-resumen" }]
```

---

### `GET /graphs/{name}`

Devuelve el JSON completo del grafo tal como fue guardado.

```json
{
  "name": "clasificador",
  "graph": {
    "schema_version": "1.0",
    "signature": { "inputs": { "texto": "str" }, "outputs": { "resultado": "str" } },
    "instances": [...],
    "connections": [...]
  }
}
```

---

### `POST /graphs/{name}` `201`

Crea un nuevo grafo. El campo `graph` se valida con el esquema Pydantic antes de persistir.

**Body**

```json
{
  "graph": {
    "schema_version": "1.0",
    "signature": { "inputs": {}, "outputs": {} },
    "variables": [],
    "instances": [...],
    "connections": [...],
    "visual": {}
  }
}
```

| Código | Motivo |
|--------|--------|
| `201` | Creado |
| `400` | Nombre inválido |
| `409` | Ya existe un grafo con ese nombre |
| `422` | El grafo no pasa la validación del esquema |

---

### `PUT /graphs/{name}`

Reemplaza el contenido de un grafo existente. Mismo body que `POST`.

---

### `DELETE /graphs/{name}` `204`

Elimina el archivo del grafo.

---

## Ejecución

### `POST /graph/validate`

Valida un grafo inline (sin guardarlo) y devuelve los errores semánticos encontrados.
La validación comprueba: ids únicos, tipos conocidos, pines que existen,
compatibilidad de tipos en las conexiones, y pines requeridos sin conexión.

**Body**

```json
{ "graph": { ... } }
```

**Respuesta**

```json
{ "errors": [] }
```

Con errores:

```json
{
  "errors": [
    "'nodo_1.valor' es un pin de datos requerido sin conexión y sin valor por defecto.",
    "Tipos incompatibles nodo_2.result (str) -> nodo_3.count (int)."
  ]
}
```

---

### `POST /graph/run`

Ejecuta un grafo inline y devuelve el resultado final cuando termina.
Útil para pruebas y llamadas síncronas sin necesidad de WebSocket.

**Body**

```json
{
  "graph": { ... },
  "args": { "texto": "hola mundo" }
}
```

`args` es opcional; si el grafo no tiene `signature.inputs`, se puede omitir.

**Respuesta** — el valor devuelto por el nodo `End`:

```json
{ "salida": "hola mundo procesado" }
```

| Código | Motivo |
|--------|--------|
| `200` | Ejecución completada |
| `400` | Error en tiempo de ejecución |
| `422` | El grafo no pasa la validación del esquema |

---

### `WS /graph/run/ws`

Ejecuta un grafo inline via WebSocket y emite eventos en tiempo real.

**Mensaje de inicio** (cliente → servidor):

```json
{
  "graph": { ... },
  "args": { "texto": "hola mundo" }
}
```

**Eventos** (servidor → cliente):

| Evento | Campos extra | Descripción |
|--------|-------------|-------------|
| `node_start` | `node_id`, `node_type` | Un nodo está por ejecutarse |
| `node_complete` | `node_id`, `node_type`, `outputs` | Un nodo terminó |
| `graph_complete` | `result` | El grafo terminó; `result` es la salida del `End` |
| `error` | `error` | Error en validación o ejecución |
| `cancelled` | — | La ejecución fue cancelada |

```json
{ "event": "node_start",    "node_id": "clasif_1", "node_type": "AgentEcho" }
{ "event": "node_complete", "node_id": "clasif_1", "node_type": "AgentEcho", "outputs": { "response": "eco: hola" } }
{ "event": "graph_complete", "result": { "salida": "eco: hola" } }
```

El servidor cierra la conexión al finalizar (tanto en éxito como en error).

---

### `POST /graphs/{name}/run`

Ejecuta un grafo guardado y devuelve el resultado final.
El cuerpo es opcional; si el grafo tiene `signature.inputs`, pasa los argumentos en `args`.

**Body** (opcional):

```json
{ "args": { "texto": "hola" } }
```

---

### `WS /graphs/{name}/run/ws`

Ejecuta un grafo guardado via WebSocket. El cliente solo envía los argumentos; el grafo se
carga del disco.

**Mensaje de inicio** (cliente → servidor):

```json
{ "args": { "texto": "hola" } }
```

Los eventos emitidos son idénticos a `/graph/run/ws`.

---

## Códigos de error comunes

| Código | Significado |
|--------|-------------|
| `400` | Nombre inválido o error en tiempo de ejecución del grafo |
| `404` | Recurso no encontrado (nodo o grafo) |
| `409` | Ya existe un recurso con ese nombre |
| `422` | El cuerpo no pasa la validación del esquema |

El cuerpo del error sigue el formato estándar de FastAPI:

```json
{ "detail": "Grafo 'foo' no encontrado." }
```

---

## Ejemplo rápido con curl

```bash
# Validar un grafo
curl -s -X POST http://localhost:8000/graph/validate \
  -H "Content-Type: application/json" \
  -d '{"graph": {"schema_version":"1.0","signature":{"inputs":{},"outputs":{}},"variables":[],"instances":[{"id":"start","type":"Start","config":{}},{"id":"end","type":"End","config":{}}],"connections":[{"kind":"exec","from_node":"start","from_pin":"exec","to_node":"end","to_pin":"exec"}],"visual":{}}}' | python -m json.tool

# Guardar un grafo
curl -s -X POST http://localhost:8000/graphs/mi-grafo \
  -H "Content-Type: application/json" \
  -d '{"graph": {...}}' | python -m json.tool

# Ejecutar un grafo guardado
curl -s -X POST http://localhost:8000/graphs/mi-grafo/run \
  -H "Content-Type: application/json" \
  -d '{"args": {"texto": "hola"}}' | python -m json.tool
```

---

## Ejemplo WebSocket con Python

```python
import asyncio
import json
import websockets

async def run():
    graph = { ... }  # tu definición de grafo
    async with websockets.connect("ws://localhost:8000/graph/run/ws") as ws:
        await ws.send(json.dumps({"graph": graph, "args": {"texto": "hola"}}))
        async for raw in ws:
            event = json.loads(raw)
            print(event["event"], event.get("node_id", ""), event.get("result", ""))
            if event["event"] in ("graph_complete", "error"):
                break

asyncio.run(run())
```
