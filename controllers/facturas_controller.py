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
from database.abonos_factura_repo import (
    insertar_abono,
    obtener_abonos_por_factura,
    obtener_total_abonado,
    eliminar_abono,
)
from models.factura import Factura
from models.abono_factura import AbonoFactura


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
        fecha_vencimiento: date | None = None,
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
            fecha_vencimiento=fecha_vencimiento,
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

    def marcar_pagada(self, factura_id: int, fecha_pago: date | None = None) -> bool:
        """Marca la factura como pagada, registrando la fecha de pago (hoy si no se indica)."""
        return actualizar_estado_factura(factura_id, "pagada", fecha_pago or date.today())

    def eliminar(self, factura_id: int) -> bool:
        """Elimina una factura del historial."""
        return eliminar_factura(factura_id)

    # ------------------------------------------------------------------
    # Abonos
    # ------------------------------------------------------------------

    def registrar_abono(
        self,
        factura_id: int,
        monto: float,
        fecha: date,
        notas: str = "",
    ) -> AbonoFactura:
        """Registra un abono parcial. Si el total pagado ≥ monto, marca como pagada."""
        if monto <= 0:
            raise ValueError("El monto del abono debe ser mayor a cero.")
        a = AbonoFactura(factura_id=factura_id, monto=monto, fecha=fecha, notas=notas)
        insertar_abono(a)
        # Auto-cerrar si el total abonado cubre el monto completo
        total = obtener_total_abonado(factura_id)
        factura = next((f for f in obtener_todas_facturas() if f.id == factura_id), None)
        if factura and total >= factura.monto:
            actualizar_estado_factura(factura_id, "pagada", fecha)
        return a

    def cargar_abonos(self, factura_id: int) -> list[AbonoFactura]:
        return obtener_abonos_por_factura(factura_id)

    def total_abonado(self, factura_id: int) -> float:
        return obtener_total_abonado(factura_id)

    def eliminar_abono(self, abono_id: int) -> bool:
        return eliminar_abono(abono_id)
