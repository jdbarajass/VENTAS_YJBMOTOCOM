"""
database/schema.py
Creación y migración del esquema SQLite.

Sistema de versiones:
  - La tabla `schema_version` registra qué migraciones se han aplicado.
  - Cada migración es un tuple (versión, descripción, [sqls]).
  - Al arrancar se aplican solo las que falten (forward-only, idempotente).
  - Para agregar una migración futura: añadir un tuple al final de _MIGRACIONES
    e incrementar _VERSION_ACTUAL.

Llamar initialize_schema() al arrancar la app, antes de cualquier
operación de lectura/escritura.
"""

import sqlite3
from utils.logger import log
from database.connection import DatabaseConnection


# ── Versión actual del esquema ────────────────────────────────────────────────
# Incrementar este número cada vez que se añada una migración a _MIGRACIONES.
_VERSION_ACTUAL = 18


# ── Lista de migraciones (forward-only) ───────────────────────────────────────
# Cada entrada: (version: int, descripcion: str, sqls: list[str])
# Los SQLs se ejecutan en orden; si alguno falla se loguea y se omite
# (compatibilidad con columnas que ya existan en BDs antiguas).
_MIGRACIONES = [
    (1, "Agregar cantidad, pagos_combinados y grupo_venta_id a ventas", [
        "ALTER TABLE ventas ADD COLUMN cantidad INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE ventas ADD COLUMN pagos_combinados TEXT DEFAULT NULL",
        "ALTER TABLE ventas ADD COLUMN grupo_venta_id INTEGER DEFAULT NULL",
    ]),
    (2, "Agregar numero_factura a ventas", [
        "ALTER TABLE ventas ADD COLUMN numero_factura INTEGER DEFAULT NULL",
    ]),
    (3, "Agregar fecha_vencimiento y fecha_pago a facturas", [
        "ALTER TABLE facturas ADD COLUMN fecha_vencimiento TEXT DEFAULT NULL",
        "ALTER TABLE facturas ADD COLUMN fecha_pago TEXT DEFAULT NULL",
    ]),
    (4, "Agregar categoria a gastos_dia", [
        "ALTER TABLE gastos_dia ADD COLUMN categoria TEXT NOT NULL DEFAULT 'Otro'",
    ]),
    (5, "Agregar clave_inventario a configuracion", [
        "ALTER TABLE configuracion ADD COLUMN clave_inventario TEXT DEFAULT 'YJB2026_*'",
    ]),
    (6, "Agregar nombre_impresora a configuracion", [
        "ALTER TABLE configuracion ADD COLUMN nombre_impresora TEXT DEFAULT ''",
    ]),
    (7, "Agregar hora a prestamos", [
        "ALTER TABLE prestamos ADD COLUMN hora TEXT NOT NULL DEFAULT ''",
    ]),
    (8, "Agregar fecha_limite a notas", [
        "ALTER TABLE notas ADD COLUMN fecha_limite TEXT DEFAULT NULL",
    ]),
    (9, "Crear tabla log_acciones para auditoría", [
        """CREATE TABLE IF NOT EXISTS log_acciones (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha     TEXT    NOT NULL,
            hora      TEXT    NOT NULL,
            accion    TEXT    NOT NULL,
            detalle   TEXT    DEFAULT '',
            usuario   TEXT    DEFAULT 'Sistema'
        )""",
    ]),
    (10, "Crear tabla usuarios para acceso multi-usuario", [
        """CREATE TABLE IF NOT EXISTS usuarios (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre     TEXT    NOT NULL UNIQUE,
            rol        TEXT    NOT NULL DEFAULT 'vendedor',
            clave_hash TEXT    NOT NULL DEFAULT ''
        )""",
    ]),
    (11, "Agregar modo_oscuro a configuracion", [
        "ALTER TABLE configuracion ADD COLUMN modo_oscuro INTEGER NOT NULL DEFAULT 0",
    ]),
    (12, "Agregar timeout_minutos a configuracion", [
        "ALTER TABLE configuracion ADD COLUMN timeout_minutos INTEGER NOT NULL DEFAULT 10",
    ]),
    (13, "Agregar hora a ventas para análisis de horas pico", [
        "ALTER TABLE ventas ADD COLUMN hora TEXT NOT NULL DEFAULT ''",
    ]),
    (14, "Crear sistema de Cuentas (cuentas, movimientos, cierres)", [
        """CREATE TABLE IF NOT EXISTS cuentas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre         TEXT    NOT NULL UNIQUE,
            metodo_pago    TEXT    NOT NULL DEFAULT '',
            balance_actual REAL    NOT NULL DEFAULT 0,
            color          TEXT    NOT NULL DEFAULT '#3B82F6',
            activa         INTEGER NOT NULL DEFAULT 1,
            orden          INTEGER NOT NULL DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS cuentas_movimientos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id   INTEGER NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
            fecha       TEXT    NOT NULL,
            tipo        TEXT    NOT NULL,
            monto       REAL    NOT NULL DEFAULT 0,
            descripcion TEXT             DEFAULT '',
            venta_id    INTEGER          DEFAULT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS cuentas_cierres (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            anio         INTEGER NOT NULL,
            mes          INTEGER NOT NULL,
            datos_json   TEXT    NOT NULL DEFAULT '[]',
            notas        TEXT             DEFAULT '',
            fecha_cierre TEXT    NOT NULL,
            UNIQUE(anio, mes)
        )""",
        # Cuentas por defecto — una por cada medio de pago del sistema
        "INSERT OR IGNORE INTO cuentas (nombre, metodo_pago, color, orden) VALUES ('Efectivo',         'Efectivo',               '#22C55E', 1)",
        "INSERT OR IGNORE INTO cuentas (nombre, metodo_pago, color, orden) VALUES ('Nequi',            'Transferencia NEQUI',    '#8B5CF6', 2)",
        "INSERT OR IGNORE INTO cuentas (nombre, metodo_pago, color, orden) VALUES ('QR / Bancolombia', 'Transferencia QR',       '#F59E0B', 3)",
        "INSERT OR IGNORE INTO cuentas (nombre, metodo_pago, color, orden) VALUES ('NU',               'Transferencia NU',       '#EF4444', 4)",
        "INSERT OR IGNORE INTO cuentas (nombre, metodo_pago, color, orden) VALUES ('Daviplata',        'Transferencia DAVIPLATA','#F97316', 5)",
        "INSERT OR IGNORE INTO cuentas (nombre, metodo_pago, color, orden) VALUES ('Addi',             'Addi',                   '#06B6D4', 6)",
    ]),
    (15, "Agregar cuenta_pago a gastos_dia", [
        "ALTER TABLE gastos_dia ADD COLUMN cuenta_pago TEXT NOT NULL DEFAULT 'Efectivo'",
    ]),
    (16, "Comprobante overhaul: vendedor, datos cliente, descuento y sku en ventas", [
        "ALTER TABLE ventas ADD COLUMN vendedor TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE ventas ADD COLUMN cliente_nombre TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE ventas ADD COLUMN cliente_cedula TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE ventas ADD COLUMN cliente_tel TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE ventas ADD COLUMN descuento INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE ventas ADD COLUMN sku TEXT NOT NULL DEFAULT ''",
    ]),
    (17, "Crear módulo de clientes deudores (fiado y abonos_fiado)", [
        """CREATE TABLE IF NOT EXISTS fiado (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_nombre  TEXT    NOT NULL,
            cliente_cedula  TEXT    NOT NULL DEFAULT '',
            cliente_tel     TEXT    NOT NULL DEFAULT '',
            descripcion     TEXT    NOT NULL,
            monto_total     REAL    NOT NULL DEFAULT 0,
            fecha           TEXT    NOT NULL,
            estado          TEXT    NOT NULL DEFAULT 'pendiente',
            notas           TEXT    NOT NULL DEFAULT ''
        )""",
        """CREATE TABLE IF NOT EXISTS abonos_fiado (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            fiado_id  INTEGER NOT NULL REFERENCES fiado(id) ON DELETE CASCADE,
            monto     REAL    NOT NULL DEFAULT 0,
            fecha     TEXT    NOT NULL,
            notas     TEXT    NOT NULL DEFAULT ''
        )""",
    ]),
    (18, "Agregar stock_minimo a inventario para alertas de reabastecimiento", [
        "ALTER TABLE inventario ADD COLUMN stock_minimo INTEGER NOT NULL DEFAULT 0",
    ]),
]


# ── API pública ───────────────────────────────────────────────────────────────

def initialize_schema() -> None:
    """
    Crea las tablas base si no existen y aplica todas las migraciones pendientes.
    Idempotente — seguro de llamar en cada arranque.
    """
    conn = DatabaseConnection.get()
    _create_tables(conn)
    _seed_configuracion(conn)
    _setup_version_table(conn)
    _aplicar_migraciones_pendientes(conn)
    _reparar_migraciones_fallidas(conn)
    conn.commit()
    log.info("Schema inicializado correctamente (versión %d)", _VERSION_ACTUAL)


# ── Creación de tablas base ───────────────────────────────────────────────────

def _create_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha         TEXT    NOT NULL,
            producto      TEXT    NOT NULL,
            costo         REAL    NOT NULL DEFAULT 0,
            precio        REAL    NOT NULL DEFAULT 0,
            metodo_pago   TEXT    NOT NULL DEFAULT 'Efectivo',
            comision      REAL    NOT NULL DEFAULT 0,
            ganancia_neta REAL    NOT NULL DEFAULT 0,
            notas         TEXT             DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gastos_dia (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha       TEXT    NOT NULL,
            descripcion TEXT    NOT NULL,
            monto       REAL    NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prestamos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha         TEXT    NOT NULL,
            producto      TEXT    NOT NULL,
            almacen       TEXT    NOT NULL,
            observaciones TEXT             DEFAULT '',
            estado        TEXT    NOT NULL DEFAULT 'pendiente'
        )
    """)
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            descripcion   TEXT    NOT NULL,
            proveedor     TEXT    NOT NULL DEFAULT '',
            monto         REAL    NOT NULL DEFAULT 0,
            fecha_llegada TEXT    NOT NULL,
            estado        TEXT    NOT NULL DEFAULT 'pendiente',
            notas         TEXT             DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS abonos_factura (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id  INTEGER NOT NULL REFERENCES facturas(id) ON DELETE CASCADE,
            fecha       TEXT    NOT NULL,
            monto       REAL    NOT NULL DEFAULT 0,
            notas       TEXT             DEFAULT ''
        )
    """)
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS notas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            texto           TEXT    NOT NULL,
            tipo            TEXT    NOT NULL DEFAULT 'tarea',
            completado      INTEGER NOT NULL DEFAULT 0,
            fecha_creacion  TEXT    NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS log_acciones (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha     TEXT    NOT NULL,
            hora      TEXT    NOT NULL,
            accion    TEXT    NOT NULL,
            detalle   TEXT    DEFAULT '',
            usuario   TEXT    DEFAULT 'Sistema'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre     TEXT    NOT NULL UNIQUE,
            rol        TEXT    NOT NULL DEFAULT 'vendedor',
            clave_hash TEXT    NOT NULL DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre         TEXT    NOT NULL UNIQUE,
            metodo_pago    TEXT    NOT NULL DEFAULT '',
            balance_actual REAL    NOT NULL DEFAULT 0,
            color          TEXT    NOT NULL DEFAULT '#3B82F6',
            activa         INTEGER NOT NULL DEFAULT 1,
            orden          INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cuentas_movimientos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cuenta_id   INTEGER NOT NULL REFERENCES cuentas(id) ON DELETE CASCADE,
            fecha       TEXT    NOT NULL,
            tipo        TEXT    NOT NULL,
            monto       REAL    NOT NULL DEFAULT 0,
            descripcion TEXT             DEFAULT '',
            venta_id    INTEGER          DEFAULT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cuentas_cierres (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            anio         INTEGER NOT NULL,
            mes          INTEGER NOT NULL,
            datos_json   TEXT    NOT NULL DEFAULT '[]',
            notas        TEXT             DEFAULT '',
            fecha_cierre TEXT    NOT NULL,
            UNIQUE(anio, mes)
        )
    """)


# ── Sistema de versiones ──────────────────────────────────────────────────────

def _setup_version_table(conn: sqlite3.Connection) -> None:
    """
    Crea la tabla de versiones si no existe.
    Si la BD ya tenía datos (viene del sistema antiguo sin tabla de versiones),
    marca todas las migraciones previas como aplicadas para no re-ejecutarlas.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_version (
            version     INTEGER PRIMARY KEY,
            descripcion TEXT    NOT NULL DEFAULT '',
            aplicada_en TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    version_max = conn.execute(
        "SELECT MAX(version) FROM schema_version"
    ).fetchone()[0]

    if version_max is None:
        # Tabla recién creada — detectar si es BD existente o nueva
        # Una BD existente ya tiene la columna clave_inventario
        tiene_clave = _columna_existe(conn, "configuracion", "clave_inventario")
        if tiene_clave:
            # BD antigua: marcar SOLO las migraciones cuyas columnas/tablas ya existen
            for v, desc, sqls in _MIGRACIONES:
                if _migracion_ya_aplicada(conn, sqls):
                    conn.execute(
                        "INSERT OR IGNORE INTO schema_version (version, descripcion) VALUES (?, ?)",
                        (v, f"[legacy] {desc}"),
                    )
            log.info("BD existente detectada — migraciones legacy marcadas como aplicadas")
        # BD nueva: no insertar nada — las migraciones se aplicarán en orden


def _aplicar_migraciones_pendientes(conn: sqlite3.Connection) -> None:
    """Aplica las migraciones que aún no figuran en schema_version."""
    aplicadas = {
        row[0] for row in conn.execute("SELECT version FROM schema_version").fetchall()
    }

    for version, descripcion, sqls in _MIGRACIONES:
        if version in aplicadas:
            continue

        log.info("Aplicando migración %d: %s", version, descripcion)
        for sql in sqls:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError as e:
                # Columna ya existente u otro error benigno — loguear y continuar
                log.warning("SQL de migración %d omitido (%s): %s", version, e, sql)

        conn.execute(
            "INSERT INTO schema_version (version, descripcion) VALUES (?, ?)",
            (version, descripcion),
        )
        log.info("Migración %d aplicada correctamente", version)


# ── Utilidades ────────────────────────────────────────────────────────────────

def _reparar_migraciones_fallidas(conn: sqlite3.Connection) -> None:
    """
    Detecta migraciones registradas en schema_version pero cuyos cambios no
    existen en el esquema real (causado por el bug de detección legacy que las
    marcaba aplicadas sin ejecutarlas). Las re-aplica sin tocar schema_version.
    """
    aplicadas = {
        row[0] for row in conn.execute("SELECT version FROM schema_version").fetchall()
    }
    for version, descripcion, sqls in _MIGRACIONES:
        if version not in aplicadas:
            continue
        if _migracion_ya_aplicada(conn, sqls):
            continue
        log.info("Reparando migración %d faltante: %s", version, descripcion)
        for sql in sqls:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError as e:
                log.warning("SQL de reparación %d omitido (%s): %s", version, e, sql)


def _migracion_ya_aplicada(conn: sqlite3.Connection, sqls: list[str]) -> bool:
    """
    Verifica si todas las operaciones de una migración ya están presentes en el
    esquema actual. Soporta ALTER TABLE … ADD COLUMN y CREATE TABLE IF NOT EXISTS.
    Las migraciones que no sean de ninguno de esos dos tipos se asumen no aplicadas.
    """
    import re
    for sql in sqls:
        sql_upper = sql.strip().upper()
        m_alter = re.match(r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)", sql_upper)
        if m_alter:
            if not _columna_existe(conn, m_alter.group(1).lower(), m_alter.group(2).lower()):
                return False
            continue
        m_create = re.match(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)", sql_upper)
        if m_create:
            tabla = m_create.group(1).lower()
            existe = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
            ).fetchone()
            if not existe:
                return False
            continue
        # SQL de tipo desconocido — asumir que no está aplicado
        return False
    return True


def _columna_existe(conn: sqlite3.Connection, tabla: str, columna: str) -> bool:
    filas = conn.execute(f"PRAGMA table_info({tabla})").fetchall()
    return any(row[1] == columna for row in filas)


def _seed_configuracion(conn: sqlite3.Connection) -> None:
    """Inserta la fila única de configuración si no existe todavía."""
    existe = conn.execute("SELECT 1 FROM configuracion WHERE id = 1").fetchone()
    if not existe:
        conn.execute("INSERT INTO configuracion (id) VALUES (1)")


# ── Reset completo (zona de peligro) ─────────────────────────────────────────

def resetear_base_datos() -> None:
    """
    Borra TODOS los datos de usuario y restablece los contadores AUTOINCREMENT.
    Conserva la estructura de tablas y la tabla schema_version.
    Esta operación es IRREVERSIBLE — llamar solo tras confirmación explícita.
    """
    conn = DatabaseConnection.get()
    conn.execute("PRAGMA foreign_keys=OFF;")
    for tabla in ("abonos_factura", "facturas", "ventas",
                  "gastos_dia", "prestamos", "inventario",
                  "presupuesto_mensual", "configuracion", "notas"):
        conn.execute(f"DELETE FROM {tabla}")
    conn.execute(
        "DELETE FROM sqlite_sequence WHERE name IN "
        "('abonos_factura','facturas','ventas',"
        "'gastos_dia','prestamos','inventario','notas')"
    )
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.commit()
    _seed_configuracion(conn)
    conn.commit()
    log.warning("Base de datos reseteada completamente por el usuario")
