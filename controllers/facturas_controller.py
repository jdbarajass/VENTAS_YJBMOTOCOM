"""
controllers/facturas_controller.py
Casos de uso para la gestión de facturas y recibos.
"""

from datetime import date

from database.facturas_repo import (
    insertar_factura,
    obtener_todas_facturas,
    obtener_facturas_pendientes,
    actualizar_factura,
    actualizar_estado_factura,
    eliminar_factura,
)
from models.factura import Factura


class FacturasController:

    def cargar_todos(self) -> list[Factura]:
        """Retorna todas las facturas (todos los estados)."""
        return obtener_todas_facturas()

    def cargar_pendientes(self) -> list[Factura]:
        """Retorna solo las facturas pendientes."""
        return obtener_facturas_pendientes()

    def registrar(
        self,
        descripcion: str,
        proveedor: str,
        monto: float,
        fecha_llegada: date,
        notas: str = "",
    ) -> Factura:
        """Valida y persiste una nueva factura. Retorna la factura con id asignado."""
        if not descripcion.strip():
            raise ValueError("La descripción no puede estar vacía.")
        if monto < 0:
            raise ValueError("El monto no puede ser negativo.")

        f = Factura(
            descripcion=descripcion.strip(),
            proveedor=proveedor.strip(),
            monto=monto,
            fecha_llegada=fecha_llegada,
            notas=notas.strip(),
            estado="pendiente",
        )
        f.id = insertar_factura(f)
        return f

    def editar(self, f: Factura) -> bool:
        """Persiste los cambios de una factura existente."""
        if not f.descripcion.strip():
            raise ValueError("La descripción no puede estar vacía.")
        if f.monto < 0:
            raise ValueError("El monto no puede ser negativo.")
        return actualizar_factura(f)

    def marcar_pagada(self, factura_id: int) -> bool:
        """Marca la factura como pagada."""
        return actualizar_estado_factura(factura_id, "pagada")

    def eliminar(self, factura_id: int) -> bool:
        """Elimina una factura del historial."""
        return eliminar_factura(factura_id)
