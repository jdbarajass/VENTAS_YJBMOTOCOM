"""
database/ventas_repo.py
CRUD completo para la tabla `ventas`.

Todas las funciones reciben/retornan objetos Venta del dominio.
La UI nunca toca sqlite3 directamente.
"""

import json
import sqlite3
from datetime import date
from typing import Optional
from models.venta import Venta
from database.connection import DatabaseConnection


def _row_to_venta(row: sqlite3.Row) -> Venta:
    """Convierte una fila de SQLite al modelo de dominio Venta."""
    keys = row.keys()
    pagos_raw = row["pagos_combinados"] if "pagos_combinados" in keys else None
    pagos = json.loads(pagos_raw) if pagos_raw else None
    v = Venta(
        id=row["id"],
        fecha=date.fromisoformat(row["fecha"]),
        producto=row["producto"],
        costo=row["costo"],
        precio=row["precio"],
        metodo_pago=row["metodo_pago"],
        cantidad=row["cantidad"] if "cantidad" in keys else 1,
        comision=row["comision"],
        ganancia_neta=row["ganancia_neta"],
        notas=row["notas"] or "",
        pagos_combinados=pagos,
    )
    v.grupo_venta_id = row["grupo_venta_id"] if "grupo_venta_id" in keys else None
    return v


# ------------------------------------------------------------------
# CREATE
# ------------------------------------------------------------------

def siguiente_grupo_venta_id() -> int:
    """Retorna el proximo grupo_venta_id disponible (max existente + 1)."""
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT COALESCE(MAX(grupo_venta_id), 0) + 1 FROM ventas"
    ).fetchone()
    return row[0]


def insertar_venta(venta: Venta) -> int:
    """
    Persiste una nueva venta y retorna el id generado.
    Actualiza venta.id en el objeto pasado.
    """
    conn = DatabaseConnection.get()
    pagos_json = json.dumps(venta.pagos_combinados) if venta.pagos_combinados else None
    grupo_id = getattr(venta, "grupo_venta_id", None)
    cursor = conn.execute(
        """
        INSERT INTO ventas
            (fecha, producto, costo, precio, metodo_pago, cantidad,
             comision, ganancia_neta, notas, pagos_combinados, grupo_venta_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            venta.fecha.isoformat(),
            venta.producto.strip(),
            venta.costo,
            venta.precio,
            venta.metodo_pago,
            venta.cantidad,
            venta.comision,
            venta.ganancia_neta,
            venta.notas,
            pagos_json,
            grupo_id,
        ),
    )
    conn.commit()
    venta.id = cursor.lastrowid
    return cursor.lastrowid


# ------------------------------------------------------------------
# READ
# ------------------------------------------------------------------

def obtener_venta_por_id(venta_id: int) -> Optional[Venta]:
    """Retorna una Venta por su id, o None si no existe."""
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT * FROM ventas WHERE id = ?", (venta_id,)
    ).fetchone()
    return _row_to_venta(row) if row else None


def obtener_ventas_por_fecha(fecha: date) -> list[Venta]:
    """Retorna todas las ventas de un día específico, ordenadas por id."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM ventas WHERE fecha = ? ORDER BY id ASC",
        (fecha.isoformat(),),
    ).fetchall()
    return [_row_to_venta(r) for r in rows]


def obtener_ventas_por_mes(año: int, mes: int) -> list[Venta]:
    """
    Retorna todas las ventas de un mes/año dado.
    Usa LIKE sobre el campo TEXT 'YYYY-MM-DD' para evitar funciones de fecha.
    """
    prefix = f"{año:04d}-{mes:02d}-%"
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM ventas WHERE fecha LIKE ? ORDER BY fecha ASC, id ASC",
        (prefix,),
    ).fetchall()
    return [_row_to_venta(r) for r in rows]


def obtener_todas_las_ventas() -> list[Venta]:
    """Retorna el histórico completo ordenado por fecha descendente."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT * FROM ventas ORDER BY fecha DESC, id DESC"
    ).fetchall()
    return [_row_to_venta(r) for r in rows]


# ------------------------------------------------------------------
# UPDATE
# ------------------------------------------------------------------

def actualizar_venta(venta: Venta) -> bool:
    """
    Actualiza todos los campos de una venta existente por su id.
    Retorna True si se modificó alguna fila.
    """
    if venta.id is None:
        raise ValueError("No se puede actualizar una venta sin id.")
    conn = DatabaseConnection.get()
    pagos_json = json.dumps(venta.pagos_combinados) if venta.pagos_combinados else None
    cursor = conn.execute(
        """
        UPDATE ventas SET
            fecha              = ?,
            producto           = ?,
            costo              = ?,
            precio             = ?,
            metodo_pago        = ?,
            cantidad           = ?,
            comision           = ?,
            ganancia_neta      = ?,
            notas              = ?,
            pagos_combinados   = ?
        WHERE id = ?
        """,
        (
            venta.fecha.isoformat(),
            venta.producto.strip(),
            venta.costo,
            venta.precio,
            venta.metodo_pago,
            venta.cantidad,
            venta.comision,
            venta.ganancia_neta,
            venta.notas,
            pagos_json,
            venta.id,
        ),
    )
    conn.commit()
    return cursor.rowcount > 0


# ------------------------------------------------------------------
# DELETE
# ------------------------------------------------------------------

def eliminar_venta(venta_id: int) -> bool:
    """
    Elimina una venta por su id.
    Retorna True si se eliminó alguna fila.
    """
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        "DELETE FROM ventas WHERE id = ?", (venta_id,)
    )
    conn.commit()
    return cursor.rowcount > 0


def eliminar_ventas_por_fecha(fecha: date) -> int:
    """Elimina todas las ventas de un día. Retorna la cantidad eliminada."""
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        "DELETE FROM ventas WHERE fecha = ?", (fecha.isoformat(),)
    )
    conn.commit()
    return cursor.rowcount


def eliminar_ventas_por_mes(año: int, mes: int) -> int:
    """Elimina todas las ventas de un mes/año. Retorna la cantidad eliminada."""
    prefix = f"{año:04d}-{mes:02d}-%"
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        "DELETE FROM ventas WHERE fecha LIKE ?", (prefix,)
    )
    conn.commit()
    return cursor.rowcount
