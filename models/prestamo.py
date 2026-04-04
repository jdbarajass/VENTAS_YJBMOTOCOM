"""
models/prestamo.py
Modelo de dominio para un préstamo de producto a otro local.
No importa nada de base de datos ni UI.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Prestamo:
    """
    Representa un producto prestado a un almacén o local externo.
    Estados posibles:
      - 'pendiente': aún no han devuelto ni pagado
      - 'devuelto':  devolvieron el producto
      - 'cobrado':   lo vendieron y pagaron el valor
    """

    producto: str
    almacen: str                          # Nombre del local o almacén
    fecha: date = field(default_factory=date.today)
    observaciones: str = ""
    estado: str = "pendiente"             # pendiente | devuelto | cobrado
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.producto.strip():
            raise ValueError("El nombre del producto no puede estar vacío.")
        if not self.almacen.strip():
            raise ValueError("El nombre del almacén no puede estar vacío.")
        if self.estado not in ("pendiente", "devuelto", "cobrado"):
            raise ValueError("Estado inválido. Use: pendiente, devuelto o cobrado.")
