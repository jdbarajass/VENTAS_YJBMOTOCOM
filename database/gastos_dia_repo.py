"""
database/gastos_dia_repo.py
CRUD para la tabla `gastos_dia`.
"""

import sqlite3
from datetime import date
from models.gasto_dia import GastoDia
from database.connection import DatabaseConnection


def _row_to_gasto(row: sqlite3.Row) -> GastoDia:
    return GastoDia(
        id=row["id"],
        fecha=date.fromisoformat(row["fecha"]),
        descripcion=row["descripcion"],
        monto=row["monto"],
    )


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------

def insertar_gasto(gasto: GastoDia) -> int:
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        "INSERT INTO gastos_dia (fecha, descripcion, monto) VALUES (?, ?, ?)",
        (gasto.fecha.isoformat(), gasto.descripcion.strip(), gasto.monto),
    )
    conn.commit()
    gasto.id = cursor.lastrowid
    return cursor.lastrowid


# ------------------------------------------------------------------
# READ
# ------------------------------------------------------------------

def obtener_gastos_por_fecha(fecha: date) -> list[GastoDia]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM gastos_dia WHERE fecha = ? ORDER BY id ASC",
        (fecha.isoformat(),),
    ).fetchall()
    return [_row_to_gasto(r) for r in rows]


def obtener_gastos_por_mes(año: int, mes: int) -> list[GastoDia]:
    prefix = f"{año:04d}-{mes:02d}-%"
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM gastos_dia WHERE fecha LIKE ? ORDER BY fecha ASC, id ASC",
        (prefix,),
    ).fetchall()
    return [_row_to_gasto(r) for r in rows]


def obtener_todos_gastos() -> list[GastoDia]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM gastos_dia ORDER BY fecha ASC, id ASC"
    ).fetchall()
    return [_row_to_gasto(r) for r in rows]


# ------------------------------------------------------------------
# DELETE
# ------------------------------------------------------------------

def eliminar_gasto(gasto_id: int) -> bool:
    conn = DatabaseConnection.get()
    cursor = conn.execute("DELETE FROM gastos_dia WHERE id = ?", (gasto_id,))
    conn.commit()
    return cursor.rowcount > 0


def eliminar_gastos_por_mes(año: int, mes: int) -> None:
    prefix = f"{año:04d}-{mes:02d}-%"
    conn = DatabaseConnection.get()
    conn.execute("DELETE FROM gastos_dia WHERE fecha LIKE ?", (prefix,))
    conn.commit()


def insertar_gasto_directo(gasto: GastoDia) -> int:
    """Inserta un gasto sin commit inmediato opcional — para importación masiva."""
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        "INSERT INTO gastos_dia (fecha, descripcion, monto) VALUES (?, ?, ?)",
        (gasto.fecha.isoformat(), gasto.descripcion.strip(), gasto.monto),
    )
    conn.commit()
    return cursor.lastrowid
