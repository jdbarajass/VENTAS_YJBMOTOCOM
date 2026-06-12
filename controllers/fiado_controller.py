"""
controllers/fiado_controller.py
Lógica de negocio para el módulo de clientes deudores (fiado).
"""

from datetime import date
from models.fiado import Fiado, AbonoFiado
from database.fiado_repo import (
    insertar_fiado, obtener_todos_fiados, obtener_fiados_pendientes,
    actualizar_fiado, marcar_pagado_fiado, eliminar_fiado,
    insertar_abono_fiado, obtener_abonos_fiado,
    total_abonado_fiado, eliminar_abono_fiado,
)


class FiadoController:

    def cargar_todos(self) -> list[Fiado]:
        return obtener_todos_fiados()

    def cargar_pendientes(self) -> list[Fiado]:
        return obtener_fiados_pendientes()

    def registrar(
        self,
        cliente_nombre: str,
        descripcion: str,
        monto_total: float,
        fecha: date,
        cliente_cedula: str = "",
        cliente_tel: str = "",
        notas: str = "",
    ) -> int:
        if not cliente_nombre.strip():
            raise ValueError("El nombre del cliente es obligatorio.")
        if not descripcion.strip():
            raise ValueError("La descripción de la deuda es obligatoria.")
        if monto_total <= 0:
            raise ValueError("El monto debe ser mayor a cero.")
        f = Fiado(
            cliente_nombre=cliente_nombre.strip(),
            descripcion=descripcion.strip(),
            monto_total=monto_total,
            fecha=fecha,
            cliente_cedula=cliente_cedula.strip(),
            cliente_tel=cliente_tel.strip(),
            notas=notas.strip(),
        )
        return insertar_fiado(f)

    def editar(self, f: Fiado) -> bool:
        if not f.cliente_nombre.strip():
            raise ValueError("El nombre del cliente es obligatorio.")
        if f.monto_total <= 0:
            raise ValueError("El monto debe ser mayor a cero.")
        return actualizar_fiado(f)

    def marcar_pagado(self, fiado_id: int) -> bool:
        return marcar_pagado_fiado(fiado_id)

    def eliminar(self, fiado_id: int) -> bool:
        return eliminar_fiado(fiado_id)

    # ── Abonos ────────────────────────────────────────────────────────────────

    def cargar_abonos(self, fiado_id: int) -> list[AbonoFiado]:
        return obtener_abonos_fiado(fiado_id)

    def total_abonado(self, fiado_id: int) -> float:
        return total_abonado_fiado(fiado_id)

    def registrar_abono(
        self, fiado_id: int, monto: float, fecha: date, notas: str = ""
    ) -> int:
        if monto <= 0:
            raise ValueError("El monto del abono debe ser mayor a cero.")
        a = AbonoFiado(fiado_id=fiado_id, monto=monto, fecha=fecha, notas=notas)
        abono_id = insertar_abono_fiado(a)
        # Marcar como pagado automáticamente si el saldo queda en cero
        from database.fiado_repo import obtener_todos_fiados
        fiados = obtener_todos_fiados()
        fiado = next((x for x in fiados if x.id == fiado_id), None)
        if fiado and fiado.estado == "pendiente":
            total = total_abonado_fiado(fiado_id)
            if total >= fiado.monto_total:
                marcar_pagado_fiado(fiado_id)
        return abono_id

    def eliminar_abono(self, abono_id: int) -> bool:
        return eliminar_abono_fiado(abono_id)
