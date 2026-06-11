"""
controllers/venta_controller.py
Coordina el formulario de registro con los servicios y la base de datos.
La UI nunca toca la BD ni el calculator directamente.
"""

from datetime import date, datetime

from models.venta import Venta
from models.configuracion import Configuracion
from services.calculator import (
    calcular_comision,
    calcular_ganancia_bruta,
    calcular_ganancia_neta,
    calcular_comision_combinada,
    completar_venta,
)
from database.ventas_repo import (
    insertar_venta,
    actualizar_venta,
    eliminar_venta as _eliminar_venta,
    siguiente_numero_factura,
)
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
        pagos_combinados: list | None = None,
    ) -> dict:
        """
        Retorna los valores calculados para mostrar en tiempo real en el form.
        No toca la base de datos. Los montos se multiplican por cantidad.
        Si pagos_combinados está presente, la comisión se calcula por partes.
        """
        cfg = self.get_configuracion()
        ganancia_bruta = calcular_ganancia_bruta(precio, costo) * cantidad

        if pagos_combinados:
            total_comision = calcular_comision_combinada(pagos_combinados, cfg)
            ganancia_neta = round(ganancia_bruta - total_comision, 2)
            return {
                "ganancia_bruta": ganancia_bruta,
                "comision": total_comision,
                "porcentaje": 0.0,
                "ganancia_neta": ganancia_neta,
                "es_combinado": True,
            }

        porcentaje = cfg.porcentaje_para(metodo_pago)
        comision_unit = calcular_comision(precio, metodo_pago, cfg)
        ganancia_neta = calcular_ganancia_neta(precio, costo, comision_unit) * cantidad
        return {
            "ganancia_bruta": ganancia_bruta,
            "comision": comision_unit * cantidad,
            "porcentaje": porcentaje,
            "ganancia_neta": ganancia_neta,
            "es_combinado": False,
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
        pagos_combinados: list | None = None,
    ) -> Venta:
        """
        Valida, calcula comisión/ganancia y persiste una nueva venta.
        Retorna el objeto Venta con su id asignado.
        Lanza ValueError si los datos no son válidos.
        Si pagos_combinados está presente, metodo_pago se ignora y se usa "Combinado".
        """
        self._validar(producto, costo, precio)

        cfg = self.get_configuracion()
        metodo_final = "Combinado" if pagos_combinados else metodo_pago
        nro_factura = siguiente_numero_factura()
        venta = Venta(
            producto=producto.strip(),
            costo=costo,
            precio=precio,
            metodo_pago=metodo_final,
            fecha=fecha,
            cantidad=cantidad,
            notas=notas.strip(),
            pagos_combinados=pagos_combinados,
        )
        venta.numero_factura = nro_factura
        venta.hora = datetime.now().strftime("%H:%M")
        completar_venta(venta, cfg)
        insertar_venta(venta)

        # Descontar del inventario (silencioso si el producto no está en inventario)
        try:
            from database.inventario_repo import decrementar_cantidad
            decrementar_cantidad(venta.producto, venta.cantidad)
        except Exception:
            pass

        # Acreditar a la cuenta correspondiente
        try:
            from database.cuentas_repo import acreditar_venta
            acreditar_venta(venta)
        except Exception:
            pass

        return venta

    # ------------------------------------------------------------------
    # Guardar carrito multi-producto
    # ------------------------------------------------------------------

    def guardar_carrito(
        self,
        fecha: date,
        lineas: list[dict],  # [{producto, costo, precio, cantidad, sku}]
        metodo_pago: str,
        notas: str,
        pagos_combinados: list | None = None,
        vendedor: str = "",
        cliente_nombre: str = "",
        cliente_cedula: str = "",
        cliente_tel: str = "",
        descuento: int = 0,
    ) -> list:
        """
        Guarda un carrito con N productos. Crea N ventas independientes.
        Si N > 1, todas comparten el mismo grupo_venta_id.
        Para pagos combinados, distribuye los montos proporcional al valor de cada producto.
        Retorna la lista de Venta creadas.
        """
        if not lineas:
            raise ValueError("El carrito no tiene productos.")
        for ln in lineas:
            self._validar(ln["producto"], ln["costo"], ln["precio"])

        cfg = self.get_configuracion()
        metodo_final = "Combinado" if pagos_combinados else metodo_pago
        total_carrito = sum(ln["precio"] * ln["cantidad"] for ln in lineas)

        if descuento > total_carrito:
            raise ValueError(
                "El descuento no puede ser mayor al total del carrito."
            )

        from database.ventas_repo import siguiente_grupo_venta_id
        grupo_id = siguiente_grupo_venta_id() if len(lineas) > 1 else None
        nro_factura = siguiente_numero_factura()

        # ── Fase 1: construir todas las Venta sin insertar ──────────────────
        ventas = []
        for i, ln in enumerate(lineas):
            # Distribuir pagos_combinados proporcionalmente
            pagos_linea = None
            if pagos_combinados and total_carrito > 0:
                valor_linea = ln["precio"] * ln["cantidad"]
                proporcion = valor_linea / total_carrito
                if i < len(lineas) - 1:
                    pagos_linea = [
                        {"metodo": p["metodo"],
                         "monto": round(p["monto"] * proporcion)}
                        for p in pagos_combinados
                    ]
                else:
                    # Último producto: usar el saldo restante para evitar redondeos
                    asignados: dict = {}
                    for v in ventas:
                        for pc in (v.pagos_combinados or []):
                            asignados[pc["metodo"]] = (
                                asignados.get(pc["metodo"], 0) + pc["monto"]
                            )
                    pagos_linea = [
                        {"metodo": p["metodo"],
                         "monto": p["monto"] - asignados.get(p["metodo"], 0)}
                        for p in pagos_combinados
                    ]

            venta = Venta(
                producto=ln["producto"].strip(),
                costo=ln["costo"],
                precio=ln["precio"],
                metodo_pago=metodo_final,
                fecha=fecha,
                cantidad=ln["cantidad"],
                notas=notas.strip() if i == 0 else "",
                pagos_combinados=pagos_linea,
                grupo_venta_id=grupo_id,
            )
            venta.numero_factura = nro_factura
            venta.hora = datetime.now().strftime("%H:%M")
            venta.vendedor = vendedor
            venta.sku = ln.get("sku", "")
            if i == 0:
                venta.cliente_nombre = cliente_nombre
                venta.cliente_cedula = cliente_cedula
                venta.cliente_tel = cliente_tel
                venta.descuento = descuento
            completar_venta(venta, cfg)
            ventas.append(venta)

        # ── Fase 2: distribuir descuento en comision y ganancia_neta (proporcional) ──
        # La comisión se recalcula sobre el precio efectivo (ya descontado) porque
        # el terminal cobra comisión sobre lo que el cliente realmente paga.
        if descuento > 0 and total_carrito > 0:
            restante = descuento
            for i, venta in enumerate(ventas):
                valor_linea = venta.precio * venta.cantidad
                if i < len(ventas) - 1:
                    prop = valor_linea / total_carrito
                    ajuste = round(descuento * prop)
                    restante -= ajuste
                else:
                    ajuste = restante

                if ajuste > 0:
                    if venta.pagos_combinados:
                        # Escalar cada pago proporcionalmente al descuento de esta línea
                        pagos_desc = [
                            {"metodo": p["metodo"],
                             "monto": p["monto"] - round(ajuste * p["monto"] / valor_linea)}
                            for p in venta.pagos_combinados
                        ]
                        comision_nueva = calcular_comision_combinada(pagos_desc, cfg)
                    else:
                        precio_neto_unit = max(0.0, venta.precio - ajuste / venta.cantidad)
                        comision_unit = calcular_comision(precio_neto_unit, venta.metodo_pago, cfg)
                        comision_nueva = round(comision_unit * venta.cantidad, 2)

                    diff_comision = venta.comision - comision_nueva
                    venta.comision = comision_nueva
                    # ganancia_neta = (precio - ajuste) × cant - costo × cant - comision_nueva
                    venta.ganancia_neta = round(
                        venta.ganancia_neta - ajuste + diff_comision, 2
                    )

        # ── Fase 3: persistir y post-procesar ────────────────────────────────
        for venta in ventas:
            insertar_venta(venta)

            try:
                from database.inventario_repo import decrementar_cantidad
                decrementar_cantidad(venta.producto, venta.cantidad)
            except Exception:
                pass

            try:
                from database.cuentas_repo import acreditar_venta
                acreditar_venta(venta)
            except Exception:
                pass

        return ventas

    # ------------------------------------------------------------------
    # Actualizar venta existente (CRUD — edicion)
    # ------------------------------------------------------------------

    def actualizar_venta_existente(
        self,
        venta: Venta,
        pagos_combinados: list | None = None,
    ) -> bool:
        """
        Recalcula comisión y ganancia neta con la config actual y persiste.
        Retorna True si se actualizó correctamente.
        """
        self._validar(venta.producto, venta.costo, venta.precio)
        if pagos_combinados is not None:
            venta.pagos_combinados = pagos_combinados
            venta.metodo_pago = "Combinado" if pagos_combinados else venta.metodo_pago
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
