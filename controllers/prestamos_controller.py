"""
controllers/prestamos_controller.py
Casos de uso para la gestión de préstamos a locales/almacenes.
"""

from datetime import date

from database.prestamos_repo import (
    insertar_prestamo,
    obtener_todos_prestamos,
    obtener_prestamos_pendientes,
    actualizar_estado_prestamo,
    eliminar_prestamo,
)
from models.prestamo import Prestamo


class PrestamosController:

    def cargar_todos(self) -> list[Prestamo]:
        """Retorna todos los préstamos (todos los estados)."""
        return obtener_todos_prestamos()

    def cargar_pendientes(self) -> list[Prestamo]:
        """Retorna solo los préstamos pendientes."""
        return obtener_prestamos_pendientes()

    def registrar(
        self,
        producto: str,
        almacen: str,
        fecha: date,
        observaciones: str = "",
    ) -> Prestamo:
        """Valida y persiste un nuevo préstamo. Retorna el préstamo con id asignado."""
        if not producto.strip():
            raise ValueError("El nombre del producto no puede estar vacío.")
        if not almacen.strip():
            raise ValueError("El nombre del almacén no puede estar vacío.")

        p = Prestamo(
            producto=producto.strip(),
            almacen=almacen.strip(),
            fecha=fecha,
            observaciones=observaciones.strip(),
            estado="pendiente",
        )
        p.id = insertar_prestamo(p)
        return p

    def marcar_devuelto(self, prestamo_id: int) -> bool:
        """Marca el préstamo como devuelto."""
        return actualizar_estado_prestamo(prestamo_id, "devuelto")

    def marcar_cobrado(self, prestamo_id: int) -> bool:
        """Marca el préstamo como cobrado (lo vendieron y pagaron)."""
        return actualizar_estado_prestamo(prestamo_id, "cobrado")

    def eliminar(self, prestamo_id: int) -> bool:
        """Elimina un préstamo del historial."""
        return eliminar_prestamo(prestamo_id)
