"""
models/venta.py
Modelo de dominio para una venta. Estructura de datos pura.
No importa nada de base de datos ni UI.
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Venta:
    """Representa una transacción de venta registrada en el sistema."""

    producto: str
    costo: float
    precio: float
    metodo_pago: str           # 'Efectivo', 'Bold', 'Addi', 'Transferencia', 'Otro', 'Combinado'
    fecha: date = field(default_factory=date.today)
    cantidad: int = 1          # Unidades vendidas en este registro
    comision: float = 0.0      # Valor calculado en pesos total (todas las unidades)
    ganancia_neta: float = 0.0 # (precio - costo - comision_unit) * cantidad
    notas: str = ""
    id: int | None = None      # None hasta ser persistido
    # Pagos combinados: lista de {"metodo": str, "monto": float} cuando el cliente
    # paga con más de un método. Si está presente, metodo_pago = "Combinado".
    pagos_combinados: list | None = None

    # ------------------------------------------------------------------
    # Propiedades derivadas (sin acceso a BD)
    # ------------------------------------------------------------------

    @property
    def ganancia_bruta(self) -> float:
        """Diferencia entre precio y costo multiplicada por cantidad."""
        return (self.precio - self.costo) * self.cantidad

    def __post_init__(self) -> None:
        """Validaciones básicas al construir el objeto."""
        if self.costo < 0:
            raise ValueError("El costo no puede ser negativo.")
        if self.precio < 0:
            raise ValueError("El precio no puede ser negativo.")
        if self.comision < 0:
            raise ValueError("La comisión no puede ser negativa.")
        if self.cantidad < 1:
            raise ValueError("La cantidad debe ser al menos 1.")
        if not self.producto.strip():
            raise ValueError("El nombre del producto no puede estar vacío.")
