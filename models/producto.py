"""
models/producto.py
Modelo de dominio puro para un producto del inventario.
"""

from dataclasses import dataclass


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
