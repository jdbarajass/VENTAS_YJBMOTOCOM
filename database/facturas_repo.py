"""
database/facturas_repo.py
CRUD de la tabla facturas.
"""

from datetime import date, datetime
from database.connection import DatabaseConnection
from models.factura import Factura


def _row_to_factura(row) -> Factura:
    fecha_val = row["fecha_llegada"]
    if isinstance(fecha_val, str):
        fecha_obj = datetime.strptime(fecha_val, "%Y-%m-%d").date()
    elif isinstance(fecha_val, datetime):
        fecha_obj = fecha_val.date()
    elif isinstance(fecha_val, date):
        fecha_obj = fecha_val
    else:
        fecha_obj = date.today()

    return Factura(
        id=row["id"],
        descripcion=row["descripcion"],
        proveedor=row["proveedor"],
        monto=row["monto"],
        fecha_llegada=fecha_obj,
        estado=row["estado"],
        notas=row["notas"] or "",
    )


def insertar_factura(f: Factura) -> int:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        """INSERT INTO facturas
           (descripcion, proveedor, monto, fecha_llegada, estado, notas)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            f.descripcion,
            f.proveedor,
            f.monto,
            f.fecha_llegada.strftime("%Y-%m-%d"),
            f.estado,
            f.notas,
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
    cur = conn.execute(
        """UPDATE facturas
           SET descripcion=?, proveedor=?, monto=?, fecha_llegada=?, estado=?, notas=?
           WHERE id=?""",
        (
            f.descripcion,
            f.proveedor,
            f.monto,
            f.fecha_llegada.strftime("%Y-%m-%d"),
            f.estado,
            f.notas,
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
    cur = conn.execute(
        """INSERT INTO facturas
           (descripcion, proveedor, monto, fecha_llegada, estado, notas)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            f.descripcion,
            f.proveedor,
            f.monto,
            f.fecha_llegada.strftime("%Y-%m-%d"),
            f.estado,
            f.notas,
        ),
    )
    conn.commit()
    return cur.lastrowid
