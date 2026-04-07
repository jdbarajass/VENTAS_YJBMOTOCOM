"""
controllers/historial_controller.py
Caso de uso: resumen mensual para el historial.
"""

from pathlib import Path

from database.ventas_repo import obtener_ventas_por_mes
from database.gastos_dia_repo import obtener_gastos_por_mes
from database.config_repo import obtener_configuracion
from database.prestamos_repo import obtener_todos_prestamos
from services.reportes import calcular_resumen_mensual, ResumenMensual
from services.exportador import exportar_ventas_mes


class HistorialController:

    def cargar_ventas_mes(self, año: int, mes: int) -> list:
        """Retorna la lista de ventas individuales del mes."""
        return obtener_ventas_por_mes(año, mes)

    def cargar_resumen_mes(self, año: int, mes: int) -> ResumenMensual:
        """
        Carga todas las ventas del mes, los gastos operativos diarios,
        la configuración activa y retorna el resumen mensual calculado.
        """
        ventas = obtener_ventas_por_mes(año, mes)
        gastos = obtener_gastos_por_mes(año, mes)
        gastos_por_dia: dict = {}
        for g in gastos:
            gastos_por_dia[g.fecha] = gastos_por_dia.get(g.fecha, 0.0) + g.monto
        cfg = obtener_configuracion()
        return calcular_resumen_mensual(ventas, cfg, año, mes, gastos_por_dia)

    def exportar_excel(self, año: int, mes: int, ruta: Path) -> None:
        """Genera el Excel con todas las ventas del mes y hoja de préstamos."""
        ventas = obtener_ventas_por_mes(año, mes)
        prestamos = obtener_todos_prestamos()
        exportar_ventas_mes(ventas, año, mes, ruta, prestamos=prestamos)
