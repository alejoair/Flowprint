"""Ejemplo de nodo custom: cuenta palabras en un texto.

Para crear tu propio nodo:
1. Copia este archivo con un nombre descriptivo.
2. Renombra la clase (el nombre de la clase es el 'type' que usas en el JSON del grafo).
3. Define Inputs / Outputs como modelos Pydantic con los pines de datos que necesitas.
4. Declara exec_inputs / exec_outputs si el nodo tiene pines de ejecución (is_pure = False).
   Si es un nodo puro (solo transforma datos, sin efectos), pon is_pure = True y omite los exec_*.
5. Implementa execute() devolviendo NodeResult(data, control).

Este nodo es puro: recibe un texto y devuelve cuántas palabras tiene.
"""

import sys
from pathlib import Path

# Permite importar desde el paquete flowprint cuando se ejecuta desde custom_nodes/
sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel

from flowprint_node_contract import Node, NodeResult, Stop


class WordCount(Node):
    class Inputs(BaseModel):
        text: str

    class Outputs(BaseModel):
        count: int

    is_pure = True

    async def execute(self, inputs: "WordCount.Inputs", ctx) -> NodeResult:
        count = len(inputs.text.split()) if inputs.text.strip() else 0
        return NodeResult(self.Outputs(count=count), Stop())
