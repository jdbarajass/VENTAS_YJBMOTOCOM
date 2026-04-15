"""
models/abono_factura.py
Modelo de dominio para abonos (pagos parciales) de una factura.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class AbonoFactura:
    """Pago parcial registrado contra una factura pendiente."""

    factura_id: int
    monto: float
    fecha: date
    notas: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if self.monto <= 0:
            raise ValueError("El monto del abono debe ser mayor a cero.")
        if not isinstance(self.fecha, date):
            raise ValueError("La fecha del abono debe ser un objeto date.")
