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
    _create_configuracion(conn)
    _seed_configuracion(conn)
    _migrate_ventas(conn)
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


def _migrate_ventas(conn: sqlite3.Connection) -> None:
    """Agrega columnas nuevas a ventas si no existen (migraciones forward-only)."""
    try:
        conn.execute("ALTER TABLE ventas ADD COLUMN cantidad INTEGER NOT NULL DEFAULT 1")
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


def _seed_configuracion(conn: sqlite3.Connection) -> None:
    """Inserta la fila única de configuración si no existe todavía."""
    exists = conn.execute(
        "SELECT 1 FROM configuracion WHERE id = 1"
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO configuracion (id) VALUES (1)"
        )
