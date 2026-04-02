"""
Calculadora de rentabilidad para el sistema de control financiero.
Contiene toda la lógica de cálculos de ganancias, comisiones y utilidades.
"""

from datetime import date
from typing import List, Dict, Any

from database.models import Venta, ResumenDiario, ResumenMensual, Configuracion
from database.db_manager import DatabaseManager


class RentabilityCalculator:
    """
    Clase que maneja todos los cálculos de rentabilidad del negocio.
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        Inicializa el calculador.

        Args:
            db_manager: Instancia del gestor de base de datos
        """
        self.db = db_manager or DatabaseManager()
        self._config = None

    @property
    def config(self) -> Configuracion:
        """Obtiene la configuración actual (con caché)."""
        if self._config is None:
            self._config = self.db.obtener_configuracion()
        return self._config

    def refrescar_configuracion(self):
        """Refresca la configuración desde la base de datos."""
        self._config = self.db.obtener_configuracion()

    def calcular_comision(self, precio_venta: float, metodo_pago: str) -> float:
        """
        Calcula la comisión basada en el método de pago.

        Args:
            precio_venta: Precio de venta del producto
            metodo_pago: Método de pago utilizado

        Returns:
            Monto de la comisión
        """
        if metodo_pago == "Bold":
            return precio_venta * (self.config.comision_bold / 100)
        return 0.0

    def procesar_venta(self, producto: str, costo: float, precio_venta: float,
                       metodo_pago: str, notas: str = "",
                       fecha: date = None) -> Venta:
        """
        Procesa una nueva venta calculando todos sus valores.

        Args:
            producto: Nombre del producto vendido
            costo: Costo del producto
            precio_venta: Precio de venta
            metodo_pago: Método de pago (Efectivo, Bold, Transferencia)
            notas: Notas opcionales
            fecha: Fecha de la venta (por defecto hoy)

        Returns:
            Objeto Venta con todos los cálculos realizados
        """
        if fecha is None:
            fecha = date.today()

        venta = Venta(
            fecha=fecha,
            producto=producto,
            costo=costo,
            precio_venta=precio_venta,
            metodo_pago=metodo_pago,
            notas=notas
        )

        # Calcular ganancias con la comisión correspondiente
        porcentaje_comision = self.config.comision_bold if metodo_pago == "Bold" else 0.0
        venta.calcular_ganancias(porcentaje_comision)

        return venta

    def registrar_venta(self, producto: str, costo: float, precio_venta: float,
                        metodo_pago: str, notas: str = "",
                        fecha: date = None) -> Venta:
        """
        Registra una nueva venta en la base de datos.

        Args:
            producto: Nombre del producto
            costo: Costo del producto
            precio_venta: Precio de venta
            metodo_pago: Método de pago
            notas: Notas opcionales
            fecha: Fecha de la venta

        Returns:
            Venta registrada con su ID asignado
        """
        venta = self.procesar_venta(producto, costo, precio_venta, metodo_pago, notas, fecha)
        venta.id = self.db.guardar_venta(venta)
        return venta

    def obtener_resumen_hoy(self) -> ResumenDiario:
        """
        Obtiene el resumen de ventas del día actual.

        Returns:
            ResumenDiario con las métricas del día
        """
        return self.db.obtener_resumen_diario(date.today(), self.config.gasto_diario)

    def obtener_resumen_fecha(self, fecha: date) -> ResumenDiario:
        """
        Obtiene el resumen de ventas de una fecha específica.

        Args:
            fecha: Fecha a consultar

        Returns:
            ResumenDiario con las métricas del día
        """
        return self.db.obtener_resumen_diario(fecha, self.config.gasto_diario)

    def obtener_resumen_mes(self, anio: int, mes: int) -> ResumenMensual:
        """
        Obtiene el resumen de un mes específico.

        Args:
            anio: Año
            mes: Mes (1-12)

        Returns:
            ResumenMensual con las métricas del mes
        """
        return self.db.obtener_resumen_mensual(anio, mes, self.config.gasto_diario)

    def obtener_ventas_hoy(self) -> List[Venta]:
        """
        Obtiene todas las ventas del día actual.

        Returns:
            Lista de ventas del día
        """
        return self.db.obtener_ventas_por_fecha(date.today())

    def obtener_ventas_fecha(self, fecha: date) -> List[Venta]:
        """
        Obtiene todas las ventas de una fecha específica.

        Args:
            fecha: Fecha a consultar

        Returns:
            Lista de ventas
        """
        return self.db.obtener_ventas_por_fecha(fecha)

    def obtener_ventas_mes(self, anio: int, mes: int) -> List[Venta]:
        """
        Obtiene todas las ventas de un mes.

        Args:
            anio: Año
            mes: Mes (1-12)

        Returns:
            Lista de ventas del mes
        """
        return self.db.obtener_ventas_por_mes(anio, mes)

    def eliminar_venta(self, venta_id: int) -> bool:
        """
        Elimina una venta por su ID.

        Args:
            venta_id: ID de la venta a eliminar

        Returns:
            True si se eliminó correctamente
        """
        return self.db.eliminar_venta(venta_id)

    def calcular_punto_equilibrio_diario(self) -> Dict[str, Any]:
        """
        Calcula información sobre el punto de equilibrio diario.

        Returns:
            Diccionario con información del punto de equilibrio
        """
        gasto_diario = self.config.gasto_diario
        resumen_hoy = self.obtener_resumen_hoy()

        return {
            "gasto_diario": gasto_diario,
            "ganancia_actual": resumen_hoy.ganancia_bruta - resumen_hoy.total_comisiones,
            "utilidad_actual": resumen_hoy.utilidad_real,
            "meta_cubierta": resumen_hoy.meta_cubierta,
            "faltante": resumen_hoy.faltante_meta,
            "porcentaje_meta": (
                ((resumen_hoy.ganancia_bruta - resumen_hoy.total_comisiones) / gasto_diario * 100)
                if gasto_diario > 0 else 0
            )
        }

    def obtener_meses_disponibles(self) -> List[tuple]:
        """
        Obtiene lista de meses que tienen ventas registradas.

        Returns:
            Lista de tuplas (año, mes, nombre_mes)
        """
        meses = self.db.obtener_meses_con_ventas()
        nombres_meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]

        return [
            (anio, mes, f"{nombres_meses[mes - 1]} {anio}")
            for anio, mes in meses
        ]

    def obtener_detalle_diario_mes(self, anio: int, mes: int) -> List[ResumenDiario]:
        """
        Obtiene el detalle diario de un mes.

        Args:
            anio: Año
            mes: Mes (1-12)

        Returns:
            Lista de ResumenDiario por cada día con ventas
        """
        return self.db.obtener_resumen_diario_por_mes(anio, mes, self.config.gasto_diario)

    def obtener_datos_grafica_mes(self, anio: int, mes: int) -> Dict[str, List]:
        """
        Obtiene datos formateados para graficar la utilidad diaria del mes.

        Args:
            anio: Año
            mes: Mes (1-12)

        Returns:
            Diccionario con 'fechas' y 'utilidades' para graficar
        """
        resumenes = self.obtener_detalle_diario_mes(anio, mes)

        return {
            "fechas": [r.fecha.strftime("%d") for r in resumenes],
            "utilidades": [r.utilidad_real for r in resumenes],
            "fechas_completas": [r.fecha for r in resumenes]
        }
