"""
database/schema.py
Creación y migración del esquema SQLite.

Llamar initialize_schema() al arrancar la app, antes de cualquier
operación de lectura/escritura.
"""

import sqlite3
from database.connection import DatabaseConnection


def initialize_schema() -> None:
    """
    Crea las tablas si no existen y aplica migraciones.
    Idempotente — seguro de llamar en cada arranque.
    """
    conn = DatabaseConnection.get()
    _create_ventas(conn)
    _create_gastos_dia(conn)
    _create_prestamos(conn)
    _create_configuracion(conn)
    _create_inventario(conn)
    _create_facturas(conn)
    _create_abonos_factura(conn)
    _create_presupuesto_mensual(conn)
    _seed_configuracion(conn)
    _migrate_ventas(conn)
    _migrate_ventas_numero_factura(conn)
    _migrate_facturas(conn)
    _migrate_gastos_dia(conn)
    _migrate_configuracion(conn)
    _migrate_configuracion_impresora(conn)
    conn.commit()


def _create_ventas(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha         TEXT    NOT NULL,        -- YYYY-MM-DD
            producto      TEXT    NOT NULL,
            costo         REAL    NOT NULL DEFAULT 0,
            precio        REAL    NOT NULL DEFAULT 0,
            metodo_pago   TEXT    NOT NULL DEFAULT 'Efectivo',
            comision      REAL    NOT NULL DEFAULT 0,
            ganancia_neta REAL    NOT NULL DEFAULT 0,
            notas         TEXT             DEFAULT ''
        )
    """)


def _create_gastos_dia(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gastos_dia (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha       TEXT    NOT NULL,
            descripcion TEXT    NOT NULL,
            monto       REAL    NOT NULL DEFAULT 0
        )
    """)


def _create_prestamos(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prestamos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha         TEXT    NOT NULL,        -- YYYY-MM-DD
            producto      TEXT    NOT NULL,
            almacen       TEXT    NOT NULL,
            observaciones TEXT             DEFAULT '',
            estado        TEXT    NOT NULL DEFAULT 'pendiente'
        )
    """)


def _migrate_ventas(conn: sqlite3.Connection) -> None:
    """Agrega columnas nuevas a ventas si no existen (migraciones forward-only)."""
    try:
        conn.execute("ALTER TABLE ventas ADD COLUMN cantidad INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # La columna ya existe
    try:
        conn.execute("ALTER TABLE ventas ADD COLUMN pagos_combinados TEXT DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # La columna ya existe
    try:
        conn.execute("ALTER TABLE ventas ADD COLUMN grupo_venta_id INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # La columna ya existe


def _create_configuracion(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            id                       INTEGER PRIMARY KEY DEFAULT 1,
            arriendo                 REAL    NOT NULL DEFAULT 0,
            sueldo                   REAL    NOT NULL DEFAULT 0,
            servicios                REAL    NOT NULL DEFAULT 0,
            otros_gastos             REAL    NOT NULL DEFAULT 0,
            dias_mes                 INTEGER NOT NULL DEFAULT 30,
            comision_bold            REAL    NOT NULL DEFAULT 0,
            comision_addi            REAL    NOT NULL DEFAULT 0,
            comision_transferencia   REAL    NOT NULL DEFAULT 0
        )
    """)


def _create_inventario(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            serial          TEXT             DEFAULT '',
            producto        TEXT    NOT NULL,
            costo_unitario  REAL    NOT NULL DEFAULT 0,
            cantidad        INTEGER NOT NULL DEFAULT 0,
            codigo_barras   TEXT             DEFAULT ''
        )
    """)


def _create_facturas(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion   TEXT    NOT NULL,
            proveedor     TEXT    NOT NULL DEFAULT '',
            monto         REAL    NOT NULL DEFAULT 0,
            fecha_llegada TEXT    NOT NULL,        -- YYYY-MM-DD
            estado        TEXT    NOT NULL DEFAULT 'pendiente',
            notas         TEXT             DEFAULT ''
        )
    """)


def _create_presupuesto_mensual(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS presupuesto_mensual (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            anio                INTEGER NOT NULL,
            mes                 INTEGER NOT NULL,
            categoria           TEXT    NOT NULL,
            monto_presupuestado REAL    NOT NULL DEFAULT 0,
            UNIQUE(anio, mes, categoria)
        )
    """)


def _create_abonos_factura(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS abonos_factura (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id  INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
            fecha       TEXT    NOT NULL,
            monto       REAL    NOT NULL DEFAULT 0,
            notas       TEXT             DEFAULT ''
        )
    """)


def _migrate_ventas_numero_factura(conn: sqlite3.Connection) -> None:
    """Agrega numero_factura a ventas si no existe."""
    try:
        conn.execute("ALTER TABLE ventas ADD COLUMN numero_factura INTEGER DEFAULT NULL")
    except sqlite3.OperationalError:
        pass  # La columna ya existe


def _migrate_facturas(conn: sqlite3.Connection) -> None:
    """Agrega fecha_vencimiento y fecha_pago a facturas si no existen."""
    try:
        conn.execute(
            "ALTER TABLE facturas ADD COLUMN fecha_vencimiento TEXT DEFAULT NULL"
        )
    except sqlite3.OperationalError:
        pass  # La columna ya existe
    try:
        conn.execute(
            "ALTER TABLE facturas ADD COLUMN fecha_pago TEXT DEFAULT NULL"
        )
    except sqlite3.OperationalError:
        pass  # La columna ya existe


def _migrate_gastos_dia(conn: sqlite3.Connection) -> None:
    """Agrega columna categoria a gastos_dia si no existe."""
    try:
        conn.execute(
            "ALTER TABLE gastos_dia ADD COLUMN categoria TEXT NOT NULL DEFAULT 'Otro'"
        )
    except sqlite3.OperationalError:
        pass  # La columna ya existe


def _migrate_configuracion(conn: sqlite3.Connection) -> None:
    """Agrega clave_inventario a configuracion si no existe."""
    try:
        conn.execute(
            "ALTER TABLE configuracion ADD COLUMN clave_inventario TEXT DEFAULT 'YJB2026_*'"
        )
    except sqlite3.OperationalError:
        pass  # La columna ya existe


def _migrate_configuracion_impresora(conn: sqlite3.Connection) -> None:
    """Agrega nombre_impresora a configuracion si no existe."""
    try:
        conn.execute(
            "ALTER TABLE configuracion ADD COLUMN nombre_impresora TEXT DEFAULT ''"
        )
    except sqlite3.OperationalError:
        pass  # La columna ya existe


def _seed_configuracion(conn: sqlite3.Connection) -> None:
    """Inserta la fila única de configuración si no existe todavía."""
    exists = conn.execute(
        "SELECT 1 FROM configuracion WHERE id = 1"
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO configuracion (id) VALUES (1)"
        )


def resetear_base_datos() -> None:
    """
    Borra TODOS los datos de usuario de la base de datos y restablece los
    contadores de autoincremento.

    Conserva la estructura de tablas (no hace DROP). Vuelve a insertar la
    fila de configuración con valores en cero.

    Esta operación es IRREVERSIBLE — llamar solo tras confirmación explícita
    del usuario.
    """
    conn = DatabaseConnection.get()
    # Desactivar FK temporalmente para borrar en cualquier orden
    conn.execute("PRAGMA foreign_keys=OFF;")
    for tabla in ("abonos_factura", "facturas", "ventas",
                  "gastos_dia", "prestamos", "inventario",
                  "presupuesto_mensual", "configuracion"):
        conn.execute(f"DELETE FROM {tabla}")
    # Resetear contadores AUTOINCREMENT
    conn.execute(
        "DELETE FROM sqlite_sequence WHERE name IN "
        "('abonos_factura','facturas','ventas',"
        "'gastos_dia','prestamos','inventario')"
    )
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.commit()
    # Re-seed configuración con defaults
    _seed_configuracion(conn)
    conn.commit()
