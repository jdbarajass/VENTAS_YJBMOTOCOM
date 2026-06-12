"""
database/inventario_repo.py
CRUD para la tabla `inventario`.
"""

import sqlite3
from models.producto import Producto
from database.connection import DatabaseConnection
from database.inventario_mov_repo import registrar_movimiento


def _row_to_producto(row: sqlite3.Row) -> Producto:
    keys = row.keys()
    return Producto(
        id=row["id"],
        serial=row["serial"] or "",
        producto=row["producto"],
        costo_unitario=row["costo_unitario"],
        cantidad=row["cantidad"],
        codigo_barras=row["codigo_barras"] or "",
        stock_minimo=row["stock_minimo"] if "stock_minimo" in keys else 0,
        categoria=row["categoria"] if "categoria" in keys else "",
    )


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------

def insertar_producto(p: Producto) -> int:
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        """
        INSERT INTO inventario (serial, producto, costo_unitario, cantidad, codigo_barras, stock_minimo, categoria)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (p.serial, p.producto.strip(), p.costo_unitario, p.cantidad,
         p.codigo_barras, p.stock_minimo, p.categoria.strip()),
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
    """Búsqueda parcial por nombre o código de barras — para el autocomplete del formulario de venta."""
    conn = DatabaseConnection.get()
    patron = f"%{texto}%"
    rows = conn.execute(
        "SELECT * FROM inventario WHERE producto LIKE ? OR codigo_barras LIKE ? ORDER BY producto ASC",
        (patron, patron),
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


def obtener_producto_por_codigo_barras(codigo: str) -> Producto | None:
    """Retorna el producto cuyo código de barras coincide exactamente."""
    if not codigo:
        return None
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT * FROM inventario WHERE codigo_barras = ? LIMIT 1",
        (codigo.strip(),),
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
    # Leer cantidad actual antes de actualizar (para el historial)
    row_ant = conn.execute(
        "SELECT cantidad FROM inventario WHERE id = ?", (p.id,)
    ).fetchone()
    cant_ant = row_ant["cantidad"] if row_ant else 0

    cursor = conn.execute(
        """
        UPDATE inventario SET
            serial         = ?,
            producto       = ?,
            costo_unitario = ?,
            cantidad       = ?,
            codigo_barras  = ?,
            stock_minimo   = ?,
            categoria      = ?
        WHERE id = ?
        """,
        (p.serial, p.producto.strip(), p.costo_unitario, p.cantidad,
         p.codigo_barras, p.stock_minimo, p.categoria.strip(), p.id),
    )
    conn.commit()
    if cursor.rowcount > 0 and cant_ant != p.cantidad:
        registrar_movimiento(p.id, p.producto.strip(), "Ajuste", cant_ant, p.cantidad)
    return cursor.rowcount > 0


def obtener_productos_bajo_stock() -> list[Producto]:
    """Retorna productos cuya cantidad es menor al stock_minimo configurado (> 0)."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM inventario WHERE stock_minimo > 0 AND cantidad < stock_minimo"
        " ORDER BY producto ASC"
    ).fetchall()
    return [_row_to_producto(r) for r in rows]


def decrementar_cantidad(nombre_producto: str, cantidad: int) -> bool:
    """
    Descuenta `cantidad` unidades del producto con ese nombre (case-insensitive).
    El stock nunca baja de 0. Retorna True si encontró el producto.
    """
    conn = DatabaseConnection.get()
    row_ant = conn.execute(
        "SELECT id, cantidad FROM inventario WHERE LOWER(producto) = LOWER(?) LIMIT 1",
        (nombre_producto,),
    ).fetchone()

    cursor = conn.execute(
        """
        UPDATE inventario
        SET cantidad = MAX(0, cantidad - ?)
        WHERE LOWER(producto) = LOWER(?)
        """,
        (cantidad, nombre_producto),
    )
    conn.commit()
    if cursor.rowcount > 0 and row_ant is not None:
        cant_ant = row_ant["cantidad"]
        cant_nva = max(0, cant_ant - cantidad)
        registrar_movimiento(
            row_ant["id"], nombre_producto, "Venta", cant_ant, cant_nva
        )
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
