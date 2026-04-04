"""
services/reportes.py
Agregaciones contables para el dashboard diario y el historial mensual.

Recibe listas de Venta ya cargadas desde la BD y una Configuracion.
No accede a la base de datos directamente — eso lo hacen los controllers.
"""

from dataclasses import dataclass, field
from datetime import date
from collections import defaultdict

from models.venta import Venta
from models.configuracion import Configuracion
from services.calculator import (
    calcular_utilidad_real_dia,
    calcular_utilidad_real_mes,
)


# ------------------------------------------------------------------
# Estructuras de resultado
# ------------------------------------------------------------------

@dataclass
class ResumenDiario:
    """Métricas consolidadas de un día de operaciones."""
    fecha: date
    cantidad_ventas: int = 0
    total_ingresos: float = 0.0     # suma de precios × cantidad
    total_costos: float = 0.0       # suma de costos × cantidad
    total_comisiones: float = 0.0   # suma de comisiones pagadas
    ganancia_bruta: float = 0.0     # total_ingresos - total_costos
    ganancia_neta: float = 0.0      # ganancia_bruta - total_comisiones
    gasto_diario: float = 0.0       # prorrateado de gastos fijos mensuales
    gastos_operativos: float = 0.0  # gastos puntuales del día (compras, reparaciones…)
    utilidad_real: float = 0.0      # ganancia_neta - gasto_diario - gastos_operativos

    @property
    def es_positivo(self) -> bool:
        return self.utilidad_real >= 0

    @property
    def margen_porcentual(self) -> float:
        """Margen de utilidad real sobre ingresos (%)."""
        if self.total_ingresos == 0:
            return 0.0
        return round(self.utilidad_real / self.total_ingresos * 100, 1)


@dataclass
class ResumenMensual:
    """Métricas consolidadas de un mes completo."""
    año: int
    mes: int
    cantidad_ventas: int = 0
    total_ingresos: float = 0.0
    total_costos: float = 0.0
    total_comisiones: float = 0.0
    ganancia_bruta: float = 0.0
    ganancia_neta: float = 0.0
    total_gastos_fijos: float = 0.0   # arriendo + sueldo + servicios + otros
    utilidad_real: float = 0.0        # ganancia_neta - total_gastos_fijos
    dias_positivos: int = 0
    dias_negativos: int = 0
    resumen_por_dia: list[ResumenDiario] = field(default_factory=list)

    @property
    def dias_con_ventas(self) -> int:
        return len(self.resumen_por_dia)

    @property
    def es_positivo(self) -> bool:
        return self.utilidad_real >= 0

    @property
    def promedio_diario(self) -> float:
        """Utilidad real promedio por día trabajado."""
        if self.dias_con_ventas == 0:
            return 0.0
        return round(self.utilidad_real / self.dias_con_ventas, 2)


# ------------------------------------------------------------------
# Funciones de cálculo
# ------------------------------------------------------------------

def calcular_resumen_diario(
    ventas: list[Venta],
    cfg: Configuracion,
    fecha: date,
    gastos_operativos: float = 0.0,
) -> ResumenDiario:
    """
    Agrega todas las ventas de un día en un ResumenDiario.
    gastos_operativos: suma de gastos puntuales del día (compras, reparaciones…).
    """
    resumen = ResumenDiario(fecha=fecha)
    resumen.gasto_diario = cfg.gasto_diario
    resumen.gastos_operativos = round(gastos_operativos, 2)
    resumen.cantidad_ventas = sum(v.cantidad for v in ventas)

    for v in ventas:
        resumen.total_ingresos += v.precio * v.cantidad
        resumen.total_costos += v.costo * v.cantidad
        resumen.total_comisiones += v.comision
        resumen.ganancia_neta += v.ganancia_neta

    resumen.total_ingresos = round(resumen.total_ingresos, 2)
    resumen.total_costos = round(resumen.total_costos, 2)
    resumen.total_comisiones = round(resumen.total_comisiones, 2)
    resumen.ganancia_bruta = round(resumen.total_ingresos - resumen.total_costos, 2)
    resumen.ganancia_neta = round(resumen.ganancia_neta, 2)
    resumen.utilidad_real = round(
        calcular_utilidad_real_dia(resumen.ganancia_neta, cfg) - resumen.gastos_operativos, 2
    )

    return resumen


def calcular_resumen_mensual(
    ventas: list[Venta],
    cfg: Configuracion,
    año: int,
    mes: int,
    gastos_por_dia: "dict[date, float] | None" = None,
) -> ResumenMensual:
    """
    Agrega todas las ventas de un mes y construye los resúmenes diarios internos.
    Los gastos fijos mensuales se restan completos (independiente de días trabajados).
    """
    gastos_por_dia = gastos_por_dia or {}
    resumen = ResumenMensual(año=año, mes=mes)
    resumen.total_gastos_fijos = cfg.total_gastos_mes

    # Agrupar ventas por fecha
    por_fecha: dict[date, list[Venta]] = defaultdict(list)
    for v in ventas:
        por_fecha[v.fecha].append(v)

    # Construir resúmenes diarios
    for fecha_dia in sorted(por_fecha.keys()):
        ventas_dia = por_fecha[fecha_dia]
        gastos_extra = gastos_por_dia.get(fecha_dia, 0.0)
        rd = calcular_resumen_diario(ventas_dia, cfg, fecha_dia, gastos_extra)
        resumen.resumen_por_dia.append(rd)

        resumen.cantidad_ventas += rd.cantidad_ventas
        resumen.total_ingresos += rd.total_ingresos
        resumen.total_costos += rd.total_costos
        resumen.total_comisiones += rd.total_comisiones
        resumen.ganancia_neta += rd.ganancia_neta

        if rd.es_positivo:
            resumen.dias_positivos += 1
        else:
            resumen.dias_negativos += 1

    resumen.total_ingresos = round(resumen.total_ingresos, 2)
    resumen.total_costos = round(resumen.total_costos, 2)
    resumen.total_comisiones = round(resumen.total_comisiones, 2)
    resumen.ganancia_bruta = round(resumen.total_ingresos - resumen.total_costos, 2)
    resumen.ganancia_neta = round(resumen.ganancia_neta, 2)
    resumen.utilidad_real = calcular_utilidad_real_mes(resumen.ganancia_neta, cfg)

    return resumen
