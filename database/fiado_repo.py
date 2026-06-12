"""
database/fiado_repo.py
CRUD para el módulo de clientes deudores (fiado).
"""

from datetime import date
from database.connection import DatabaseConnection
from models.fiado import Fiado, AbonoFiado


def _row_to_fiado(row) -> Fiado:
    f = Fiado(
        id=row[0],
        cliente_nombre=row[1],
        cliente_cedula=row[2] or "",
        cliente_tel=row[3] or "",
        descripcion=row[4],
        monto_total=row[5],
        fecha=date.fromisoformat(row[6]),
        estado=row[7] or "pendiente",
        notas=row[8] or "",
    )
    return f


def _row_to_abono(row) -> AbonoFiado:
    return AbonoFiado(
        id=row[0],
        fiado_id=row[1],
        monto=row[2],
        fecha=date.fromisoformat(row[3]),
        notas=row[4] or "",
    )


# ── Fiados ────────────────────────────────────────────────────────────────────

def insertar_fiado(f: Fiado) -> int:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        """INSERT INTO fiado
           (cliente_nombre, cliente_cedula, cliente_tel, descripcion,
            monto_total, fecha, estado, notas)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (f.cliente_nombre, f.cliente_cedula, f.cliente_tel, f.descripcion,
         f.monto_total, f.fecha.isoformat(), f.estado, f.notas),
    )
    conn.commit()
    return cur.lastrowid


def obtener_todos_fiados() -> list[Fiado]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, cliente_nombre, cliente_cedula, cliente_tel, descripcion,"
        "       monto_total, fecha, estado, notas FROM fiado ORDER BY fecha DESC"
    ).fetchall()
    return [_row_to_fiado(r) for r in rows]


def obtener_fiados_pendientes() -> list[Fiado]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, cliente_nombre, cliente_cedula, cliente_tel, descripcion,"
        "       monto_total, fecha, estado, notas FROM fiado"
        " WHERE estado = 'pendiente' ORDER BY fecha DESC"
    ).fetchall()
    return [_row_to_fiado(r) for r in rows]


def obtener_fiados_por_cliente(nombre: str) -> list[Fiado]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, cliente_nombre, cliente_cedula, cliente_tel, descripcion,"
        "       monto_total, fecha, estado, notas FROM fiado"
        " WHERE LOWER(cliente_nombre) LIKE LOWER(?)"
        " ORDER BY fecha DESC",
        (f"%{nombre}%",),
    ).fetchall()
    return [_row_to_fiado(r) for r in rows]


def actualizar_fiado(f: Fiado) -> bool:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        """UPDATE fiado SET
               cliente_nombre=?, cliente_cedula=?, cliente_tel=?,
               descripcion=?, monto_total=?, fecha=?, estado=?, notas=?
           WHERE id=?""",
        (f.cliente_nombre, f.cliente_cedula, f.cliente_tel,
         f.descripcion, f.monto_total, f.fecha.isoformat(),
         f.estado, f.notas, f.id),
    )
    conn.commit()
    return cur.rowcount > 0


def marcar_pagado_fiado(fiado_id: int) -> bool:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        "UPDATE fiado SET estado='pagado' WHERE id=?", (fiado_id,)
    )
    conn.commit()
    return cur.rowcount > 0


def eliminar_fiado(fiado_id: int) -> bool:
    conn = DatabaseConnection.get()
    cur = conn.execute("DELETE FROM fiado WHERE id=?", (fiado_id,))
    conn.commit()
    return cur.rowcount > 0


# ── Abonos ────────────────────────────────────────────────────────────────────

def insertar_abono_fiado(a: AbonoFiado) -> int:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        "INSERT INTO abonos_fiado (fiado_id, monto, fecha, notas) VALUES (?,?,?,?)",
        (a.fiado_id, a.monto, a.fecha.isoformat(), a.notas),
    )
    conn.commit()
    return cur.lastrowid


def obtener_abonos_fiado(fiado_id: int) -> list[AbonoFiado]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, fiado_id, monto, fecha, notas FROM abonos_fiado"
        " WHERE fiado_id=? ORDER BY fecha ASC",
        (fiado_id,),
    ).fetchall()
    return [_row_to_abono(r) for r in rows]


def total_abonado_fiado(fiado_id: int) -> float:
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT COALESCE(SUM(monto), 0) FROM abonos_fiado WHERE fiado_id=?",
        (fiado_id,),
    ).fetchone()
    return float(row[0]) if row else 0.0


def obtener_todos_abonos_fiado() -> list:
    """Retorna todos los abonos de fiado con nombre del cliente, ordenados por fecha."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        """
        SELECT af.id, af.fiado_id, af.monto, af.fecha, af.notas,
               f.cliente_nombre, f.descripcion
        FROM abonos_fiado af
        JOIN fiado f ON f.id = af.fiado_id
        ORDER BY af.fecha ASC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def eliminar_abono_fiado(abono_id: int) -> bool:
    conn = DatabaseConnection.get()
    cur = conn.execute("DELETE FROM abonos_fiado WHERE id=?", (abono_id,))
    conn.commit()
    return cur.rowcount > 0
