"""Ejemplo de nodo custom: cuenta palabras en un texto.

Para crear tu propio nodo:
1. Copia este archivo con un nombre descriptivo.
2. Renombra la clase (el nombre de la clase es el 'type' en el JSON del grafo).
3. Define Inputs / Outputs como modelos Pydantic.
4. Si el nodo tiene pines de ejecución: is_pure = False, declara exec_inputs/exec_outputs.
   Si solo transforma datos: is_pure = True.
5. Implementa execute() devolviendo NodeResult(data, control).
"""

from pydantic import BaseModel

from flowprint.core.control import Stop
from flowprint.core.node import Node, NodeResult


class WordCount(Node):
    class Inputs(BaseModel):
        text: str

    class Outputs(BaseModel):
        count: int

    is_pure = True

    async def execute(self, inputs: "WordCount.Inputs", ctx) -> NodeResult:
        count = len(inputs.text.split()) if inputs.text.strip() else 0
        return NodeResult(self.Outputs(count=count), Stop())
