"""
database/prestamos_repo.py
CRUD para la tabla prestamos.
"""

import sqlite3
from datetime import date, datetime

from database.connection import DatabaseConnection
from models.prestamo import Prestamo


def _parse_fecha(valor: str) -> date:
    """Acepta '2026-03-26' y '2026-03-26T00:00:00' por compatibilidad."""
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return datetime.fromisoformat(valor).date()


def _row_to_prestamo(row: sqlite3.Row) -> Prestamo:
    return Prestamo(
        id=row["id"],
        fecha=_parse_fecha(row["fecha"]),
        producto=row["producto"],
        almacen=row["almacen"],
        observaciones=row["observaciones"] or "",
        estado=row["estado"],
    )


def insertar_prestamo(p: Prestamo) -> int:
    """Persiste un nuevo préstamo y retorna el id asignado."""
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        """
        INSERT INTO prestamos (fecha, producto, almacen, observaciones, estado)
        VALUES (?, ?, ?, ?, ?)
        """,
        (p.fecha.isoformat(), p.producto, p.almacen, p.observaciones, p.estado),
    )
    conn.commit()
    return cursor.lastrowid


def obtener_todos_prestamos() -> list[Prestamo]:
    """Retorna todos los préstamos ordenados por fecha descendente."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM prestamos ORDER BY fecha DESC, id DESC"
    ).fetchall()
    return [_row_to_prestamo(r) for r in rows]


def obtener_prestamos_pendientes() -> list[Prestamo]:
    """Retorna solo los préstamos con estado 'pendiente'."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM prestamos WHERE estado = 'pendiente' ORDER BY fecha ASC, id ASC"
    ).fetchall()
    return [_row_to_prestamo(r) for r in rows]


def actualizar_estado_prestamo(prestamo_id: int, estado: str) -> bool:
    """Cambia el estado de un préstamo (pendiente → devuelto | cobrado)."""
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        "UPDATE prestamos SET estado = ? WHERE id = ?",
        (estado, prestamo_id),
    )
    conn.commit()
    return cursor.rowcount > 0


def actualizar_prestamo(p: Prestamo) -> bool:
    """Actualiza todos los campos editables de un préstamo."""
    if p.id is None:
        return False
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        """UPDATE prestamos
           SET fecha=?, producto=?, almacen=?, observaciones=?, estado=?
           WHERE id=?""",
        (p.fecha.isoformat(), p.producto.strip(), p.almacen.strip(),
         p.observaciones or "", p.estado, p.id),
    )
    conn.commit()
    return cursor.rowcount > 0


def eliminar_prestamo(prestamo_id: int) -> bool:
    """Elimina un préstamo por id."""
    conn = DatabaseConnection.get()
    cursor = conn.execute("DELETE FROM prestamos WHERE id = ?", (prestamo_id,))
    conn.commit()
    return cursor.rowcount > 0


def eliminar_todos_prestamos() -> int:
    """Elimina todos los préstamos. Retorna la cantidad eliminada."""
    conn = DatabaseConnection.get()
    cursor = conn.execute("DELETE FROM prestamos")
    conn.commit()
    return cursor.rowcount
