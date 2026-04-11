"""
models/factura.py
Modelo de dominio para facturas y recibos por pagar.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Factura:
    """Representa una factura o recibo pendiente de pago."""

    descripcion: str           # concepto / nombre de la factura
    proveedor: str             # proveedor o emisor
    monto: float               # monto total a pagar
    fecha_llegada: date        # cuándo llegó la factura
    estado: str = "pendiente"  # pendiente | pagada
    notas: str = ""
    id: int | None = None

    # Calculado — no se almacena
    @property
    def dias_transcurridos(self) -> int:
        return (date.today() - self.fecha_llegada).days

    def __post_init__(self) -> None:
        if not self.descripcion.strip():
            raise ValueError("La descripción no puede estar vacía.")
        if not isinstance(self.monto, (int, float)) or self.monto < 0:
            raise ValueError("El monto debe ser un número no negativo.")
        if self.estado not in ("pendiente", "pagada"):
            raise ValueError(f"Estado inválido: '{self.estado}'.")
        if not isinstance(self.fecha_llegada, date):
            raise ValueError("fecha_llegada debe ser un objeto date.")
