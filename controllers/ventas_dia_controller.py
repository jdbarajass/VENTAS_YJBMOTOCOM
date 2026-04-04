"""
controllers/ventas_dia_controller.py
Casos de uso para la vista de ventas del día: listar, eliminar, exportar.
"""

from datetime import date
from pathlib import Path

from models.venta import Venta
from database.ventas_repo import (
    obtener_ventas_por_fecha,
    eliminar_venta,
)
from database.config_repo import obtener_configuracion
from services.exportador import exportar_ventas_dia


class VentasDiaController:

    def cargar_ventas(self, fecha: date) -> list[Venta]:
        """Retorna todas las ventas del día dado, ordenadas por id."""
        return obtener_ventas_por_fecha(fecha)

    def eliminar(self, venta_id: int) -> bool:
        """Elimina una venta por id. Retorna True si se eliminó."""
        return eliminar_venta(venta_id)

    def exportar_excel(self, ventas: list[Venta], fecha: date, ruta: Path) -> None:
        """Genera el archivo Excel en la ruta indicada."""
        exportar_ventas_dia(ventas, fecha, ruta)
