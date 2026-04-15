"""
database/facturas_repo.py
CRUD de la tabla facturas.
"""

from datetime import date, datetime
from database.connection import DatabaseConnection
from models.factura import Factura


def _parse_fecha(val) -> date | None:
    """Convierte un valor de columna fecha TEXT/datetime a date, o None."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _row_to_factura(row) -> Factura:
    fecha_obj = _parse_fecha(row["fecha_llegada"]) or date.today()
    # fecha_vencimiento puede no existir en filas antiguas — usar dict.get con fallback
    try:
        fv_raw = row["fecha_vencimiento"]
    except (IndexError, KeyError):
        fv_raw = None
    fecha_venc = _parse_fecha(fv_raw)

    return Factura(
        id=row["id"],
        descripcion=row["descripcion"],
        proveedor=row["proveedor"],
        monto=row["monto"],
        fecha_llegada=fecha_obj,
        estado=row["estado"],
        notas=row["notas"] or "",
        fecha_vencimiento=fecha_venc,
    )


def insertar_factura(f: Factura) -> int:
    conn = DatabaseConnection.get()
    fv = f.fecha_vencimiento.strftime("%Y-%m-%d") if f.fecha_vencimiento else None
    cur = conn.execute(
        """INSERT INTO facturas
           (descripcion, proveedor, monto, fecha_llegada, estado, notas, fecha_vencimiento)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            f.descripcion,
            f.proveedor,
            f.monto,
            f.fecha_llegada.strftime("%Y-%m-%d"),
            f.estado,
            f.notas,
            fv,
        ),
    )
    conn.commit()
    return cur.lastrowid


def obtener_todas_facturas() -> list[Factura]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM facturas ORDER BY fecha_llegada DESC, id DESC"
    ).fetchall()
    return [_row_to_factura(r) for r in rows]


def obtener_facturas_pendientes() -> list[Factura]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM facturas WHERE estado = 'pendiente' ORDER BY fecha_llegada ASC, id ASC"
    ).fetchall()
    return [_row_to_factura(r) for r in rows]


def actualizar_factura(f: Factura) -> bool:
    conn = DatabaseConnection.get()
    fv = f.fecha_vencimiento.strftime("%Y-%m-%d") if f.fecha_vencimiento else None
    cur = conn.execute(
        """UPDATE facturas
           SET descripcion=?, proveedor=?, monto=?, fecha_llegada=?, estado=?, notas=?,
               fecha_vencimiento=?
           WHERE id=?""",
        (
            f.descripcion,
            f.proveedor,
            f.monto,
            f.fecha_llegada.strftime("%Y-%m-%d"),
            f.estado,
            f.notas,
            fv,
            f.id,
        ),
    )
    conn.commit()
    return cur.rowcount > 0


def actualizar_estado_factura(factura_id: int, estado: str) -> bool:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        "UPDATE facturas SET estado = ? WHERE id = ?",
        (estado, factura_id),
    )
    conn.commit()
    return cur.rowcount > 0


def eliminar_factura(factura_id: int) -> bool:
    conn = DatabaseConnection.get()
    cur = conn.execute("DELETE FROM facturas WHERE id = ?", (factura_id,))
    conn.commit()
    return cur.rowcount > 0


def eliminar_todas_facturas() -> None:
    conn = DatabaseConnection.get()
    conn.execute("DELETE FROM facturas")
    conn.commit()


def insertar_factura_directa(f) -> int:
    """Igual que insertar_factura pero acepta estado arbitrario (para importación)."""
    conn = DatabaseConnection.get()
    fv = f.fecha_vencimiento.strftime("%Y-%m-%d") if getattr(f, "fecha_vencimiento", None) else None
    cur = conn.execute(
        """INSERT INTO facturas
           (descripcion, proveedor, monto, fecha_llegada, estado, notas, fecha_vencimiento)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            f.descripcion,
            f.proveedor,
            f.monto,
            f.fecha_llegada.strftime("%Y-%m-%d"),
            f.estado,
            f.notas,
            fv,
        ),
    )
    conn.commit()
    return cur.lastrowid
