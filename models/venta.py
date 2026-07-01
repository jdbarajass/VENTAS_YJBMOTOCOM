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
    # Agrupa varias ventas de un mismo carrito (multi-producto). None = venta simple.
    grupo_venta_id: int | None = None
    # Número de factura consecutivo compartido por todo el carrito.
    numero_factura: int | None = None
    # Hora de registro en formato "HH:MM". Vacío en ventas históricas.
    hora: str = ""
    # Campos del comprobante de venta
    vendedor: str = ""
    cliente_nombre: str = ""
    cliente_cedula: str = ""
    cliente_tel: str = ""
    descuento: int = 0         # ahorro total del carrito en pesos (solo en v0, informativo)
    sku: str = ""              # código/serial del producto
    # Precio que se le anunció al cliente antes del descuento. 0 = sin descuento.
    precio_ofertado: float = 0.0
    # Talla del producto vendido (ej. "M", "L", "XL"). Vacío para productos sin talla.
    talla: str = ""

    # ------------------------------------------------------------------
    # Propiedades derivadas (sin acceso a BD)
    # ------------------------------------------------------------------

    @property
    def ganancia_bruta(self) -> float:
        """Diferencia entre precio y costo multiplicada por cantidad."""
        return (self.precio - self.costo) * self.cantidad

    def ingreso_real(self) -> float:
        """
        Importe real cobrado al cliente, compatible con ambos modelos de descuento.
        - Modelo nuevo (precio_ofertado > 0): precio ya es el real; precio_ofertado es el anunciado.
        - Modelo antiguo (descuento > 0): precio es el anunciado; descuento es el ahorro.
        """
        _po = self.precio_ofertado or 0.0
        _d  = self.descuento or 0
        return self.precio * self.cantidad - (0 if _po > 0 else _d)

    def total_cobrado_cliente(self) -> float:
        """
        Total que debe pagar el cliente, incluyendo la comisión trasladada
        (Addi, Datafono o Transferencia con comisión configurada).
        """
        return self.ingreso_real() + self.comision

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
