"""
models/gasto_dia.py
Modelo de dominio para un gasto operativo puntual de un día.
Ejemplos: compra de insumos, reparación, flete, etc.
"""

from dataclasses import dataclass, field
from datetime import date


CATEGORIAS_GASTO = ["Transporte", "Alimentación", "Insumos", "Banco", "Otro"]


@dataclass
class GastoDia:
    """Gasto operativo registrado en un día específico."""

    descripcion: str
    monto: float
    fecha: date = field(default_factory=date.today)
    id: int | None = None
    categoria: str = "Otro"

    def __post_init__(self) -> None:
        if not self.descripcion.strip():
            raise ValueError("La descripción del gasto no puede estar vacía.")
        if self.monto <= 0:
            raise ValueError("El monto del gasto debe ser mayor a cero.")
        if self.categoria not in CATEGORIAS_GASTO:
            self.categoria = "Otro"
