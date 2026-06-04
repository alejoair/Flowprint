# Cómo crear un nodo custom

Un nodo es la unidad de trabajo en Flowprint. Puede ser un agente LLM, una
transformación de datos, una llamada a una API externa, o cualquier lógica
que necesites orquestar.

## Pasos

### 1. Crear el archivo

Cada tipo de nodo vive en su propio archivo bajo `src/flowprint/nodes/`.
Elige la carpeta según su propósito:

```
src/flowprint/nodes/
├── agents/      ← nodos que llaman a LLMs u otros servicios externos
├── control/     ← nodos que controlan el flujo (Branch, Sequence, loops)
├── data/        ← nodos que transforman datos sin efectos externos
└── variables/   ← nodos que leen/escriben variables del grafo
```

### 2. Heredar de `Node` e implementar el contrato

```python
from pydantic import BaseModel
from flowprint.core.node import Node, NodeResult, ExecutionContext
from flowprint.core.control import Goto

class MiAgente(Node):
    class Inputs(BaseModel):
        prompt: str
        temperatura: float = 0.7   # default → pin opcional en el grafo

    class Outputs(BaseModel):
        respuesta: str

    exec_inputs  = ("in",)
    exec_outputs = ("out",)
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        resultado = await llamar_a_mi_api(inputs.prompt, inputs.temperatura)
        return NodeResult(self.Outputs(respuesta=resultado), Goto(["out"]))
```

### 3. Registrar el nodo

Añade el tipo al registro en `src/flowprint/graph/registry.py`:

```python
from flowprint.nodes.agents.mi_agente import MiAgente

NODE_REGISTRY = {
    ...
    "MiAgente": MiAgente,
}
```

Sin este paso el validador rechaza el grafo con "tipo desconocido".

---

## Referencia del contrato

### `Inputs` y `Outputs`

Modelos Pydantic. Cada campo es un pin de datos tipado.

```python
class Inputs(BaseModel):
    texto: str          # requerido — debe tener conexión en el grafo
    n: int = 3          # opcional — puede quedar sin conectar (usa el default)
```

- **Campo sin default → pin requerido.** El validador rechaza el grafo si ese
  pin no tiene conexión.
- **Campo con default → pin opcional.** Puede quedar sin conectar.
- **El tipo del campo define qué conexiones son válidas.** El validador comprueba
  compatibilidad en diseño antes de ejecutar.

### Pines de ejecución

```python
exec_inputs  = ("in",)    # señales de ejecución que acepta el nodo
exec_outputs = ("out",)   # señales de ejecución que emite el nodo
```

Ejemplos según el tipo de nodo:

| Propósito | `exec_inputs` | `exec_outputs` |
|---|---|---|
| Nodo normal | `("in",)` | `("out",)` |
| Bifurcación | `("in",)` | `("true", "false")` |
| Secuencia | `("in",)` | `("1", "2", "3")` |
| Loop | `("in",)` | `("body", "completed")` |
| Punto de entrada (Start) | `()` | `("out",)` |
| Punto de salida (End) | `("in",)` | `()` |

### `is_pure`

```python
is_pure = False   # tiene pines de ejecución (comportamiento por defecto)
is_pure = True    # nodo de datos puro, sin pines de ejecución
```

Un nodo puro se evalúa **bajo demanda** cuando otro nodo necesita su salida.
No participa en el flujo de ejecución. Ejemplos: `Const`, `Concat`, `Equals`.

**Regla:** lo caro nunca es puro. Las llamadas a APIs, LLMs o servicios externos
deben ser `is_pure = False` — el motor las ejecuta una vez y guarda la salida.
Un nodo puro puede reevaluarse varias veces (por ejemplo dentro de un loop).

### `execute`

```python
async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
    ...
```

- Siempre `async def`, aunque no uses `await`.
- `inputs` llega ya validado como instancia de tu `Inputs`.
- `ctx` expone:
  - `ctx.get_var(nombre)` / `ctx.set_var(nombre, valor)` — variables del grafo
  - `ctx.node_state(self.instance_id)` — dict persistente privado del nodo
    (para guardar estado entre ejecuciones dentro del mismo grafo, como un
    contador o el índice actual de un loop)
- Devuelve `NodeResult(data, control)`.

### `NodeResult` y las instrucciones de control

```python
NodeResult(self.Outputs(...), instrucción)
```

| Instrucción | Significado |
|---|---|
| `Goto(["out"])` | avanzar al siguiente nodo |
| `Goto(["true"])` | bifurcar hacia la salida `true` |
| `Goto(["1", "2", "3"])` | activar varias salidas en orden (Sequence) |
| `Repeat(["body"])` | activar la salida y re-encolarse (loops) |
| `Stop()` | esta rama termina aquí; obligatorio en nodos puros |

El vocabulario es cerrado: solo existen estas cuatro instrucciones. El motor
las interpreta sin conocer el tipo del nodo.

### `config`

Parámetros fijos de la instancia que vienen del JSON del grafo (modelo, prompt,
temperatura, etc.). Se acceden desde `self.config`:

```python
modelo = self.config.get("model", "gpt-4o")
```

Se definen en el JSON del grafo bajo `Instance.config`, no llegan por pines.

---

## Ejemplo: nodo puro de transformación

```python
from pydantic import BaseModel
from flowprint.core.node import Node, NodeResult, ExecutionContext
from flowprint.core.control import Stop

class MayusculasNode(Node):
    class Inputs(BaseModel):
        texto: str

    class Outputs(BaseModel):
        resultado: str

    is_pure = True

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(self.Outputs(resultado=inputs.texto.upper()), Stop())
```

## Ejemplo: nodo con estado interno (contador)

```python
from pydantic import BaseModel
from flowprint.core.node import Node, NodeResult, ExecutionContext
from flowprint.core.control import Goto

class ContadorNode(Node):
    class Inputs(BaseModel):
        pass

    class Outputs(BaseModel):
        n: int

    exec_inputs  = ("in",)
    exec_outputs = ("out",)
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        st = ctx.node_state(self.instance_id)
        st["n"] = st.get("n", 0) + 1
        return NodeResult(self.Outputs(n=st["n"]), Goto(["out"]))
```

El estado (`st`) persiste entre ejecuciones dentro de la misma corrida del
grafo y es privado a esta instancia concreta.

## Ejemplo: nodo que bifurca

```python
from pydantic import BaseModel
from flowprint.core.node import Node, NodeResult, ExecutionContext
from flowprint.core.control import Goto

class EsLargoNode(Node):
    class Inputs(BaseModel):
        texto: str
        limite: int = 100

    class Outputs(BaseModel):
        pass

    exec_inputs  = ("in",)
    exec_outputs = ("si", "no")
    is_pure = False

    async def execute(self, inputs: Inputs, ctx: ExecutionContext) -> NodeResult:
        pin = "si" if len(inputs.texto) > inputs.limite else "no"
        return NodeResult(self.Outputs(), Goto([pin]))
```
