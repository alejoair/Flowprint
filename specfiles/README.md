# Flowprint — prototipos de referencia

Motor de orquestación multiagente en Python basado en el modelo Blueprint de
Unreal. Estos archivos son **prototipos validados** que fijan el diseño; no son
todavía el paquete final (ver sección 12 del spec para llevarlos al repo).

## Por dónde empezar

1. **`flowprint-spec.md`** — el documento de diseño completo. Empieza aquí.
   Toda decisión, su porqué y las alternativas descartadas. La sección 10
   distingue lo validado de lo pendiente; la 12 explica cómo pasar al repo.

## Archivos de código (orden de dependencia)

- **`flowprint_node_contract.py`** — contrato base: `Node`, `NodeResult`,
  `ExecutionContext` y el vocabulario de control (`Goto`/`Repeat`/`Stop`/`Fork`).
- **`flowprint_engine.py`** — el motor (bucle de frentes, pull sin caché) y los
  tipos de nodo de ejemplo (Start, End, Sequence, ForEach, Const, GetVar,
  SetVar, AgentEcho...).
- **`flowprint_graph_schema.py`** — esquema JSON del grafo + validador
  (existencia de pines, compatibilidad de tipos, pines requeridos sin conexión).
- **`flowprint_registry.py`** — registro único nombre→clase de nodo.
- **`flowprint_loader.py`** — puente: `Graph` (JSON) → instancias + aristas →
  `Engine` listo. `run_graph(graph, args)`.
- **`test_e2e.py`** — prueba de extremo a extremo: JSON → validador → cargador →
  motor.
- **`type_check_proto.py`** — prototipo aislado de la regla de compatibilidad de
  tipos (referencia).

## Ejecutar

```bash
pip install pydantic
python test_e2e.py
```

## Estado

Todas las decisiones de diseño están cerradas y los huecos de integración
resueltos. Lo que sigue es empaquetado (estructura de paquete, separar nodos,
suite pytest) y la primera funcionalidad real (`LLMAgent`). Detalle en la
sección 12 del spec.
