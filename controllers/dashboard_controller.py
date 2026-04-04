"""
controllers/dashboard_controller.py
Caso de uso: obtener el resumen contable de un día para el dashboard.
"""

from datetime import date

from database.ventas_repo import obtener_ventas_por_fecha
from database.config_repo import obtener_configuracion
from services.reportes import calcular_resumen_diario, ResumenDiario


class DashboardController:

    def get_resumen_dia(self, fecha: date) -> ResumenDiario:
        """
        Carga ventas y configuración, calcula y retorna el ResumenDiario.
        Si no hay ventas, retorna resumen con ceros (el gasto diario igual corre).
        """
        ventas = obtener_ventas_por_fecha(fecha)
        cfg = obtener_configuracion()
        return calcular_resumen_diario(ventas, cfg, fecha)
