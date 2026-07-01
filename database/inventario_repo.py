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
        talla=row["talla"] if "talla" in keys else "",
    )


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------

def codigo_barras_en_uso(codigo: str, excluir_id: int | None = None) -> bool:
    """True si `codigo` ya está asignado a otro producto del inventario."""
    if not codigo:
        return False
    conn = DatabaseConnection.get()
    if excluir_id is None:
        row = conn.execute(
            "SELECT 1 FROM inventario WHERE codigo_barras = ? LIMIT 1", (codigo,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM inventario WHERE codigo_barras = ? AND id != ? LIMIT 1",
            (codigo, excluir_id),
        ).fetchone()
    return row is not None


def insertar_producto(p: Producto, commit: bool = True) -> int:
    """Si commit=False, no confirma la transacción (uso en importación masiva)."""
    if codigo_barras_en_uso(p.codigo_barras):
        raise ValueError(
            f"El código de barras '{p.codigo_barras}' ya está asignado a otro producto."
        )
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        """
        INSERT INTO inventario (serial, producto, costo_unitario, cantidad, codigo_barras, stock_minimo, categoria, talla)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (p.serial, p.producto.strip(), p.costo_unitario, p.cantidad,
         p.codigo_barras, p.stock_minimo, p.categoria.strip(), p.talla.strip()),
    )
    if commit:
        conn.commit()
    p.id = cursor.lastrowid
    if p.cantidad > 0:
        registrar_movimiento(p.id, p.producto.strip(), "Entrada", 0, p.cantidad, commit=commit)
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


def obtener_producto_por_id(pid: int) -> Producto | None:
    """Retorna el producto por su ID primario."""
    conn = DatabaseConnection.get()
    row = conn.execute("SELECT * FROM inventario WHERE id = ?", (pid,)).fetchone()
    return _row_to_producto(row) if row else None


def obtener_variantes_por_nombre(nombre: str) -> list[Producto]:
    """Retorna todos los registros de inventario con ese nombre exacto, ordenados por talla.
    Usado para saber qué tallas existen de un producto y cuál tiene stock disponible."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM inventario WHERE LOWER(producto) = LOWER(?) ORDER BY talla ASC",
        (nombre,),
    ).fetchall()
    return [_row_to_producto(r) for r in rows]


def buscar_producto_por_nombre_y_talla(nombre: str, talla: str) -> Producto | None:
    """Retorna el producto cuyo nombre Y talla coinciden exactamente (case-insensitive).
    Usado para distinguir variantes de talla del mismo producto."""
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT * FROM inventario WHERE LOWER(producto) = LOWER(?) AND LOWER(talla) = LOWER(?) LIMIT 1",
        (nombre, talla),
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
    if codigo_barras_en_uso(p.codigo_barras, excluir_id=p.id):
        raise ValueError(
            f"El código de barras '{p.codigo_barras}' ya está asignado a otro producto."
        )
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
            categoria      = ?,
            talla          = ?
        WHERE id = ?
        """,
        (p.serial, p.producto.strip(), p.costo_unitario, p.cantidad,
         p.codigo_barras, p.stock_minimo, p.categoria.strip(), p.talla.strip(), p.id),
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


def decrementar_cantidad(nombre_producto: str, cantidad: int, talla: str = "") -> bool:
    """
    Descuenta `cantidad` unidades del producto con ese nombre (case-insensitive).
    Si se indica `talla`, solo afecta al registro con esa talla específica — imprescindible
    cuando el mismo nombre existe en varias tallas (ej. CHAQUETA S / M / L).
    Sin talla, actualiza todos los registros con ese nombre (comportamiento heredado para
    productos sin variantes de talla).
    El stock nunca baja de 0. Retorna True si encontró el producto.
    """
    conn = DatabaseConnection.get()
    _talla = (talla or "").strip()
    if _talla and _talla not in ("—", "N/A"):
        row_ant = conn.execute(
            "SELECT id, cantidad FROM inventario WHERE LOWER(producto) = LOWER(?) AND LOWER(talla) = LOWER(?) LIMIT 1",
            (nombre_producto, _talla),
        ).fetchone()
        cursor = conn.execute(
            "UPDATE inventario SET cantidad = MAX(0, cantidad - ?) WHERE LOWER(producto) = LOWER(?) AND LOWER(talla) = LOWER(?)",
            (cantidad, nombre_producto, _talla),
        )
    else:
        row_ant = conn.execute(
            "SELECT id, cantidad FROM inventario WHERE LOWER(producto) = LOWER(?) LIMIT 1",
            (nombre_producto,),
        ).fetchone()
        cursor = conn.execute(
            "UPDATE inventario SET cantidad = MAX(0, cantidad - ?) WHERE LOWER(producto) = LOWER(?)",
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


def incrementar_cantidad(nombre_producto: str, cantidad: int, talla: str = "") -> bool:
    """
    Devuelve `cantidad` unidades al stock del producto (reversa de una venta eliminada).
    Si se indica `talla`, solo restaura el registro con esa talla específica.
    Retorna True si encontró el producto.
    """
    conn = DatabaseConnection.get()
    _talla = (talla or "").strip()
    if _talla and _talla not in ("—", "N/A"):
        row_ant = conn.execute(
            "SELECT id, cantidad FROM inventario WHERE LOWER(producto) = LOWER(?) AND LOWER(talla) = LOWER(?) LIMIT 1",
            (nombre_producto, _talla),
        ).fetchone()
        cursor = conn.execute(
            "UPDATE inventario SET cantidad = cantidad + ? WHERE LOWER(producto) = LOWER(?) AND LOWER(talla) = LOWER(?)",
            (cantidad, nombre_producto, _talla),
        )
    else:
        row_ant = conn.execute(
            "SELECT id, cantidad FROM inventario WHERE LOWER(producto) = LOWER(?) LIMIT 1",
            (nombre_producto,),
        ).fetchone()
        cursor = conn.execute(
            "UPDATE inventario SET cantidad = cantidad + ? WHERE LOWER(producto) = LOWER(?)",
            (cantidad, nombre_producto),
        )
    conn.commit()
    if cursor.rowcount > 0 and row_ant is not None:
        cant_ant = row_ant["cantidad"]
        registrar_movimiento(
            row_ant["id"], nombre_producto, "Reversa venta", cant_ant, cant_ant + cantidad
        )
    return cursor.rowcount > 0


def actualizar_cantidad_con_tipo(
    prod_id: int,
    nombre: str,
    nueva_cantidad: int,
    tipo: str,
    notas: str = "",
) -> None:
    """Actualiza solo la cantidad de un producto y registra el movimiento con el tipo indicado.
    Usar cuando se necesita un tipo específico (Cambio, Entrada, etc.) en lugar de 'Ajuste'."""
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT cantidad FROM inventario WHERE id = ?", (prod_id,)
    ).fetchone()
    cant_ant = row["cantidad"] if row else 0
    conn.execute(
        "UPDATE inventario SET cantidad = ? WHERE id = ?",
        (nueva_cantidad, prod_id),
    )
    conn.commit()
    registrar_movimiento(prod_id, nombre, tipo, cant_ant, nueva_cantidad, notas=notas)


# ------------------------------------------------------------------
# DELETE
# ------------------------------------------------------------------

def eliminar_producto(producto_id: int) -> bool:
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT producto, cantidad FROM inventario WHERE id = ?", (producto_id,)
    ).fetchone()
    cursor = conn.execute(
        "DELETE FROM inventario WHERE id = ?", (producto_id,)
    )
    conn.commit()
    if cursor.rowcount > 0 and row is not None and row["cantidad"] > 0:
        registrar_movimiento(
            producto_id, row["producto"], "Eliminado", row["cantidad"], 0,
            notas="Producto eliminado del inventario",
        )
    return cursor.rowcount > 0


def eliminar_todo_inventario(commit: bool = True) -> int:
    """Borra todo el inventario. Retorna la cantidad de filas eliminadas."""
    conn = DatabaseConnection.get()
    cursor = conn.execute("DELETE FROM inventario")
    if commit:
        conn.commit()
    return cursor.rowcount
