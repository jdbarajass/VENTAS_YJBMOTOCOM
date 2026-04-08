"""
controllers/dashboard_controller.py
Caso de uso: obtener el resumen contable de un día para el dashboard.
"""

from datetime import date

from database.ventas_repo import obtener_ventas_por_fecha, obtener_ventas_por_mes
from database.gastos_dia_repo import obtener_gastos_por_fecha, obtener_gastos_por_mes
from database.config_repo import obtener_configuracion
from services.reportes import calcular_resumen_diario, ResumenDiario


class DashboardController:

    def get_resumen_dia(self, fecha: date) -> ResumenDiario:
        """
        Carga ventas, gastos operativos y configuración, calcula y retorna
        el ResumenDiario. Los gastos operativos del día se descuentan de la
        utilidad real junto con el gasto fijo diario prorrateado.
        """
        ventas = obtener_ventas_por_fecha(fecha)
        gastos = obtener_gastos_por_fecha(fecha)
        gastos_total = round(sum(g.monto for g in gastos), 2)
        cfg = obtener_configuracion()
        return calcular_resumen_diario(ventas, cfg, fecha, gastos_total)

    def get_proyeccion_mes(self, fecha: date) -> dict:
        """
        Calcula la proyección acumulada del mes hasta la fecha dada.
        Compara lo que se DEBERÍA tener vs lo que REALMENTE se tiene.
        """
        cfg = obtener_configuracion()

        ventas_mes = obtener_ventas_por_mes(fecha.year, fecha.month)
        ventas_hasta = [v for v in ventas_mes if v.fecha <= fecha]

        gastos_mes = obtener_gastos_por_mes(fecha.year, fecha.month)
        gastos_extra_hasta = round(
            sum(g.monto for g in gastos_mes if g.fecha <= fecha), 2
        )

        ganancia_acumulada = round(sum(v.ganancia_neta for v in ventas_hasta), 2)
        utilidad_acumulada = round(ganancia_acumulada - gastos_extra_hasta, 2)
        meta = round(cfg.gasto_diario * fecha.day, 2)
        diferencia = round(utilidad_acumulada - meta, 2)

        return {
            "dia": fecha.day,
            "dias_mes": cfg.dias_mes,
            "gasto_diario": cfg.gasto_diario,
            "meta": meta,
            "ganancia_acumulada": ganancia_acumulada,
            "gastos_extra_acumulados": gastos_extra_hasta,
            "utilidad_acumulada": utilidad_acumulada,
            "diferencia": diferencia,
        }
