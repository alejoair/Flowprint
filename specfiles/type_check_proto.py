"""Prototipo de la comprobación de compatibilidad de tipos entre pines.

Regla (decisión 4.2): una conexión de datos from_pin -> to_pin es válida si
  1) los tipos son idénticos, o
  2) el tipo de salida es SUBTIPO del de entrada (herencia Pydantic / clases), o
  3) existe una CONVERSIÓN SEGURA en el catálogo (se reporta como nodo sugerido).
Si nada aplica -> incompatible (se rechaza en diseño).

El catálogo de conversiones son NODOS PUROS explícitos (honestidad visual):
convertir es un nodo más en el grafo, no una transformación oculta del motor.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


# Catálogo de conversiones seguras: (tipo_origen, tipo_destino) -> nodo de cast.
SAFE_CONVERSIONS: dict[tuple[type, type], str] = {
    (int, float): "IntToFloat",
    (int, str): "ToStr",
    (float, str): "ToStr",
    (bool, str): "ToStr",
    (bool, int): "BoolToInt",
}


def check_compat(src_t: type, dst_t: type) -> tuple[str, str | None]:
    """Devuelve (estado, nodo_conversion).
    estado: 'ok' | 'convert' | 'incompatible'
    nodo_conversion: nombre del nodo de cast si estado == 'convert', si no None.
    """
    if src_t == dst_t:
        return ("ok", None)
    # subtipo: src es subclase de dst (un derivado encaja donde se espera la base)
    if isinstance(src_t, type) and isinstance(dst_t, type) and issubclass(src_t, dst_t):
        return ("ok", None)
    # conversión segura del catálogo
    if (src_t, dst_t) in SAFE_CONVERSIONS:
        return ("convert", SAFE_CONVERSIONS[(src_t, dst_t)])
    return ("incompatible", None)


# --- Tipos de ejemplo para probar subtipo con Pydantic ---
class Mensaje(BaseModel):
    texto: str

class MensajeUrgente(Mensaje):   # subtipo de Mensaje
    prioridad: int = 1


if __name__ == "__main__":
    casos = [
        ("idéntico str->str", str, str),
        ("int->float (seguro)", int, float),
        ("int->str (seguro)", int, str),
        ("str->int (NO seguro)", str, int),
        ("subtipo MensajeUrgente->Mensaje", MensajeUrgente, Mensaje),
        ("supertipo Mensaje->MensajeUrgente (NO)", Mensaje, MensajeUrgente),
    ]
    for nombre, s, d in casos:
        estado, conv = check_compat(s, d)
        extra = f" (insertar nodo {conv})" if conv else ""
        print(f"{nombre:42} -> {estado}{extra}")
