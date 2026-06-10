# Flowprint — Documento de Diseño

**Estado:** diseño cerrado e implementado en `src/flowprint/`.
**Método:** spec-driven. Cada decisión se cerró antes de escribir código, evaluando alternativas.
**Código fuente:** `src/flowprint/` — motor, nodos, validación y cargador. Tests en `tests/`.

---

## 1. Resumen ejecutivo

Flowprint es un motor de orquestación de sistemas multiagente en Python, construido sobre
el modelo de ejecución de los Blueprints de Unreal Engine. Cada agente es un nodo que
recibe una entrada tipada y devuelve una salida tipada. Los nodos se conectan en un grafo
que define cómo se orquesta el flujo: en qué orden se ejecutan, cómo se ramifica la lógica
y cómo viajan los datos entre ellos.

La diferencia central con las herramientas existentes está en el modelo de ejecución.
Flowprint separa explícitamente el flujo de ejecución (el orden en que corren los nodos)
del flujo de datos (los valores que viajan entre ellos), tal como hace Blueprint con sus
pines blancos de ejecución y sus pines de colores de datos. Esto da control imperativo
fino sobre la orquestación, algo que los modelos puramente basados en dataflow no ofrecen.

El proyecto se construye por fases: primero el motor de ejecución (Python puro, validado
con una API de código y tests), después un visualizador de solo lectura para depurar, y
finalmente un editor visual interactivo.

---

## 2. El problema

Orquestar varios agentes de LLM requiere expresar lógica de control: ejecutar un agente,
ramificar según su salida, iterar sobre una lista aplicando un agente a cada elemento,
encadenar pasos en un orden concreto. Hoy existen dos familias de herramientas para esto,
y ambas tienen una limitación.

Las herramientas visuales como Langflow y Flowise usan un modelo de **dataflow**: un nodo
se ejecuta cuando sus datos de entrada están disponibles. El orden emerge de las
dependencias de datos, no se controla explícitamente. Esto es cómodo para tuberías
lineales de transformación, pero se queda corto cuando necesitas lógica imperativa: "haz
esto, luego esto, y si se cumple tal condición ramifica hacia allá". El control de flujo
queda implícito y es difícil de razonar.

Las herramientas de código como LangGraph modelan el flujo como un grafo de estados con
nodos y aristas, y dan control fino, pero carecen de representación visual y obligan a
manejar el estado y las transiciones en código, con una curva de aprendizaje pronunciada.

Flowprint toma el modelo de ejecución de Blueprint, que resuelve exactamente esta tensión:
es visual e imperativo a la vez. El pin de ejecución hace explícito el orden, el pin de
datos hace explícito el flujo de información, y ambos son visibles en el grafo. Es un
modelo probado durante más de una década en producción de videojuegos, trasladado al
dominio de la orquestación de agentes.

---

## 3. Panorama de alternativas

Para situar Flowprint, así se reparten las herramientas existentes:

**Langflow** es lo más cercano en intención: editor visual basado en nodos donde cada
componente es código Python, con soporte de orquestación multiagente y exportación a JSON.
Usa modelo dataflow, no flujo de ejecución explícito.

**Flowise** ofrece un builder visual (Agentflow) pensado para sistemas multiagente con
memoria y nodos human-in-the-loop. También dataflow.

**LangGraph** es lo más parecido conceptualmente al modelo de Flowprint (grafo de nodos y
aristas, estado compartido, control fino) pero sin capa visual y con estado por
TypedDict compartido, no por pines.

**ChatOllamaAgent** es el más cercano en filosofía a Blueprint: programación visual por
nodos para flujos de LLM, con runner en Python, validación de tipos y control de flujo.
Proyecto pequeño pero conceptualmente casi idéntico a "Blueprint para LLMs".

Lo que ninguna ofrece es la separación estricta entre pin de ejecución y pin de datos con
nodos de control imperativos (Branch, Sequence) importados del modelo de Unreal. Esa es la
contribución de Flowprint.

Hay además una conexión con el trabajo previo en MFR-PDDL: el modelo de Blueprint, con
preconditions implícitas, efectos y nodos conectados por flujo, es estructuralmente
parecido a operadores PDDL encadenados. La diferencia es que Blueprint es imperativo y
explícito mientras PDDL es declarativo. Flowprint puede verse como un PDDL imperativo y
visual donde cada agente es un operador con firma tipada.

---

## 4. Decisiones de arquitectura

Cada decisión se tomó evaluando alternativas. Se documenta la decisión, su razón y sus
consecuencias.

### 4.1 Modelo de ejecución: flujo explícito (Blueprint)

**Decisión.** Flujo de ejecución explícito, estilo Blueprint. Dos tipos de conexión
separados entre nodos:

- **Pin de ejecución:** define el orden. Un nodo solo corre cuando le llega la señal de
  ejecución por su pin de entrada, sin importar si sus datos estaban listos antes.
- **Pin de datos:** transporta valores tipados entre nodos.

**Alternativa descartada.** El modelo dataflow (Langflow), donde la disponibilidad de
datos dispara la ejecución. Se descartó porque no permite expresar control imperativo
explícito (Sequence, Branch) ni la distinción puro/efecto, que eran requisitos.

**Consecuencias.**

*Nodos puros por evaluación pull.* Un nodo puro no tiene pin de ejecución. Se evalúa bajo
demanda cuando un nodo con efecto necesita su valor de salida. Antes de ejecutar un nodo
con efecto, el motor recorre hacia atrás sus pines de datos de entrada y evalúa
recursivamente cualquier nodo puro conectado. Es evaluación pull (bajo demanda), no push.
El motor necesita esta resolución recursiva desde el inicio; sin ella los nodos puros no
funcionan.

*Asincronía desde el inicio.* El motor es asíncrono desde la primera línea. Los
nodos-agente llaman a LLMs, que es espera de I/O; async evita bloquear el flujo y habilita
ejecución paralela futura sin reescribir el motor. Migrar de síncrono a async después es
costoso porque async es contagioso: una función async obliga a que todo lo que la llama
sea async hacia arriba en la cadena. El contrato base es:

```python
class Node:
    async def execute(self, inputs: dict) -> NodeResult:
        ...
```

Un nodo puro sin I/O igual usa `async def` pero no está obligado a usar `await` dentro; no
paga complejidad por ser simple.

*El nodo decide qué salida de ejecución activa.* Al terminar, un nodo no devuelve
"siguiente nodo" sino cuál de sus pines de salida de ejecución activa; el motor sigue esa
señal. Branch activa True o False; Sequence activa sus salidas en orden; FlipFlop alterna.
El contrato de `NodeResult` debe llevar tanto los datos de salida como el pin de ejecución
activado.

### 4.2 Qué es un nodo y qué es un agente

**Decisión: modelo plano.** Solo existe `Node`. Un agente no es un tipo especial: es un
nodo cuya `execute()` resulta que llama a un LLM. Para el motor es indistinguible de un
nodo que suma dos números. La "agentidad" vive en la implementación, no en el tipo.

**Alternativa descartada.** Jerarquía con `Agent` como subclase especial que el motor
trata distinto. Se descartó por acoplar el motor a un concepto que no necesita conocer. El
modelo plano es coherente con MFR-PDDL, donde los agentes son atómicos y opacos desde la
perspectiva del dominio.

**Decisión: estado externo (modelo Unreal / MFR-PDDL).** El nodo no tiene estado propio.
El estado persistente vive en un contexto de ejecución externo.

Esto replica cómo funciona Unreal. Un Blueprint no es el grafo de nodos: es una clase, y
al colocar un actor en el mundo se crea una instancia. El grafo es la definición del
comportamiento, compartida por todas las instancias; el estado vive en la instancia. Un
FlipFlop guarda su bit, pero ese bit vive en la instancia del actor, no en el nodo del
grafo. Diez actores del mismo Blueprint tienen diez FlipFlops independientes con el mismo
grafo.

Trasladado a Flowprint: el grafo es la definición compartida y reproducible; el estado de
una corrida (el bit del FlipFlop, un contador, el historial de un agente) vive en un
contexto de ejecución externo. Un mismo grafo se ejecuta varias veces con contextos
distintos. El objeto `Node` sigue siendo caja negra sin estado interno, serializable y
reproducible.

Mapeo con MFR-PDDL: el grafo es como `domain.pddl` (definición); el contexto de ejecución
es como `state.db` (estado de una corrida).

**Decisión: tipado estricto en diseño + autoconversión segura (modelo Unreal).**
Validación estricta de tipos en tiempo de diseño, con conversión automática para casos
seguros, igual que Unreal.

Mecanismo, replicando Unreal. Cada pin tiene un tipo. Al conectar salida de tipo A a
entrada de tipo B:

- **Tipos idénticos:** conexión directa.
- **Distintos con conversión segura conocida:** el motor inserta una conversión automática
  (int→float; casi cualquier cosa→string para depuración). Catálogo de promociones seguras
  predefinido, las que no pierden información o cuya pérdida es aceptable.
- **Incompatibles sin conversión conocida:** la conexión se rechaza en el editor. Nunca
  llega a runtime una conexión inválida.

Para tipos de objeto y estructura, las relaciones de subtipo de Pydantic hacen el papel de
la jerarquía de objetos de Unreal: subir (derivado→base) es implícito y seguro; bajar
(base→derivado) requiere un cast explícito con pin de fallo. Los agentes con salida
estructurada usan schemas Pydantic planos, y ese mismo schema es el tipo del pin.
Filosofía: errores temprano.

### 4.3 Estado y comunicación

**Decisión: comunicación solo por pines (Blueprint puro).** Toda la comunicación entre
nodos pasa por los pines de datos. No hay canal lateral. El grafo es la única vía de
información; mirando las conexiones se ve todo el flujo.

**Alternativa descartada.** Un blackboard de estado compartido de lectura/escritura libre
(estilo LangGraph, o las tablas de MFR-PDDL). Se descartó a favor de la honestidad visual
de Blueprint, aunque es deliberadamente lo contrario de lo elegido en MFR-PDDL. Aquí se
prioriza que el grafo sea autoexplicativo.

Consecuencia sobre el contexto de ejecución de 4.2: sigue existiendo, pero no es un
blackboard de comunicación entre nodos. Es solo el almacén del estado oculto que ciertos
nodos necesitan (el bit del FlipFlop, un contador, el historial de un agente). Lo usa el
motor para guardar el estado interno de nodos concretos; los nodos no lo usan para
hablarse entre sí.

El contexto es un **Ray Actor** (`_ContextActor`) — un proceso separado gestionado por Ray.
Las llamadas de lectura/escritura son remotas y asíncronas por diseño. Esto garantiza
consistencia cuando múltiples ramas del grafo corren en paralelo (Fork), ya que Ray serializa
todas las llamadas al actor. El motor accede al actor vía `RayContextProxy`, que implementa
`ContextProtocol` con la misma interfaz que `LocalContext` (usada en tests sin Ray).

**Decisión: nodos de variable Get/Set (como Unreal).** Existen nodos `Get` y `Set` que
acceden a variables nombradas del grafo. Un `Set` escribe, un `Get` lee, en cualquier
punto. Siguen siendo nodos visibles en el grafo, no un canal lateral invisible: incluso el
acceso a estado compartido se ve como un nodo.

Razón. Con comunicación estrictamente por cable, llevar un dato de un nodo temprano a uno
lejano obligaría a cablearlo a través de todos los intermedios (el "wire spaghetti" que en
Blueprint se evita justamente con variables de instancia). Los nodos Get/Set resuelven eso
sin romper la honestidad visual. Sin ellos, cualquier flujo no trivial se vuelve
inmanejable.

### 4.4 Representación y persistencia

La clave es separar la definición de un tipo de nodo (código) de la instancia de un nodo
dentro de un grafo concreto (datos). Son cosas distintas.

**Decisión: tipos de nodo en archivos Python.** Cada tipo de nodo (un agente, Branch,
Sequence, Get/Set) es una clase o función Python en su propio archivo `.py`: su
`async def execute()`, su firma de pines tipados, su lógica. La biblioteca de tipos
disponibles es un conjunto de archivos Python. Precedente: en Unreal cada Blueprint es una
clase; en MFR-PDDL cada agente es un archivo en `.claude/agents/<name>.md`.

**Decisión: grafo en JSON como fuente de verdad.** El grafo es un archivo JSON que
referencia tipos por nombre y describe instancias y conexiones. Conceptualmente: "instancia
3, de tipo `LLMAgentNode`, en posición (x,y), con estos parámetros, pin de salida conectado
a la instancia 5". El JSON es la fuente de verdad; el editor visual lo lee y escribe
trivialmente.

**Alternativa descartada: guardar cada instancia como archivo Python.** Atractivo a primera
vista, pero falla por tres razones:

- *Conexiones.* Un grafo es fundamentalmente aristas entre pines; la información importante
  vive en las relaciones, no en los nodos. No se descompone limpio en un archivo por nodo.
- *Editor visual.* Si el grafo fuera código repartido en archivos, arrastrar un nodo o
  crear un cable obligaría a parsear y regenerar `.py`. Frágil y lento.
- *Estado visual.* Posición en el canvas, zoom y comentarios son datos puros, no código.

La distinción que resuelve esto es justo la de Unreal entre la clase Blueprint (definición)
y el nivel donde se colocan los actores (instancias y relaciones).

**Decisión: API Python para construir el grafo.** Existe una API Python para construir y
manipular el JSON programáticamente. El código produce JSON; no es la fuente de verdad.
Permite generar grafos desde código sin cerrar el camino al editor visual, y es lo que se
usa para validar el motor en la fase 1.

### 4.5 Punto de entrada y salida: nodos Start y End

**Decisión.** Cada grafo tiene un nodo `Start` único como punto de arranque y un nodo
`End` (o `Return`) que marca dónde termina y qué devuelve. Juntos definen la **firma del
grafo**: qué entra y qué sale.

`Start` no tiene pin de entrada de ejecución; solo un pin de salida de ejecución desde el
que arranca el flujo. Además expone, como pines de datos de salida, los argumentos con los
que se invocó el grafo: no es un disparador vacío, es por donde entran los datos iniciales
(el texto a clasificar, la lista de documentos).

`End` no tiene pin de salida de ejecución; recibe la señal de ejecución y toma, por sus
pines de datos de entrada, los valores que el grafo entrega como resultado. Sin él no
quedaría claro cuál es la salida del grafo al terminar.

**Razón.** Definir entrada y salida convierte el grafo en algo invocable como una función.
Esto habilita, más adelante, que un grafo completo se use como un nodo dentro de otro
grafo, igual que en Blueprint una función con su Input y su Return Node se llama desde
otros grafos. Es la base de la composición.

**Alternativa considerada.** Múltiples nodos de evento como raíces de ejecución
independientes (BeginPlay, Tick, eventos de input), como en Blueprint real. Se aplaza
porque en orquestación multiagente el patrón normal es "una entrada, un resultado", y no
hay todavía un equivalente claro de qué dispararía cada evento. El `Start` único es
suficiente para v1 y no cierra la puerta a eventos múltiples después.

**Pendiente de detallar** en el contrato de `Node` y el esquema JSON: cómo se declaran
formalmente los pines de datos del `Start` y del `End` (la firma tipada del grafo).

### 4.6 Control de flujo: nodos de la v1

**Decisión.** La v1 incluye tres nodos de control: Branch, Sequence y ForEach.

- **Branch:** bifurcación por condición booleana, dos salidas de ejecución (True/False).
  Es el `if`.
- **Sequence:** varias salidas de ejecución que se disparan en orden. Encadena pasos o
  agentes uno tras otro. Central para orquestación multiagente.
- **ForEach:** itera sobre un array, con pin `Loop Body` y pin `Completed`. Aplica un
  agente a cada elemento de una colección.

Con esos tres se expresan condicionales, secuencias de agentes e iteración sobre
colecciones, que cubren la mayoría de flujos multiagente reales.

**Aplazados.** ForLoop, FlipFlop, WhileLoop, Gate, DoOnce y el nodo paralelo (gather).
Casi todos son baratos de añadir después porque solo requieren las dos capacidades que el
contrato del nodo ya tiene (múltiples salidas de ejecución y estado en el contexto); son
archivos Python aditivos que no tocan el motor.

**Supuestos del motor desde el inicio.** Lo que importa no es cuántos nodos hay en v1 sino
qué supuestos hace el motor. Dos quedan abiertos desde el inicio para evitar
refactorizaciones caras:

1. *Repetición: el motor no asume grafos acíclicos.* Un pin de ejecución puede volver a un
   nodo ya visitado. ForEach lo ejercita en v1. El motor no lleva un conjunto de "nodos ya
   ejecutados" para impedir revisitas; un nodo puede ejecutarse muchas veces, y el estado
   de iteración vive en el contexto, no en una marca de visitado. Esto deja gratis ForLoop
   y WhileLoop después.

2. *Múltiples frentes de ejecución: listo para paralelismo.* El bucle del motor no se
   escribe alrededor de "un único nodo actual". Maneja una colección de frentes de
   ejecución activos, aunque en v1 casi siempre tenga uno solo. El modelo de avance es
   "tomar el siguiente frente pendiente, ejecutarlo, encolar los frentes que produce", no
   "ir al siguiente nodo". Esto permite añadir el nodo paralelo (gather) después sin
   reescribir el bucle.

El coste de ambos supuestos en v1 es casi nulo y protegen el activo más caro de reescribir:
el bucle de ejecución.

### 4.7 Alcance de la primera versión

**Decisión.** Motor primero, con un visualizador de solo lectura como fase intermedia, y
el editor visual interactivo como fase final.

**Alternativa descartada.** Construir editor y motor en paralelo desde el inicio. Se
descartó porque el editor visual es un proyecto grande por sí mismo (canvas, pines,
conexiones, validación en diseño, drag & drop) que competiría en calidad de UI con Langflow
y Flowise, restando foco al motor, que es la verdadera contribución.

**Fase 1 — Motor.** Construir el motor completo y validarlo con grafos definidos vía la API
Python y tests, sin interfaz gráfica. El motor debe ejecutar nodos puros (pull), nodos con
efecto, nodos-agente, Branch, Sequence, ForEach, nodos Get/Set y el contexto de ejecución,
con los dos supuestos abiertos. Aquí vive todo lo difícil del diseño: doble pin, evaluación
pull, frentes de ejecución, async. Al terminar esta fase, Flowprint ya es usable por
código, comparable conceptualmente a LangGraph pero con modelo Blueprint.

**Fase 2 — Visualizador de solo lectura.** Renderizar el grafo JSON como diagrama, sin
edición. Da depuración visual del motor con poco esfuerzo y pospone el editor interactivo
hasta que sea necesario.

**Fase 3 — Editor visual interactivo.** Editor de grafos (probablemente React) con pines,
conexiones, validación de tipos en diseño y drag & drop. Lee y escribe el JSON que el motor
ya entiende, así que encaja sin tocar el motor.

**Razonamiento de la secuencia.** El motor es Python puro, terreno fuerte; el editor es
React, terreno en aprendizaje; separarlos evita que las dudas de uno contaminen al otro. El
JSON como fuente de verdad garantiza que cada fase encaje sobre la anterior sin fricción.

---

## 5. Ejemplos conceptuales

Estos ejemplos ilustran cómo se ven los flujos. No son sintaxis final, son bocetos para
fijar el modelo mental.

**Ejemplo 1 — Clasificar y ramificar.** Un agente clasifica un texto entrante; según la
categoría, se ejecuta uno u otro agente especializado.

```
[Start] --exec--> [Agente Clasificador] --exec--> [Branch]
  |data: texto          |data: categoria             |True  --exec--> [Agente Soporte] --exec--> [End]
                                                      |False --exec--> [Agente Ventas]  --exec--> [End]
```

El `Start` expone el dato `texto` con el que se invocó el grafo. El pin de datos
`categoria` alimenta la condición del Branch (vía un nodo puro de comparación). Los pines
de ejecución deciden qué agente corre. Ambas ramas terminan en `End`, que entrega el
resultado del grafo.

**Ejemplo 2 — Aplicar un agente a cada elemento.** Una lista de documentos; un agente
resume cada uno.

```
[Inicio] --exec--> [ForEach (lista de docs)]
                       |Loop Body --exec--> [Agente Resumidor] (recibe el elemento actual)
                       |Completed --exec--> [Agente Consolidador]
```

ForEach ejercita la repetición del motor: vuelve a su Loop Body por cada elemento, y el
índice actual vive en el contexto de ejecución.

**Ejemplo 3 — Secuencia con variable compartida.** Un agente genera un plan; varios pasos
posteriores lo leen sin cablearlo a través de todos.

```
[Inicio] --exec--> [Agente Planificador] --exec--> [Set "plan"] --exec--> [Sequence]
                                                                              |1 --exec--> [Get "plan"] --> [Agente Paso A]
                                                                              |2 --exec--> [Get "plan"] --> [Agente Paso B]
```

`Set "plan"` y `Get "plan"` son nodos visibles que evitan el wire spaghetti.

---

## 6. Resumen de decisiones

1. **Ejecución:** flujo explícito (Blueprint). Async desde el inicio. Nodos puros por pull.
   El nodo decide qué pin de salida de ejecución activa.
2. **Nodo/agente:** modelo plano (solo `Node`). Estado externo (modelo Unreal/MFR-PDDL).
   Tipado estricto en diseño + autoconversión segura, vía Pydantic.
3. **Comunicación:** solo por pines (Blueprint puro). Nodos Get/Set de variable visibles.
4. **Persistencia:** tipos de nodo en `.py`; grafo en JSON (fuente de verdad); API Python
   que produce el JSON. Nodos `Start` y `End` definen la firma del grafo (entrada/salida),
   lo que lo hace invocable y componible como un nodo dentro de otro grafo.
5. **Control de flujo v1:** Branch + Sequence + ForEach. Motor listo para repetición y
   paralelismo futuro.
6. **Alcance v1:** motor primero (API Python + tests) → visualizador de solo lectura →
   editor visual interactivo.

---

## 7. Contrato de `Node` y `NodeResult` — DEFINIDO

Código de referencia validado: `flowprint_node_contract.py` (Pydantic 2.x, async).

**Decisión: modelo híbrido.** Pydantic para los pines de datos; declaración aparte para
los pines de ejecución. Razón: el editor visual y el validador de tipos en diseño deben
leer la firma de un nodo **sin ejecutarlo**, así que la firma es declarativa e
introspeccionable.

**Declaración de pines.** Cada tipo de nodo declara:

- `Inputs` / `Outputs`: modelos Pydantic anidados → pines de **datos** tipados.
- `exec_inputs` / `exec_outputs`: tuplas de nombres → pines de **ejecución** (no
  transportan datos, son aristas de control). Branch: `("true", "false")`. FlipFlop:
  `("a", "b")`.
- `is_pure: bool`: marca nodo puro (sin pines de ejecución, evaluable por pull). Cuando es
  `True`, no expone `exec_inputs`/`exec_outputs`.
- Método `describe()`: devuelve la firma completa por introspección, sin ejecutar.

**Firma de `execute`.**

```python
async def execute(self, inputs: BaseModel, ctx: ContextProtocol) -> NodeResult: ...
```

- `inputs`: modelo Pydantic ya validado (la firma de entrada).
- `ctx`: el contexto de ejecución — una implementación de `ContextProtocol`.
- Retorna `NodeResult(data: BaseModel, control: Control)`, donde `data` son las salidas de
  datos y `control` es una **instrucción de control** (ver sección 9), no un string de pin.

**`config` uniforme.** Todos los nodos reciben `__init__(self, instance_id, config: dict)`.
`config` son los parámetros fijos de la instancia (modelo, prompt, temperatura) que vienen
de `Instance.config` del JSON. Es el puente uniforme entre el grafo y el nodo; ningún nodo
usa constructores ad hoc.

**Acceso al contexto.** El `ContextProtocol` se pasa como argumento a `execute`. Es una
interfaz async — todos sus métodos se llaman con `await`. En producción es un Ray Actor
distribuido (`RayContextProxy`); en tests es `LocalContext` in-process. El código del nodo
no necesita saber cuál es.

- `await get_var(name)` / `await set_var(name, value)`: variables del grafo (nodos Get/Set).
- `await get_node_state(instance_id)` → `dict` (copia): estado oculto de un nodo concreto
  (bit del FlipFlop, contador), aislado por `instance_id`. El estado vive aquí, **no** en
  el objeto `Node`. Devuelve copia — nunca mutar el dict retornado.
- `await update_node_state(instance_id, patch)`: aplica un merge patch al estado del nodo.
- `await append_to_list(instance_id, key, value)`: append atómico a una lista dentro del
  estado (para nodos que acumulan historial en un contexto potencialmente distribuido).

**Distinción puro vs efecto.** El flag `is_pure`. Un nodo puro no tiene pines de ejecución,
se evalúa por pull y devuelve `Stop()` como control (nunca participa del flujo de
ejecución). Uno con efecto tiene al menos una entrada y una salida de ejecución y devuelve
una instrucción de control activa (`Goto`/`Repeat`/`Fork`).

## 8. Esquema del JSON del grafo — DEFINIDO

Código de referencia validado: `flowprint_graph_schema.py` (modelos Pydantic + validador
contra el contrato de Node).

**Criterio rector: que un LLM pueda leer y modificar el grafo de forma fiable.** Esto
inclinó varias decisiones hacia la uniformidad y la legibilidad, por encima de micro-
optimizaciones para el motor (que se recuperan en memoria al cargar).

**Decisión: lista única de conexiones con campo `kind`.** Todas las conexiones van en una
sola lista; cada una lleva `kind: "exec" | "data"`. Razón: un LLM modifica mejor un patrón
uniforme (siempre el mismo gesto: añadir un objeto con los mismos campos) que dos listas
entre las que debe elegir. El motor separa por tipo en memoria con un filtro trivial
(`exec_connections()` / `data_connections()`), así que no pierde nada.

**Tres mejoras para edición por LLM (parte de la decisión):**
- **Ids legibles:** `clasificador_1`, `branch_categoria`, no `n7f3a2`. El nombre dice qué
  es cada nodo; el LLM razona con más precisión.
- **Pines por nombre:** `from_pin: "true"`, `to_pin: "condition"` — los nombres reales del
  contrato, no índices. El LLM los conoce por la descripción del tipo.
- **Visual aparte:** posiciones y zoom en una sección `visual` separada. Son ruido para el
  LLM y no afectan la ejecución; puede editar la lógica sin tocarlas.

**Estructura del grafo (raíz):**
- `schema_version`: versión del esquema.
- `signature`: firma del grafo — `inputs` y `outputs` (nombre → tipo), lo que exponen
  `Start` y `End`.
- `variables`: variables nombradas del grafo (nodos Get/Set), cada una con nombre y tipo.
- `instances`: lista de instancias, cada una con `id` (legible), `type` (nombre del tipo en
  el registro) y `config` (parámetros fijos: modelo, prompt, temperatura — lo que NO llega
  por un pin).
- `connections`: lista única de aristas (`kind`, `from_node`, `from_pin`, `to_node`,
  `to_pin`).
- `visual`: metadatos visuales separados.

**Registro de tipos.** Un `NODE_REGISTRY` mapea nombre de tipo → clase `Node`. El grafo
referencia tipos por nombre; el registro los resuelve.

**Validación semántica.** Más allá del parseo estructural de Pydantic, un validador
comprueba contra el contrato de Node: ids únicos, tipos conocidos, y que cada conexión
referencie instancias y pines que existen y del `kind` correcto (un pin `exec` debe existir
en `exec_outputs`/`exec_inputs`; uno `data`, en `Outputs`/`Inputs`). Esto atrapa errores
—incluidos los de un LLM que invente un nombre de pin— antes de ejecutar.

## 9. Bucle del motor — DEFINIDO

Código de referencia validado: `flowprint_engine.py` (Sequence serial y repetición de
ForEach probados de extremo a extremo).

**Modelo de frentes como PILA (LIFO).** El motor mantiene una pila de frentes de
ejecución. Toma el frente superior, ejecuta su nodo, y apila los destinos que produce. La
consecuencia es que **el frente actual se agota antes de retomar los pendientes**, lo que
da el comportamiento serial de Blueprint. La excepción es `Fork`: cuando el nodo `Parallel`
emite esta instrucción, el motor lanza todas las ramas como Ray tasks concurrentes en lugar
de apilarlas.

**Evaluación pull SIN caché (modelo Unreal).** Antes de ejecutar un nodo, el motor
resuelve sus entradas de datos recorriendo hacia atrás las conexiones de datos
(`_resolve_inputs` → `_produce_output`). Un nodo puro se **reevalúa en el momento** de
leer su salida, sin guardar el resultado entre lecturas; resuelve recursivamente sus
propias entradas. Un nodo con efecto ya guardó su salida al ejecutarse, y esa se lee.

**Regla de diseño asociada:** lo caro nunca es puro. Los agentes (llamadas a LLM) son
siempre nodos con efecto, que corren una vez; si su resultado se necesita en varios
sitios, se guarda con `Set` y se lee con `Get`. Así nunca se reevalúa una llamada cara.

**Protocolo de control (sin `isinstance` de nodos).** El motor NO conoce los nodos de
control por su tipo. Cada nodo devuelve una **instrucción de control** y el motor
interpreta un vocabulario cerrado de cuatro:

- `Goto(pins)`: activar esos pines de ejecución en orden serial. Nodo normal = 1 pin;
  Sequence = varios en orden; Branch = el pin que eligió.
- `Repeat(pins)`: activar esos pines y **reencolar al nodo emisor**. Loops (ForEach,
  ForLoop, WhileLoop) lo usan para volver a sí mismos.
- `Stop()`: esta rama termina aquí. End, loop agotado, y todos los nodos puros.
- `Fork(pins)`: activar en paralelo como Ray tasks independientes. El nodo `Parallel` lo
  usa para lanzar N ramas concurrentes; el motor espera a que todas terminen antes de
  continuar.

El vocabulario es **cerrado** (4 casos que no crecen); los tipos de nodo son **abiertos**.
El motor discrimina sobre el vocabulario, no sobre los tipos, así que añadir ForLoop,
WhileLoop o Gate es escribir un archivo de nodo nuevo que devuelve estas instrucciones, sin
tocar el motor. Esto cumple la promesa de 4.6 ("el nodo declara, el motor ejecuta"), que la
versión anterior con `isinstance(node, Sequence)` no cumplía. Verificado por introspección:
el código del motor no menciona ningún tipo de nodo concreto.

**Sequence serial.** Devuelve `Goto(["1","2","3"])`. El motor apila los destinos en orden
inverso para que, con LIFO, la salida "1" se procese primero y su rama se agote antes de
la "2".

**Repetición de loops.** Un loop devuelve `Repeat(["body"])` mientras le queden elementos
(el motor reencola al loop y luego su cuerpo; por LIFO el cuerpo corre antes y, al agotarse,
el motor vuelve al loop) y `Goto(["completed"])` al terminar. El estado de iteración vive en
el contexto. Funciona porque el motor **no asume grafos acíclicos** (supuesto de 4.6).

**Fork paralelo con Ray.** Cuando el motor encuentra `Fork(pins)` y hay más de un destino,
llama a `_run_fork()`. Éste serializa todos los nodos del grafo (nombre de tipo + config),
lanza una `run_branch` Ray task por cada rama con `ray.remote`, y espera su finalización
con `asyncio.gather`. Cada tarea reconstruye los nodos en el worker, crea un `RayContextProxy`
sobre el mismo `_ContextActor` compartido, y corre un sub-Engine desde su nodo inicial.
Los eventos de cada rama llegan en batch al terminar y se re-emiten por el callback
`on_event` del motor padre. El contexto compartido garantiza coherencia entre ramas.

**Arranque y fin.** El motor arranca apilando el `Start` (sin entrada de ejecución, expone
los argumentos del grafo). Termina cuando la pila se vacía; el `End` guarda el resultado
del grafo en el contexto (`__result__`), que `run()` devuelve.

**Resolución de datos real (validada sin parches).** `flowprint_engine.py` implementa la
resolución pull real: `_resolve_inputs` recorre las conexiones de datos que entran a un
nodo y `_produce_output` evalúa cada origen, reevaluando nodos puros por pull recursivo
(puro que lee puros). Casos validados: Sequence serial con textos por conexión de datos
real; cadena puro→puro (Const+Const→Concat→agente); y ForEach con un nodo puro `ItemOf`
que lee el elemento actual en cada vuelta —demostración de por qué la ausencia de caché es
necesaria: un valor cacheado devolvería el primer elemento en todas las iteraciones.

---

## 10. Estado real: validado vs pendiente

Distinción honesta entre lo que el código de referencia **valida de verdad** y lo que aún
**falta** para programar la Fase 1 sin topar con decisiones a medio resolver.

**Validado en código (núcleo + integración):**
- Doble pin (ejecución/datos) y contrato de `Node` introspeccionable.
- Evaluación pull sin caché, incluida la cadena puro→puro y el nodo puro dentro de un loop.
- Pila LIFO; Sequence serial; repetición de loops con estado en el contexto.
- Protocolo de control: el motor no conoce nodos por tipo (vocabulario cerrado de 4
  instrucciones).
- `config` uniforme: todo nodo pasa su `config` a `super().__init__` y lee sus parámetros
  de `self.config` (sin atributos ad hoc). Corregido un bug donde los nodos del motor la
  descartaban.
- **Registro unificado** (`flowprint_registry.py`): un solo `NODE_REGISTRY` con todos los
  tipos (control, puros, estado, agentes). Lo comparten validador, cargador y motor.
- **Cargador `Graph`→motor** (`flowprint_loader.py`): valida el grafo, instancia los nodos
  vía el registro pasando `config`, deriva `exec_edges`/`data_edges` filtrando `connections`
  por `kind`, y devuelve un `Engine` listo. Rechaza grafos inválidos ANTES de ejecutar.
- **Prueba E2E** (`test_e2e.py`): JSON → validador → cargador → motor, sin construir nodos a
  mano; y un grafo inválido (pin inexistente) correctamente rechazado.

- **Validación de tipos en diseño (4.2): cerrada.** El validador (`flowprint_graph_schema.py`)
  comprueba compatibilidad entre `from_pin` y `to_pin`, no solo existencia. Regla:
  (1) tipos idénticos → ok; (2) salida subtipo de la entrada (herencia Pydantic) → ok;
  (3) conversión segura del catálogo `SAFE_CONVERSIONS` → reporta el nodo de cast a insertar
  (p. ej. `IntToFloat`, `ToStr`); (4) si nada aplica → incompatible, rechazado en diseño.
  Las conversiones son **nodos puros explícitos** (honestidad visual); en v1 el validador
  **detecta y reporta**, no inserta automáticamente. Validado: `bool→str` pide `ToStr`,
  `str→bool` se rechaza, subtipo Pydantic pasa en la dirección correcta.

**Huecos finos RESUELTOS (integración):**
- **Firma del `Start`/`End` tipada (4.5): hecho.** El cargador inyecta `signature` en la
  `config` de `Start` (como `input_names`) y `End` (como `output_names`). `Engine.run(start,
  args)` publica los argumentos del grafo en el contexto; `Start` los expone como variables;
  `End` compone un resultado tipado por nombre (`{salida: valor}`) en vez de `Any`. Validado:
  un grafo con `signature.inputs={nombre:str}` invocado con `{"nombre":"SrArtur"}` produce
  `{"saludo": "echo:SrArtur"}`. De paso se implementaron `GetVar`/`SetVar` (decididos en 3b,
  faltaban) y se corrigió que `Any` sea comodín en la validación de tipos.
- **Pin de entrada sin conexión: hecho.** El validador exige que todo pin de datos de
  entrada **requerido** (sin default Pydantic) tenga conexión; si falta, error en diseño. Un
  pin con default puede quedar sin conexión (usa el default). Nunca falla en runtime por dato
  ausente.
- **Manejo de errores en `execute`: hecho.** El bucle envuelve `execute` en try/except.
  Política v1: no reintentar; registrar `{node, error}` en el contexto (`__error__`) y
  detener devolviendo ese error. Validado con un nodo que lanza excepción.

*Con esto, todas las decisiones de diseño están cerradas y los huecos de integración
resueltos. El núcleo es programable como Fase 1 (ver sección 12).*

---

## 12. De los prototipos al repo: qué falta para programar la Fase 1

Los siete archivos de referencia validan el diseño, pero son prototipos en un solo
directorio plano. Para convertirlos en el proyecto real:

**Estructura del paquete.** Mover los prototipos a un paquete instalable:
`flowprint/` con `core/` (contrato `node.py`, `context.py`, vocabulario `control.py`),
`graph/` (esquema `schema.py`, validador `validation.py`, cargador `loader.py`,
`registry.py`), `nodes/` (un archivo por tipo de nodo: `control/`, `data/`, `agents/`),
y `engine.py`. Más `pyproject.toml`, `README.md`, `tests/`.

**Separar los nodos del motor.** Hoy `flowprint_engine.py` define a la vez el `Engine` y
todos los nodos de ejemplo (Start, End, Sequence, ForEach, Const, GetVar...). En el repo,
cada tipo de nodo va a su archivo bajo `nodes/`, y el registro los descubre. El motor queda
solo con el bucle.

**Tests de verdad (pytest).** Convertir los `if __name__` y los scripts de validación en
una suite: un test por comportamiento (pull sin caché, Sequence serial, repetición de loop,
protocolo de control, validación de tipos, pin requerido, error en execute, firma del
grafo). Los casos ya están escritos como prints; pasarlos a `assert`.

**Nodo-agente real.** `AgentEcho` es un simulador. El primer nodo de valor real es un
`LLMAgent` cuya `config` lleva modelo, prompt y temperatura, que llama a un proveedor por su
API. Su `Inputs`/`Outputs` siguen siendo Pydantic; encaja sin tocar el motor.

**Catálogo de nodos de conversión.** La validación de tipos ya *sugiere* nodos como
`IntToFloat`/`ToStr`; falta crearlos como nodos puros reales en `nodes/conversions/` y,
opcionalmente, una utilidad que los inserte automáticamente.

**Detalles de robustez aún sin abordar (no bloquean v1, conviene anotarlos):**
detección de ciclos no acotados (un grafo con un loop sin salida cuelga el motor);
límite de profundidad/iteraciones como cortacircuitos; serialización del contexto de
ejecución para pausar/reanudar; y logging estructurado en vez de prints.

**Orden sugerido para el repo:** (1) estructura del paquete + `pyproject.toml`; (2) mover
contrato, control y contexto a `core/`; (3) separar nodos a `nodes/`; (4) mover esquema,
validación, registro y cargador a `graph/`; (5) suite pytest a partir de los casos
existentes; (6) `LLMAgent` real; (7) nodos de conversión. Tras (5) ya tienes la Fase 1
ejecutable con tests; (6)–(7) la hacen útil.

---

## 13. Glosario

- **Instrucción de control:** valor que un nodo devuelve para decirle al motor cómo seguir
  el flujo, sin que el motor conozca el tipo del nodo. Vocabulario cerrado: `Goto`, `Repeat`,
  `Stop`, `Fork`.
- **Goto / Repeat / Stop / Fork:** activar pines en serie / activar y reencolar el nodo
  (loops) / terminar la rama / activar en paralelo (futuro).
- **Vocabulario cerrado vs tipos abiertos:** el motor discrimina sobre un conjunto fijo de
  instrucciones (cerrado, no crece), no sobre los tipos de nodo (abiertos, infinitos); por
  eso añadir nodos de control no toca el motor.
- **Pin de ejecución:** conector que define el orden de ejecución de los nodos.
- **Pin de datos:** conector que transporta valores tipados entre nodos.
- **Evaluación pull:** un valor se computa solo cuando alguien lo necesita, recorriendo
  hacia atrás las dependencias; opuesto a push.
- **Push:** modelo opuesto, donde un valor se propaga hacia adelante en cuanto se produce.
- **Async contagioso:** una función `async` obliga a que sus llamadores también sean
  `async`, propagándose hacia arriba en la cadena.
- **NodeResult:** valor de retorno de un nodo; incluye sus datos de salida y qué pin de
  salida de ejecución se activó.
- **Nodo puro:** nodo sin pin de ejecución que se evalúa bajo demanda y no tiene efectos
  secundarios; produce un valor a partir de sus entradas.
- **Nodo con efecto:** nodo con pin de ejecución que corre cuando recibe la señal y puede
  modificar estado o llamar servicios externos.
- **Modelo plano:** diseño donde solo existe un tipo `Node`; no hay subclase `Agent`. La
  diferencia de comportamiento vive en la implementación de `execute()`.
- **Contexto de ejecución:** contenedor externo al grafo donde vive el estado persistente
  de una corrida concreta; análogo a la instancia del actor en Unreal y a `state.db` en
  MFR-PDDL.
- **Autoconversión segura:** conversión de tipo insertada automáticamente por el motor
  cuando no pierde información relevante (int→float, valor→string para depuración).
- **Dataflow:** modelo de ejecución donde la disponibilidad de datos en las entradas de un
  nodo dispara su ejecución, sin flujo de control explícito separado.
- **Blackboard:** espacio de datos compartido al que cualquier nodo accede por clave;
  descartado en Flowprint para la comunicación entre nodos a favor de los pines.
- **Wire spaghetti:** enredo visual que resulta de cablear un dato a través de muchos nodos
  intermedios para llevarlo de un punto temprano a uno lejano.
- **Nodo Get/Set:** nodo visible que lee o escribe una variable nombrada del contexto del
  grafo, evitando el wire spaghetti sin perder honestidad visual.
- **Nodo Start:** punto de arranque único del grafo. Sin pin de entrada de ejecución;
  expone como pines de datos los argumentos con que se invocó el grafo.
- **Nodo End (Return):** punto de terminación del grafo. Recibe la señal de ejecución y
  toma por sus pines de datos los valores que el grafo devuelve como resultado.
- **Firma del grafo:** el conjunto de entradas (datos del Start) y salidas (datos del End)
  que hace al grafo invocable como una función y componible como nodo de otro grafo.
- **Tipo de nodo vs instancia:** el tipo es la definición reutilizable (código `.py`); la
  instancia es un nodo concreto colocado en un grafo con su posición, parámetros y
  conexiones (datos JSON).
- **Fuente de verdad:** representación canónica de la que derivan las demás. En Flowprint es
  el JSON del grafo; la API Python lo produce pero no lo reemplaza.
- **Round-trip:** capacidad de convertir entre dos representaciones (visual ↔ archivo) en
  ambos sentidos sin pérdida de información; garantizado al tener el JSON como fuente.
- **Frente de ejecución:** un punto activo de avance en el grafo. El motor mantiene una
  colección de frentes; en v1 suele haber uno, pero el modelo permite varios (paralelismo).
- **Grafo acíclico:** grafo sin ciclos. El motor de Flowprint NO lo asume, para permitir
  repetición (ForEach, loops).
- **Gather:** nodo futuro que lanza varias ramas de ejecución a la vez y espera a que todas
  terminen; equivalente a `asyncio.gather`. No existe en Blueprint.
- **Visualizador de solo lectura:** componente que renderiza el grafo JSON como diagrama sin
  permitir edición; sirve para depurar el motor antes de construir el editor interactivo.
