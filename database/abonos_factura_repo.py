"""
database/abonos_factura_repo.py
CRUD para la tabla abonos_factura.
"""

import sqlite3
from datetime import date, datetime
from models.abono_factura import AbonoFactura
from database.connection import DatabaseConnection


def _row_to_abono(row: sqlite3.Row) -> AbonoFactura:
    fecha_val = row["fecha"]
    if isinstance(fecha_val, str):
        fecha_obj = datetime.strptime(fecha_val, "%Y-%m-%d").date()
    elif isinstance(fecha_val, datetime):
        fecha_obj = fecha_val.date()
    elif isinstance(fecha_val, date):
        fecha_obj = fecha_val
    else:
        fecha_obj = date.today()

    return AbonoFactura(
        id=row["id"],
        factura_id=row["factura_id"],
        monto=row["monto"],
        fecha=fecha_obj,
        notas=row["notas"] or "",
    )


def insertar_abono(a: AbonoFactura) -> int:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        """INSERT INTO abonos_factura (factura_id, monto, fecha, notas)
           VALUES (?, ?, ?, ?)""",
        (a.factura_id, a.monto, a.fecha.strftime("%Y-%m-%d"), a.notas),
    )
    conn.commit()
    a.id = cur.lastrowid
    return cur.lastrowid


def obtener_abonos_por_factura(factura_id: int) -> list[AbonoFactura]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM abonos_factura WHERE factura_id = ? ORDER BY fecha ASC, id ASC",
        (factura_id,),
    ).fetchall()
    return [_row_to_abono(r) for r in rows]


def obtener_total_abonado(factura_id: int) -> float:
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT COALESCE(SUM(monto), 0) AS total FROM abonos_factura WHERE factura_id = ?",
        (factura_id,),
    ).fetchone()
    return round(float(row["total"]), 2)


def eliminar_abono(abono_id: int) -> bool:
    conn = DatabaseConnection.get()
    cur = conn.execute("DELETE FROM abonos_factura WHERE id = ?", (abono_id,))
    conn.commit()
    return cur.rowcount > 0


def eliminar_abonos_por_factura(factura_id: int) -> None:
    conn = DatabaseConnection.get()
    conn.execute("DELETE FROM abonos_factura WHERE factura_id = ?", (factura_id,))
    conn.commit()
