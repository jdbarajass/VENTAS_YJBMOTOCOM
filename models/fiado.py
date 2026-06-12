"""
models/fiado.py
Modelo de dominio para el control de clientes deudores (fiado).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class Fiado:
    cliente_nombre: str
    descripcion: str
    monto_total: float
    fecha: date
    estado: str = "pendiente"          # pendiente | pagado
    cliente_cedula: str = ""
    cliente_tel: str = ""
    notas: str = ""
    id: Optional[int] = None

    @property
    def dias_transcurridos(self) -> int:
        return (date.today() - self.fecha).days


@dataclass
class AbonoFiado:
    fiado_id: int
    monto: float
    fecha: date
    notas: str = ""
    id: Optional[int] = None
