"""
models/factura.py
Modelo de dominio para facturas y recibos por pagar.
"""

from dataclasses import dataclass
from datetime import date


@dataclass
class Factura:
    """Representa una factura o recibo pendiente de pago."""

    descripcion: str                    # concepto / nombre de la factura
    proveedor: str                      # proveedor o emisor
    monto: float                        # monto total a pagar
    fecha_llegada: date                 # cuándo llegó la factura
    estado: str = "pendiente"           # pendiente | pagada
    notas: str = ""
    id: int | None = None
    fecha_vencimiento: date | None = None  # fecha límite de pago (opcional)

    # Calculados — no se almacenan
    @property
    def dias_transcurridos(self) -> int:
        """Días desde que llegó la factura."""
        return (date.today() - self.fecha_llegada).days

    @property
    def dias_para_vencer(self) -> int | None:
        """Días hasta la fecha de vencimiento. Negativo = vencida. None si no hay fecha."""
        if self.fecha_vencimiento is None:
            return None
        return (self.fecha_vencimiento - date.today()).days

    def __post_init__(self) -> None:
        if not self.descripcion.strip():
            raise ValueError("La descripción no puede estar vacía.")
        if not isinstance(self.monto, (int, float)) or self.monto < 0:
            raise ValueError("El monto debe ser un número no negativo.")
        if self.estado not in ("pendiente", "pagada"):
            raise ValueError(f"Estado inválido: '{self.estado}'.")
        if not isinstance(self.fecha_llegada, date):
            raise ValueError("fecha_llegada debe ser un objeto date.")
