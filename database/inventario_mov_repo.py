"""
database/inventario_mov_repo.py
Registro y consulta del historial de movimientos de inventario.
"""

from datetime import datetime
from database.connection import DatabaseConnection


def registrar_movimiento(
    producto_id: int,
    producto: str,
    tipo: str,
    cantidad_ant: int,
    cantidad_nva: int,
    notas: str = "",
    commit: bool = True,
) -> None:
    """Inserta un registro de movimiento. Llamado automáticamente por los repos de inventario.
    Si commit=False, no confirma la transacción (uso en importación masiva)."""
    if cantidad_ant == cantidad_nva:
        return
    ahora = datetime.now()
    conn = DatabaseConnection.get()
    conn.execute(
        """
        INSERT INTO inventario_movimientos
            (fecha, hora, producto_id, producto, tipo, cantidad_ant, cantidad_nva, diferencia, notas)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ahora.strftime("%Y-%m-%d"),
            ahora.strftime("%H:%M:%S"),
            producto_id,
            producto,
            tipo,
            cantidad_ant,
            cantidad_nva,
            cantidad_nva - cantidad_ant,
            notas,
        ),
    )
    if commit:
        conn.commit()


def insertar_movimiento_directo(
    fecha: str, hora: str, producto_id: int, producto: str, tipo: str,
    cantidad_ant: int, cantidad_nva: int, notas: str = "", commit: bool = True,
) -> int:
    """Inserta un movimiento histórico exacto (fecha/hora/cantidades tal cual
    vienen del Excel), sin el guard de `registrar_movimiento` que omite
    movimientos donde cantidad_ant == cantidad_nva — usado para restaurar
    fielmente un respaldo, no para uso operativo en vivo."""
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        """
        INSERT INTO inventario_movimientos
            (fecha, hora, producto_id, producto, tipo, cantidad_ant, cantidad_nva, diferencia, notas)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (fecha, hora, producto_id, producto, tipo, cantidad_ant, cantidad_nva,
         cantidad_nva - cantidad_ant, notas),
    )
    if commit:
        conn.commit()
    return cursor.lastrowid


def eliminar_todos_movimientos(commit: bool = True) -> int:
    conn = DatabaseConnection.get()
    cursor = conn.execute("DELETE FROM inventario_movimientos")
    if commit:
        conn.commit()
    return cursor.rowcount


def obtener_movimientos_recientes(limite: int = 200) -> list[dict]:
    """Retorna los últimos `limite` movimientos ordenados por más reciente primero."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        """
        SELECT id, fecha, hora, producto_id, producto, tipo,
               cantidad_ant, cantidad_nva, diferencia, notas
        FROM inventario_movimientos
        ORDER BY id DESC
        LIMIT ?
        """,
        (limite,),
    ).fetchall()
    return [dict(r) for r in rows]


def obtener_todos_movimientos() -> list[dict]:
    """Retorna todos los movimientos de inventario ordenados cronológicamente."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        """
        SELECT id, fecha, hora, producto_id, producto, tipo,
               cantidad_ant, cantidad_nva, diferencia, notas
        FROM inventario_movimientos
        ORDER BY id ASC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def obtener_movimientos_producto(producto_id: int, limite: int = 100) -> list[dict]:
    """Retorna los movimientos de un producto específico."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        """
        SELECT id, fecha, hora, producto_id, producto, tipo,
               cantidad_ant, cantidad_nva, diferencia, notas
        FROM inventario_movimientos
        WHERE producto_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (producto_id, limite),
    ).fetchall()
    return [dict(r) for r in rows]
