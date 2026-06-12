"""
database/facturas_items_repo.py
CRUD para los items (líneas) de una factura por pagar.
"""

from database.connection import DatabaseConnection


def insertar_item(factura_id: int, descripcion_item: str, cantidad: float, precio_unitario: float) -> int:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        """
        INSERT INTO facturas_items (factura_id, descripcion_item, cantidad, precio_unitario)
        VALUES (?, ?, ?, ?)
        """,
        (factura_id, descripcion_item.strip(), cantidad, precio_unitario),
    )
    conn.commit()
    return cur.lastrowid


def obtener_items_factura(factura_id: int) -> list[dict]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        """
        SELECT id, factura_id, descripcion_item, cantidad, precio_unitario,
               (cantidad * precio_unitario) AS subtotal
        FROM facturas_items
        WHERE factura_id = ?
        ORDER BY id ASC
        """,
        (factura_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def eliminar_item(item_id: int) -> bool:
    conn = DatabaseConnection.get()
    cur = conn.execute("DELETE FROM facturas_items WHERE id = ?", (item_id,))
    conn.commit()
    return cur.rowcount > 0


def eliminar_items_factura(factura_id: int) -> None:
    conn = DatabaseConnection.get()
    conn.execute("DELETE FROM facturas_items WHERE factura_id = ?", (factura_id,))
    conn.commit()


def total_items_factura(factura_id: int) -> float:
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT COALESCE(SUM(cantidad * precio_unitario), 0) FROM facturas_items WHERE factura_id = ?",
        (factura_id,),
    ).fetchone()
    return float(row[0]) if row else 0.0
