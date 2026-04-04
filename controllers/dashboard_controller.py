"""
controllers/dashboard_controller.py
Caso de uso: obtener el resumen contable de un día para el dashboard.
"""

from datetime import date

from database.ventas_repo import obtener_ventas_por_fecha
from database.gastos_dia_repo import obtener_gastos_por_fecha
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
