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

    try:
        cuenta_id = row["cuenta_id"]
    except (IndexError, KeyError):
        cuenta_id = None

    return AbonoFactura(
        id=row["id"],
        factura_id=row["factura_id"],
        monto=row["monto"],
        fecha=fecha_obj,
        notas=row["notas"] or "",
        cuenta_id=cuenta_id,
    )


def insertar_abono(a: AbonoFactura) -> int:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        """INSERT INTO abonos_factura (factura_id, monto, fecha, notas, cuenta_id)
           VALUES (?, ?, ?, ?, ?)""",
        (a.factura_id, a.monto, a.fecha.strftime("%Y-%m-%d"), a.notas, a.cuenta_id),
    )
    conn.commit()
    a.id = cur.lastrowid
    return cur.lastrowid


def obtener_abono_por_id(abono_id: int) -> AbonoFactura | None:
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT * FROM abonos_factura WHERE id = ?", (abono_id,)
    ).fetchone()
    return _row_to_abono(row) if row else None


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


def eliminar_todos_abonos() -> None:
    conn = DatabaseConnection.get()
    conn.execute("DELETE FROM abonos_factura")
    conn.commit()


def obtener_todos_abonos_con_factura() -> list[dict]:
    """
    Retorna todos los abonos junto con descripción y proveedor de su factura.
    Cada elemento: {factura_desc, factura_prov, monto, fecha, notas}
    """
    conn = DatabaseConnection.get()
    rows = conn.execute(
        """SELECT a.monto, a.fecha, a.notas,
                  f.descripcion AS factura_desc, f.proveedor AS factura_prov
           FROM abonos_factura a
           JOIN facturas f ON f.id = a.factura_id
           ORDER BY f.id, a.fecha, a.id"""
    ).fetchall()
    result = []
    for r in rows:
        fecha_val = r["fecha"]
        if isinstance(fecha_val, str):
            from datetime import datetime as _dt
            try:
                fecha_obj = _dt.strptime(fecha_val, "%Y-%m-%d").date()
            except ValueError:
                from datetime import date as _d
                fecha_obj = _d.today()
        else:
            fecha_obj = fecha_val
        result.append({
            "factura_desc": r["factura_desc"],
            "factura_prov": r["factura_prov"],
            "monto": float(r["monto"]),
            "fecha": fecha_obj,
            "notas": r["notas"] or "",
        })
    return result
