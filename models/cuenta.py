"""
models/cuenta.py
Modelos de dominio para el sistema de Cuentas.
"""

from dataclasses import dataclass, field


@dataclass
class Cuenta:
    """Representa una cuenta/medio de pago con su saldo."""
    id: int | None = None
    nombre: str = ""
    metodo_pago: str = ""       # coincide con ventas.metodo_pago
    balance_actual: float = 0.0
    color: str = "#3B82F6"
    activa: bool = True
    orden: int = 0


@dataclass
class MovimientoCuenta:
    """Registra cada cambio en el saldo de una cuenta."""
    id: int | None = None
    cuenta_id: int = 0
    fecha: str = ""
    tipo: str = ""              # 'venta', 'ajuste_manual', 'transferencia_salida', 'transferencia_entrada'
    monto: float = 0.0          # positivo = ingreso, negativo = egreso
    descripcion: str = ""
    venta_id: int | None = None


@dataclass
class CierreMensual:
    """Snapshot del estado de todas las cuentas al cierre de un mes."""
    id: int | None = None
    anio: int = 0
    mes: int = 0                # 1–12
    datos_json: str = ""        # JSON: [{cuenta_id, nombre, balance}]
    notas: str = ""
    fecha_cierre: str = ""
