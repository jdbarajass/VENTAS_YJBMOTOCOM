"""
services/calculator.py
Motor de cálculo contable — 100% testeable sin UI ni base de datos.

Recibe objetos del dominio (Venta, Configuracion) y retorna valores calculados.
Nunca importa nada de PySide6 ni de database/.
"""

from models.venta import Venta
from models.configuracion import Configuracion


# ------------------------------------------------------------------
# Cálculos de una venta individual
# ------------------------------------------------------------------

def calcular_comision(precio: float, metodo_pago: str, cfg: Configuracion) -> float:
    """
    Calcula la comisión en pesos según el método de pago.
    La comisión se aplica sobre el precio de venta (no sobre la ganancia).
    """
    porcentaje = cfg.porcentaje_para(metodo_pago)
    return round(precio * porcentaje / 100, 2)


def calcular_ganancia_bruta(precio: float, costo: float) -> float:
    """Diferencia entre precio de venta y costo del producto."""
    return round(precio - costo, 2)


def calcular_ganancia_neta(precio: float, costo: float, comision: float) -> float:
    """Ganancia después de descontar la comisión del intermediario."""
    return round(precio - costo - comision, 2)


def completar_venta(venta: Venta, cfg: Configuracion) -> Venta:
    """
    Toma una Venta con precio/costo/metodo_pago/cantidad y calcula + rellena
    comision y ganancia_neta (totales para todas las unidades).
    precio y costo se almacenan como valores UNITARIOS.
    """
    comision_unit = calcular_comision(venta.precio, venta.metodo_pago, cfg)
    venta.comision = round(comision_unit * venta.cantidad, 2)
    venta.ganancia_neta = round(
        calcular_ganancia_neta(venta.precio, venta.costo, comision_unit) * venta.cantidad, 2
    )
    return venta


# ------------------------------------------------------------------
# Cálculos de utilidad diaria
# ------------------------------------------------------------------

def calcular_utilidad_real_dia(
    ganancia_neta_total_dia: float,
    cfg: Configuracion,
) -> float:
    """
    Utilidad real de un día = suma de ganancias netas - gasto operativo diario.
    El gasto diario prorratea los gastos fijos mensuales entre los días del mes.
    """
    return round(ganancia_neta_total_dia - cfg.gasto_diario, 2)


def calcular_utilidad_real_mes(
    ganancia_neta_total_mes: float,
    cfg: Configuracion,
) -> float:
    """
    Utilidad real del mes completo = suma de ganancias netas - gastos fijos totales.
    Los gastos fijos son independientes de cuántos días se vendió.
    """
    return round(ganancia_neta_total_mes - cfg.total_gastos_mes, 2)
