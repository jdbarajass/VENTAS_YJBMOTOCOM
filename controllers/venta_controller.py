"""
controllers/venta_controller.py
Coordina el formulario de registro con los servicios y la base de datos.
La UI nunca toca la BD ni el calculator directamente.
"""

from datetime import date

from models.venta import Venta
from models.configuracion import Configuracion
from services.calculator import (
    calcular_comision,
    calcular_ganancia_bruta,
    calcular_ganancia_neta,
    completar_venta,
)
from database.ventas_repo import insertar_venta, actualizar_venta, eliminar_venta as _eliminar_venta
from database.config_repo import obtener_configuracion


class VentaController:
    """Casos de uso relacionados con el registro y edición de ventas."""

    # ------------------------------------------------------------------
    # Configuración
    # ------------------------------------------------------------------

    def get_configuracion(self) -> Configuracion:
        """Carga la configuración activa desde la BD."""
        return obtener_configuracion()

    # ------------------------------------------------------------------
    # Preview en tiempo real (sin persistir)
    # ------------------------------------------------------------------

    def calcular_preview(
        self,
        costo: float,
        precio: float,
        metodo_pago: str,
        cantidad: int = 1,
    ) -> dict:
        """
        Retorna los valores calculados para mostrar en tiempo real en el form.
        No toca la base de datos. Los montos se multiplican por cantidad.
        """
        cfg = self.get_configuracion()
        porcentaje = cfg.porcentaje_para(metodo_pago)
        comision_unit = calcular_comision(precio, metodo_pago, cfg)
        ganancia_bruta = calcular_ganancia_bruta(precio, costo) * cantidad
        ganancia_neta = calcular_ganancia_neta(precio, costo, comision_unit) * cantidad

        return {
            "ganancia_bruta": ganancia_bruta,
            "comision": comision_unit * cantidad,
            "porcentaje": porcentaje,
            "ganancia_neta": ganancia_neta,
        }

    # ------------------------------------------------------------------
    # Guardar nueva venta
    # ------------------------------------------------------------------

    def guardar_nueva_venta(
        self,
        fecha: date,
        producto: str,
        costo: float,
        precio: float,
        metodo_pago: str,
        notas: str,
        cantidad: int = 1,
    ) -> Venta:
        """
        Valida, calcula comisión/ganancia y persiste una nueva venta.
        Retorna el objeto Venta con su id asignado.
        Lanza ValueError si los datos no son válidos.
        """
        self._validar(producto, costo, precio)

        cfg = self.get_configuracion()
        venta = Venta(
            producto=producto.strip(),
            costo=costo,
            precio=precio,
            metodo_pago=metodo_pago,
            fecha=fecha,
            cantidad=cantidad,
            notas=notas.strip(),
        )
        completar_venta(venta, cfg)
        insertar_venta(venta)

        # Descontar del inventario (silencioso si el producto no está en inventario)
        try:
            from database.inventario_repo import decrementar_cantidad
            decrementar_cantidad(venta.producto, venta.cantidad)
        except Exception:
            pass

        return venta

    # ------------------------------------------------------------------
    # Actualizar venta existente (CRUD — edición)
    # ------------------------------------------------------------------

    def actualizar_venta_existente(self, venta: Venta) -> bool:
        """
        Recalcula comisión y ganancia neta con la config actual y persiste.
        Retorna True si se actualizó correctamente.
        """
        self._validar(venta.producto, venta.costo, venta.precio)
        cfg = self.get_configuracion()
        completar_venta(venta, cfg)
        return actualizar_venta(venta)

    # ------------------------------------------------------------------
    # Eliminar venta
    # ------------------------------------------------------------------

    def eliminar_venta(self, venta_id: int) -> bool:
        """Elimina una venta por su id. Retorna True si se eliminó."""
        return _eliminar_venta(venta_id)

    # ------------------------------------------------------------------
    # Validación interna
    # ------------------------------------------------------------------

    @staticmethod
    def _validar(producto: str, costo: float, precio: float) -> None:
        if not producto or not producto.strip():
            raise ValueError("El nombre del producto es obligatorio.")
        if costo < 0:
            raise ValueError("El costo no puede ser negativo.")
        if precio <= 0:
            raise ValueError("El precio de venta debe ser mayor a cero.")
