"""Motor de Flowprint con PROTOCOLO DE CONTROL — sin isinstance.

El motor solo conoce un vocabulario de 4 instrucciones de control. No sabe qué
es un Sequence ni un ForEach: cada nodo de control devuelve una instrucción y el
motor la interpreta genéricamente.

Vocabulario:
  - Goto(pins)        -> activa esos pines de ejecución en orden (serial).
                         Nodo normal: 1 pin. Sequence: varios en orden.
  - Repeat(pins)      -> activa esos pines y REENCOLA al nodo emisor (loops).
  - Stop()            -> esta rama termina aquí (End, loop agotado).
  - Fork(pins)        -> activa esos pines en paralelo (futuro: gather). No v1.

Un nodo con efecto devuelve NodeResult(data, control). Un nodo de datos puro no
participa del flujo de ejecución (control = Stop por convención, nunca se usa).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from flowprint_node_contract import (ExecutionContext, Node, NodeResult,
                                      Goto, Repeat, Stop, Fork)


# ===========================================================================
# Vocabulario de control
# ===========================================================================
class Start(Node):
    """Expone los argumentos del grafo (signature.inputs) como datos de salida.
    El cargador pasa los nombres de input por config['input_names']; los valores
    de invocación llegan al contexto bajo '__args__' (los pone Engine.run)."""
    class Inputs(BaseModel): pass
    class Outputs(BaseModel): pass
    exec_inputs = (); exec_outputs = ("out",); is_pure = False

    async def execute(self, inputs, ctx):
        args = ctx.get_var("__args__") or {}
        # publica cada argumento del grafo como variable, accesible por Get o pull
        for name in self.config.get("input_names", []):
            ctx.set_var(name, args.get(name))
        return NodeResult(self.Outputs(), Goto(["out"]))


class End(Node):
    """Recoge el resultado del grafo. config['output_names'] define qué variables
    del contexto componen el resultado tipado (en vez de un Any genérico)."""
    class Inputs(BaseModel):
        result: Any = None
    exec_inputs = ("in",); exec_outputs = (); is_pure = False

    class Outputs(BaseModel): pass

    async def execute(self, inputs: "End.Inputs", ctx):
        names = self.config.get("output_names", [])
        if names:
            ctx.set_var("__result__", {n: ctx.get_var(n) for n in names})
        else:
            ctx.set_var("__result__", inputs.result)
        return NodeResult(self.Outputs(), Stop())


class Sequence(Node):
    class Inputs(BaseModel): pass
    class Outputs(BaseModel): pass
    exec_inputs = ("in",); exec_outputs = ("1", "2", "3"); is_pure = False
    def __init__(self, instance_id, config=None): super().__init__(instance_id, config)
    async def execute(self, inputs, ctx):
        # serial: el motor activará estos pines en orden
        return NodeResult(self.Outputs(), Goto(["1", "2", "3"]))


class ForEach(Node):
    class Inputs(BaseModel): pass
    class Outputs(BaseModel): pass
    exec_inputs = ("in",); exec_outputs = ("body", "completed"); is_pure = False
    def __init__(self, instance_id, config=None): super().__init__(instance_id, config)
    async def execute(self, inputs, ctx):
        st = ctx.node_state(self.instance_id)
        if "items" not in st:
            st["items"] = ctx.get_var("foreach_items") or []
            st["idx"] = 0
        idx, items = st["idx"], st["items"]
        if idx < len(items):
            st["current"] = items[idx]
            st["idx"] = idx + 1
            return NodeResult(self.Outputs(), Repeat(["body"]))  # reencólame
        return NodeResult(self.Outputs(), Goto(["completed"]))


class Const(Node):
    class Inputs(BaseModel): pass
    class Outputs(BaseModel): value: str
    is_pure = True
    async def execute(self, inputs, ctx):
        return NodeResult(self.Outputs(value=self.config.get("value", "")), Stop())


class Concat(Node):
    class Inputs(BaseModel): a: str; b: str
    class Outputs(BaseModel): value: str
    is_pure = True
    def __init__(self, instance_id, config=None): super().__init__(instance_id, config)
    async def execute(self, inputs, ctx):
        return NodeResult(self.Outputs(value=inputs.a + inputs.b), Stop())


class ItemOf(Node):
    class Inputs(BaseModel): pass
    class Outputs(BaseModel): value: str
    is_pure = True
    async def execute(self, inputs, ctx):
        fid = self.config.get("foreach_id")
        return NodeResult(self.Outputs(value=ctx.node_state(fid).get("current", "")), Stop())


class GetVar(Node):
    """Nodo PURO: lee una variable del grafo (config['var']) del contexto."""
    class Inputs(BaseModel): pass
    class Outputs(BaseModel): value: Any = None
    is_pure = True
    async def execute(self, inputs, ctx):
        return NodeResult(self.Outputs(value=ctx.get_var(self.config.get("var"))), Stop())


class SetVar(Node):
    """Nodo con EFECTO: escribe una variable del grafo (config['var'])."""
    class Inputs(BaseModel): value: Any = None
    class Outputs(BaseModel): pass
    exec_inputs = ("in",); exec_outputs = ("out",); is_pure = False
    async def execute(self, inputs: "SetVar.Inputs", ctx):
        ctx.set_var(self.config.get("var"), inputs.value)
        return NodeResult(self.Outputs(), Goto(["out"]))


class AgentEcho(Node):
    class Inputs(BaseModel): text: str
    class Outputs(BaseModel): reply: str
    exec_inputs = ("in",); exec_outputs = ("out",); is_pure = False
    def __init__(self, instance_id, config=None): super().__init__(instance_id, config)
    async def execute(self, inputs, ctx):
        ctx.node_state("__log__").setdefault("calls", []).append(f"agent({inputs.text})")
        await asyncio.sleep(0)
        return NodeResult(self.Outputs(reply=f"echo:{inputs.text}"), Goto(["out"]))


# ===========================================================================
# Motor — interpreta SOLO el vocabulario de control. Cero isinstance de nodos.
# ===========================================================================
class Engine:
    def __init__(self, nodes, exec_edges, data_edges, on_event=None):
        self.nodes = nodes
        self.exec_edges = exec_edges
        self.data_edges = data_edges
        self.ctx = ExecutionContext()
        self._on_event = on_event   # async callable(dict) | None
        self._cancelled = False

    def cancel(self) -> None:
        """Señala al motor que debe detenerse en la próxima iteración."""
        self._cancelled = True

    async def _emit(self, event: dict) -> None:
        if self._on_event:
            await self._on_event(event)

    async def _resolve_inputs(self, node_id):
        values = {}
        for (fn, fp, tn, tp) in self.data_edges:
            if tn == node_id:
                values[tp] = await self._produce_output(fn, fp)
        return values

    async def _produce_output(self, node_id, pin):
        node = self.nodes[node_id]
        if node.is_pure:
            sub = await self._resolve_inputs(node_id)
            res = await node.execute(node.Inputs(**sub), self.ctx)
            return getattr(res.data, pin)
        produced = self.ctx.node_state(node_id).get("__out__")
        return getattr(produced, pin) if produced is not None else None

    def _targets(self, node_id, pins):
        out = []
        for pin in pins:
            for (fn, fp, tn, tp) in self.exec_edges:
                if fn == node_id and fp == pin:
                    out.append(tn)
        return out

    async def run(self, start_id, args: dict | None = None):
        if args:
            self.ctx.set_var("__args__", args)
        stack = [start_id]
        while stack:
            if self._cancelled:
                await self._emit({"event": "cancelled"})
                return {"__cancelled__": True}

            node_id = stack.pop()
            node = self.nodes[node_id]

            await self._emit({"event": "node_start", "node": node_id})
            try:
                inputs = await self._resolve_inputs(node_id)
                result = await node.execute(node.Inputs(**inputs), self.ctx)
            except Exception as exc:
                error = {"node": node_id, "error": repr(exc)}
                self.ctx.set_var("__error__", error)
                await self._emit({"event": "error", **error})
                return {"__error__": error}

            self.ctx.node_state(node_id)["__out__"] = result.data
            await self._emit({
                "event": "node_complete",
                "node": node_id,
                "outputs": result.data.model_dump(),
            })

            # --- interpretar la instrucción de control, sin conocer el tipo del nodo ---
            ctrl = result.control
            if isinstance(ctrl, Stop):
                continue
            elif isinstance(ctrl, Goto):
                for nxt in reversed(self._targets(node_id, ctrl.pins)):
                    stack.append(nxt)
            elif isinstance(ctrl, Repeat):
                stack.append(node_id)
                for nxt in reversed(self._targets(node_id, ctrl.pins)):
                    stack.append(nxt)
            elif isinstance(ctrl, Fork):
                for nxt in reversed(self._targets(node_id, ctrl.pins)):
                    stack.append(nxt)

        result = self.ctx.get_var("__result__")
        await self._emit({"event": "graph_complete", "result": result})
        return result


# ===========================================================================
# Validación: mismos 3 casos, ahora sin isinstance de nodos en el motor
# ===========================================================================
async def main():
    # Caso 1: Sequence serial con datos reales
    nodes = {
        "start": Start("start"), "seq": Sequence("seq"),
        "a1": AgentEcho("a1"), "a2": AgentEcho("a2"), "a3": AgentEcho("a3"),
        "c1": Const("c1", {"value": "uno"}), "c2": Const("c2", {"value": "dos"}),
        "c3": Const("c3", {"value": "tres"}), "end": End("end"),
    }
    exec_edges = [("start","out","seq","in"), ("seq","1","a1","in"),
                  ("seq","2","a2","in"), ("seq","3","a3","in"), ("a3","out","end","in")]
    data_edges = [("c1","value","a1","text"), ("c2","value","a2","text"), ("c3","value","a3","text")]
    eng = Engine(nodes, exec_edges, data_edges); await eng.run("start")
    print("Caso 1 (Sequence serial):", eng.ctx.node_state("__log__").get("calls"))

    # Caso 2: pull recursivo puro->puro
    nodes2 = {
        "start": Start("start"), "ca": Const("ca", {"value": "hola_"}),
        "cb": Const("cb", {"value": "mundo"}), "cat": Concat("cat"),
        "ag": AgentEcho("ag"), "end": End("end"),
    }
    exec_edges2 = [("start","out","ag","in"), ("ag","out","end","in")]
    data_edges2 = [("ca","value","cat","a"), ("cb","value","cat","b"), ("cat","value","ag","text")]
    eng2 = Engine(nodes2, exec_edges2, data_edges2); await eng2.run("start")
    print("Caso 2 (pull puro->puro):", eng2.ctx.node_state("__log__").get("calls"))

    # Caso 3: ForEach con ItemOf puro
    nodes3 = {
        "start": Start("start"), "fe": ForEach("fe"),
        "item": ItemOf("item", {"foreach_id": "fe"}), "ag": AgentEcho("ag"), "end": End("end"),
    }
    exec_edges3 = [("start","out","fe","in"), ("fe","body","ag","in"), ("fe","completed","end","in")]
    data_edges3 = [("item","value","ag","text")]
    eng3 = Engine(nodes3, exec_edges3, data_edges3)
    eng3.ctx.set_var("foreach_items", ["x","y","z"]); await eng3.run("start")
    print("Caso 3 (ForEach + ItemOf):", eng3.ctx.node_state("__log__").get("calls"))

    # Comprobación: el motor no nombra ningún tipo de nodo concreto
    import inspect
    src = inspect.getsource(Engine)
    nombres = ["Sequence", "ForEach", "Branch", "AgentEcho", "Const", "ItemOf"]
    usados = [n for n in nombres if n in src]
    print("Tipos de nodo mencionados en el motor:", usados or "NINGUNO")


if __name__ == "__main__":
    asyncio.run(main())
