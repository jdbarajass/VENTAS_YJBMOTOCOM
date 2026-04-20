"""
models/producto.py
Modelo de dominio puro para un producto del inventario.
"""

import re
from dataclasses import dataclass

_PAT_TALLA = re.compile(r"-T:(\w+)$")


@dataclass
class Producto:
    producto: str
    costo_unitario: float
    cantidad: int = 0
    serial: str = ""
    codigo_barras: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not str(self.producto).strip():
            raise ValueError("El nombre del producto no puede estar vacío.")
        if self.costo_unitario < 0:
            raise ValueError("El costo unitario no puede ser negativo.")
        if self.cantidad < 0:
            self.cantidad = 0

    @property
    def talla(self) -> str:
        """Extrae la talla del nombre del producto (formato -T:M). 'N/A' si no aplica."""
        m = _PAT_TALLA.search(self.producto or "")
        return m.group(1) if m else "N/A"
