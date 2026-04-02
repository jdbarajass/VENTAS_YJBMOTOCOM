"""
Gestor de base de datos SQLite para el sistema de rentabilidad.
Maneja todas las operaciones de persistencia de datos.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple
from contextlib import contextmanager

from .models import Venta, Configuracion, ResumenDiario, ResumenMensual


class DatabaseManager:
    """
    Gestor de base de datos SQLite.
    Implementa el patrón Singleton para asegurar una única conexión.
    """

    _instance = None

    def __new__(cls, db_path: Path = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Path = None):
        if self._initialized:
            return

        if db_path is None:
            from config import DATABASE_PATH
            db_path = DATABASE_PATH

        self.db_path = db_path
        self._initialized = True
        self._crear_tablas()
        self._inicializar_configuracion()

    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones a la base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _crear_tablas(self):
        """Crea las tablas necesarias si no existen."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tabla de ventas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ventas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATE NOT NULL,
                    producto TEXT NOT NULL,
                    costo REAL NOT NULL,
                    precio_venta REAL NOT NULL,
                    metodo_pago TEXT NOT NULL,
                    comision REAL DEFAULT 0,
                    ganancia_bruta REAL,
                    ganancia_neta REAL,
                    notas TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Tabla de configuración
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configuracion (
                    id INTEGER PRIMARY KEY,
                    arriendo REAL DEFAULT 3000000,
                    sueldo REAL DEFAULT 2000000,
                    servicios REAL DEFAULT 300000,
                    comision_bold REAL DEFAULT 5.11,
                    dias_mes INTEGER DEFAULT 30
                )
            """)

            # Índice para búsquedas por fecha
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas(fecha)
            """)

    def _inicializar_configuracion(self):
        """Inicializa la configuración por defecto si no existe."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM configuracion")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO configuracion (id, arriendo, sueldo, servicios, comision_bold, dias_mes)
                    VALUES (1, 3000000, 2000000, 300000, 5.11, 30)
                """)

    # =========================================================================
    # OPERACIONES DE VENTAS
    # =========================================================================

    def guardar_venta(self, venta: Venta) -> int:
        """
        Guarda una nueva venta en la base de datos.

        Args:
            venta: Objeto Venta a guardar

        Returns:
            ID de la venta guardada
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ventas (fecha, producto, costo, precio_venta, metodo_pago,
                                   comision, ganancia_bruta, ganancia_neta, notas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                venta.fecha.isoformat(),
                venta.producto,
                venta.costo,
                venta.precio_venta,
                venta.metodo_pago,
                venta.comision,
                venta.ganancia_bruta,
                venta.ganancia_neta,
                venta.notas
            ))
            return cursor.lastrowid

    def actualizar_venta(self, venta: Venta) -> bool:
        """
        Actualiza una venta existente.

        Args:
            venta: Objeto Venta con los datos actualizados

        Returns:
            True si se actualizó correctamente
        """
        if venta.id is None:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE ventas
                SET fecha = ?, producto = ?, costo = ?, precio_venta = ?,
                    metodo_pago = ?, comision = ?, ganancia_bruta = ?,
                    ganancia_neta = ?, notas = ?
                WHERE id = ?
            """, (
                venta.fecha.isoformat(),
                venta.producto,
                venta.costo,
                venta.precio_venta,
                venta.metodo_pago,
                venta.comision,
                venta.ganancia_bruta,
                venta.ganancia_neta,
                venta.notas,
                venta.id
            ))
            return cursor.rowcount > 0

    def eliminar_venta(self, venta_id: int) -> bool:
        """
        Elimina una venta por su ID.

        Args:
            venta_id: ID de la venta a eliminar

        Returns:
            True si se eliminó correctamente
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
            return cursor.rowcount > 0

    def obtener_venta(self, venta_id: int) -> Optional[Venta]:
        """Obtiene una venta por su ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ventas WHERE id = ?", (venta_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_venta(row)
            return None

    def obtener_ventas_por_fecha(self, fecha: date) -> List[Venta]:
        """
        Obtiene todas las ventas de una fecha específica.

        Args:
            fecha: Fecha de las ventas a buscar

        Returns:
            Lista de ventas del día
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ventas
                WHERE fecha = ?
                ORDER BY created_at DESC
            """, (fecha.isoformat(),))
            return [self._row_to_venta(row) for row in cursor.fetchall()]

    def obtener_ventas_por_mes(self, anio: int, mes: int) -> List[Venta]:
        """
        Obtiene todas las ventas de un mes específico.

        Args:
            anio: Año (ej: 2026)
            mes: Mes (1-12)

        Returns:
            Lista de ventas del mes
        """
        fecha_inicio = f"{anio}-{mes:02d}-01"
        if mes == 12:
            fecha_fin = f"{anio + 1}-01-01"
        else:
            fecha_fin = f"{anio}-{mes + 1:02d}-01"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ventas
                WHERE fecha >= ? AND fecha < ?
                ORDER BY fecha DESC, created_at DESC
            """, (fecha_inicio, fecha_fin))
            return [self._row_to_venta(row) for row in cursor.fetchall()]

    def obtener_meses_con_ventas(self) -> List[Tuple[int, int]]:
        """
        Obtiene lista de meses que tienen ventas registradas.

        Returns:
            Lista de tuplas (año, mes) ordenadas descendentemente
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT
                    CAST(strftime('%Y', fecha) AS INTEGER) as anio,
                    CAST(strftime('%m', fecha) AS INTEGER) as mes
                FROM ventas
                ORDER BY anio DESC, mes DESC
            """)
            return [(row['anio'], row['mes']) for row in cursor.fetchall()]

    def _row_to_venta(self, row: sqlite3.Row) -> Venta:
        """Convierte una fila de la base de datos a objeto Venta."""
        return Venta(
            id=row['id'],
            fecha=date.fromisoformat(row['fecha']),
            producto=row['producto'],
            costo=row['costo'],
            precio_venta=row['precio_venta'],
            metodo_pago=row['metodo_pago'],
            comision=row['comision'],
            ganancia_bruta=row['ganancia_bruta'],
            ganancia_neta=row['ganancia_neta'],
            notas=row['notas'] or "",
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None
        )

    # =========================================================================
    # OPERACIONES DE RESÚMENES
    # =========================================================================

    def obtener_resumen_diario(self, fecha: date, gasto_diario: float) -> ResumenDiario:
        """
        Calcula el resumen de ventas de un día.

        Args:
            fecha: Fecha del resumen
            gasto_diario: Gasto operativo diario a considerar

        Returns:
            Objeto ResumenDiario con las métricas del día
        """
        ventas = self.obtener_ventas_por_fecha(fecha)

        resumen = ResumenDiario(
            fecha=fecha,
            gasto_operativo=gasto_diario,
            num_ventas=len(ventas)
        )

        for venta in ventas:
            resumen.total_ventas += venta.precio_venta
            resumen.total_costos += venta.costo
            resumen.ganancia_bruta += venta.ganancia_bruta
            resumen.total_comisiones += venta.comision

            # Acumular por método de pago
            if venta.metodo_pago == "Efectivo":
                resumen.ventas_efectivo += venta.precio_venta
            elif venta.metodo_pago == "Bold":
                resumen.ventas_bold += venta.precio_venta
            elif venta.metodo_pago == "Transferencia":
                resumen.ventas_transferencia += venta.precio_venta

        # Utilidad real = Ganancia bruta - Comisiones - Gasto operativo
        resumen.utilidad_real = (
            resumen.ganancia_bruta - resumen.total_comisiones - resumen.gasto_operativo
        )

        return resumen

    def obtener_resumen_mensual(self, anio: int, mes: int, gasto_diario: float) -> ResumenMensual:
        """
        Calcula el resumen de ventas de un mes.

        Args:
            anio: Año del resumen
            mes: Mes del resumen (1-12)
            gasto_diario: Gasto operativo diario

        Returns:
            Objeto ResumenMensual con las métricas del mes
        """
        ventas = self.obtener_ventas_por_mes(anio, mes)

        resumen = ResumenMensual(
            anio=anio,
            mes=mes,
            num_ventas=len(ventas)
        )

        # Agrupar ventas por día para calcular días positivos/negativos
        ventas_por_dia = {}
        for venta in ventas:
            if venta.fecha not in ventas_por_dia:
                ventas_por_dia[venta.fecha] = []
            ventas_por_dia[venta.fecha].append(venta)

            # Acumular totales
            resumen.total_ventas += venta.precio_venta
            resumen.total_costos += venta.costo
            resumen.ganancia_bruta += venta.ganancia_bruta
            resumen.total_comisiones += venta.comision

        # Calcular utilidad por día y determinar días positivos/negativos
        dias_con_ventas = len(ventas_por_dia)
        resumen.total_gastos_operativos = gasto_diario * dias_con_ventas

        for fecha_dia, ventas_dia in ventas_por_dia.items():
            ganancia_dia = sum(v.ganancia_bruta for v in ventas_dia)
            comision_dia = sum(v.comision for v in ventas_dia)
            utilidad_dia = ganancia_dia - comision_dia - gasto_diario

            if utilidad_dia >= 0:
                resumen.dias_positivos += 1
            else:
                resumen.dias_negativos += 1

            # Mejor y peor día
            if resumen.mejor_dia is None or utilidad_dia > resumen.mejor_dia_utilidad:
                resumen.mejor_dia = fecha_dia
                resumen.mejor_dia_utilidad = utilidad_dia

            if resumen.peor_dia is None or utilidad_dia < resumen.peor_dia_utilidad:
                resumen.peor_dia = fecha_dia
                resumen.peor_dia_utilidad = utilidad_dia

        # Utilidad real del mes
        resumen.utilidad_real = (
            resumen.ganancia_bruta - resumen.total_comisiones - resumen.total_gastos_operativos
        )

        return resumen

    def obtener_resumen_diario_por_mes(self, anio: int, mes: int, gasto_diario: float) -> List[ResumenDiario]:
        """
        Obtiene resúmenes diarios de todos los días con ventas en un mes.

        Args:
            anio: Año
            mes: Mes (1-12)
            gasto_diario: Gasto operativo diario

        Returns:
            Lista de ResumenDiario ordenada por fecha
        """
        ventas = self.obtener_ventas_por_mes(anio, mes)

        # Agrupar por fecha
        ventas_por_dia = {}
        for venta in ventas:
            if venta.fecha not in ventas_por_dia:
                ventas_por_dia[venta.fecha] = []
            ventas_por_dia[venta.fecha].append(venta)

        # Crear resúmenes
        resumenes = []
        for fecha_dia in sorted(ventas_por_dia.keys()):
            resumen = self.obtener_resumen_diario(fecha_dia, gasto_diario)
            resumenes.append(resumen)

        return resumenes

    # =========================================================================
    # OPERACIONES DE CONFIGURACIÓN
    # =========================================================================

    def obtener_configuracion(self) -> Configuracion:
        """Obtiene la configuración actual del sistema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM configuracion WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return Configuracion(
                    id=row['id'],
                    arriendo=row['arriendo'],
                    sueldo=row['sueldo'],
                    servicios=row['servicios'],
                    comision_bold=row['comision_bold'],
                    dias_mes=row['dias_mes']
                )
            return Configuracion()

    def guardar_configuracion(self, config: Configuracion) -> bool:
        """
        Guarda o actualiza la configuración del sistema.

        Args:
            config: Objeto Configuracion con los nuevos valores

        Returns:
            True si se guardó correctamente
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE configuracion
                SET arriendo = ?, sueldo = ?, servicios = ?,
                    comision_bold = ?, dias_mes = ?
                WHERE id = 1
            """, (
                config.arriendo,
                config.sueldo,
                config.servicios,
                config.comision_bold,
                config.dias_mes
            ))
            return cursor.rowcount > 0
