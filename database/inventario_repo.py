"""
database/inventario_repo.py
CRUD para la tabla `inventario`.
"""

import sqlite3
from models.producto import Producto
from database.connection import DatabaseConnection


def _row_to_producto(row: sqlite3.Row) -> Producto:
    return Producto(
        id=row["id"],
        serial=row["serial"] or "",
        producto=row["producto"],
        costo_unitario=row["costo_unitario"],
        cantidad=row["cantidad"],
        codigo_barras=row["codigo_barras"] or "",
    )


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------

def insertar_producto(p: Producto) -> int:
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        """
        INSERT INTO inventario (serial, producto, costo_unitario, cantidad, codigo_barras)
        VALUES (?, ?, ?, ?, ?)
        """,
        (p.serial, p.producto.strip(), p.costo_unitario, p.cantidad, p.codigo_barras),
    )
    conn.commit()
    p.id = cursor.lastrowid
    return cursor.lastrowid


# ------------------------------------------------------------------
# READ
# ------------------------------------------------------------------

def obtener_todos_productos() -> list[Producto]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM inventario ORDER BY CAST(serial AS INTEGER) ASC, serial ASC, producto ASC"
    ).fetchall()
    return [_row_to_producto(r) for r in rows]


def buscar_productos_por_nombre(texto: str) -> list[Producto]:
    """Búsqueda parcial por nombre — para el autocomplete del formulario de venta."""
    conn = DatabaseConnection.get()
    # Sin LIMIT: devuelve todas las coincidencias para que el completer las muestre
    rows = conn.execute(
        "SELECT * FROM inventario WHERE producto LIKE ? ORDER BY producto ASC",
        (f"%{texto}%",),
    ).fetchall()
    return [_row_to_producto(r) for r in rows]


def obtener_producto_por_nombre_exacto(nombre: str) -> Producto | None:
    """Retorna el producto cuyo nombre coincide exactamente (case-insensitive)."""
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT * FROM inventario WHERE LOWER(producto) = LOWER(?) LIMIT 1",
        (nombre,),
    ).fetchone()
    return _row_to_producto(row) if row else None


def obtener_producto_por_id(producto_id: int) -> Producto | None:
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT * FROM inventario WHERE id = ?", (producto_id,)
    ).fetchone()
    return _row_to_producto(row) if row else None


# ------------------------------------------------------------------
# UPDATE
# ------------------------------------------------------------------

def actualizar_producto(p: Producto) -> bool:
    if p.id is None:
        raise ValueError("No se puede actualizar un producto sin id.")
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        """
        UPDATE inventario SET
            serial         = ?,
            producto       = ?,
            costo_unitario = ?,
            cantidad       = ?,
            codigo_barras  = ?
        WHERE id = ?
        """,
        (p.serial, p.producto.strip(), p.costo_unitario, p.cantidad, p.codigo_barras, p.id),
    )
    conn.commit()
    return cursor.rowcount > 0


def decrementar_cantidad(nombre_producto: str, cantidad: int) -> bool:
    """
    Descuenta `cantidad` unidades del producto con ese nombre (case-insensitive).
    El stock nunca baja de 0. Retorna True si encontró el producto.
    """
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        """
        UPDATE inventario
        SET cantidad = MAX(0, cantidad - ?)
        WHERE LOWER(producto) = LOWER(?)
        """,
        (cantidad, nombre_producto),
    )
    conn.commit()
    return cursor.rowcount > 0


# ------------------------------------------------------------------
# DELETE
# ------------------------------------------------------------------

def eliminar_producto(producto_id: int) -> bool:
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        "DELETE FROM inventario WHERE id = ?", (producto_id,)
    )
    conn.commit()
    return cursor.rowcount > 0


def eliminar_todo_inventario() -> int:
    """Borra todo el inventario. Retorna la cantidad de filas eliminadas."""
    conn = DatabaseConnection.get()
    cursor = conn.execute("DELETE FROM inventario")
    conn.commit()
    return cursor.rowcount
