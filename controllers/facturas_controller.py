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
    obtener_abono_por_id,
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

    def marcar_pagada(
        self, factura_id: int, fecha_pago: date | None = None,
        cuenta_id: int | None = None,
    ) -> bool:
        """Marca la factura como pagada y debita el saldo pendiente de la cuenta indicada."""
        fecha = fecha_pago or date.today()
        factura = next((f for f in obtener_todas_facturas() if f.id == factura_id), None)
        resultado = actualizar_estado_factura(factura_id, "pagada", fecha, cuenta_id)
        if resultado and factura and cuenta_id:
            ya_abonado = obtener_total_abonado(factura_id)
            restante = max(0.0, factura.monto - ya_abonado)
            if restante > 0:
                from database.cuentas_repo import debitar_pago_factura
                debitar_pago_factura(
                    cuenta_id, restante, factura_id, fecha,
                    f"Pago factura: {factura.descripcion}",
                )
        return resultado

    def eliminar(self, factura_id: int) -> bool:
        """
        Elimina una factura y revierte los débitos en cuenta de todos sus abonos
        y del pago final si existía, antes de eliminar la fila (el CASCADE borrará
        los abonos_factura automáticamente).
        """
        from database.cuentas_repo import revertir_abono_factura
        from datetime import date as _date

        factura = next((f for f in obtener_todas_facturas() if f.id == factura_id), None)
        abonos = obtener_abonos_por_factura(factura_id)

        # Revertir cada abono que haya debitado una cuenta
        for abono in abonos:
            if abono.cuenta_id:
                try:
                    fecha_rev = abono.fecha if abono.fecha else _date.today()
                    revertir_abono_factura(
                        abono.cuenta_id, abono.monto, fecha_rev,
                        f"Reversa abono (factura eliminada #{factura_id})",
                    )
                except Exception:
                    pass

        # Si la factura estaba pagada y tenía cuenta_id, revertir el pago final
        if factura and factura.estado == "pagada" and factura.cuenta_id:
            ya_abonado = obtener_total_abonado(factura_id)
            restante = max(0.0, factura.monto - ya_abonado)
            if restante > 0:
                try:
                    fecha_rev = factura.fecha_pago if factura.fecha_pago else _date.today()
                    revertir_abono_factura(
                        factura.cuenta_id, restante, fecha_rev,
                        f"Reversa pago final (factura eliminada #{factura_id})",
                    )
                except Exception:
                    pass

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
        cuenta_id: int | None = None,
    ) -> AbonoFactura:
        """Registra un abono parcial, debita la cuenta indicada y auto-cierra si cubre el total."""
        if monto <= 0:
            raise ValueError("El monto del abono debe ser mayor a cero.")
        a = AbonoFactura(factura_id=factura_id, monto=monto, fecha=fecha,
                         notas=notas, cuenta_id=cuenta_id)
        insertar_abono(a)
        if cuenta_id:
            from database.cuentas_repo import debitar_pago_factura
            factura_ref = next(
                (f for f in obtener_todas_facturas() if f.id == factura_id), None
            )
            desc = f"Abono factura: {factura_ref.descripcion}" if factura_ref else "Abono factura"
            debitar_pago_factura(cuenta_id, monto, factura_id, fecha, desc)
        # Auto-cerrar si el total abonado cubre el monto completo
        total = obtener_total_abonado(factura_id)
        factura = next((f for f in obtener_todas_facturas() if f.id == factura_id), None)
        if factura and total >= factura.monto:
            actualizar_estado_factura(factura_id, "pagada", fecha, cuenta_id)
        return a

    def cargar_abonos(self, factura_id: int) -> list[AbonoFactura]:
        return obtener_abonos_por_factura(factura_id)

    def total_abonado(self, factura_id: int) -> float:
        return obtener_total_abonado(factura_id)

    def eliminar_abono(self, abono_id: int) -> bool:
        abono = obtener_abono_por_id(abono_id)
        resultado = eliminar_abono(abono_id)
        if resultado and abono and abono.cuenta_id:
            from database.cuentas_repo import revertir_abono_factura
            fecha_reversa = abono.fecha if abono.fecha else date.today()
            revertir_abono_factura(
                abono.cuenta_id, abono.monto, fecha_reversa,
                f"Reversa abono factura #{abono.factura_id}",
            )
        return resultado
