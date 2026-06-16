"""
controllers/ventas_dia_controller.py
Casos de uso para la vista de ventas del día: listar, eliminar, exportar.
"""

from datetime import date
from pathlib import Path

from models.venta import Venta
from models.gasto_dia import GastoDia
from database.ventas_repo import obtener_ventas_por_fecha
from database.gastos_dia_repo import (
    insertar_gasto,
    obtener_gastos_por_fecha,
    obtener_gasto_por_id,
    eliminar_gasto as _eliminar_gasto_repo,
)
from database.cuentas_repo import revertir_gasto as _revertir_gasto
from services.exportador import exportar_ventas_dia


class VentasDiaController:

    def cargar_ventas(self, fecha: date) -> list[Venta]:
        """Retorna todas las ventas del día dado, ordenadas por id."""
        return obtener_ventas_por_fecha(fecha)

    def eliminar(self, venta_id: int) -> bool:
        """Elimina una venta y revierte stock e inventario. Retorna True si se eliminó."""
        from controllers.venta_controller import VentaController
        return VentaController().eliminar_venta(venta_id)

    def exportar_excel(self, ventas: list[Venta], fecha: date, ruta: Path) -> None:
        """Genera el archivo Excel en la ruta indicada."""
        exportar_ventas_dia(ventas, fecha, ruta)

    # ------------------------------------------------------------------
    # Gastos operativos del día
    # ------------------------------------------------------------------

    def cargar_gastos(self, fecha: date) -> list[GastoDia]:
        """Retorna los gastos operativos del día dado."""
        return obtener_gastos_por_fecha(fecha)

    def agregar_gasto(self, descripcion: str, monto: float, fecha: date,
                      categoria: str = "Otro",
                      cuenta_pago: str = "Efectivo") -> GastoDia:
        """Valida y persiste un nuevo gasto operativo. Lanza ValueError si inválido."""
        gasto = GastoDia(descripcion=descripcion, monto=monto, fecha=fecha,
                         categoria=categoria, cuenta_pago=cuenta_pago)
        insertar_gasto(gasto)
        return gasto

    def obtener_gasto(self, gasto_id: int) -> GastoDia | None:
        """Retorna un gasto por id, o None si no existe."""
        return obtener_gasto_por_id(gasto_id)

    def eliminar_gasto(self, gasto_id: int) -> bool:
        """Elimina un gasto operativo y revierte el débito en la cuenta correspondiente."""
        gasto = obtener_gasto_por_id(gasto_id)
        resultado = _eliminar_gasto_repo(gasto_id)
        if resultado and gasto:
            try:
                _revertir_gasto(gasto)
            except Exception:
                pass
        return resultado
