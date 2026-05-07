"""
database/config_repo.py
Lectura y escritura de la configuración operativa (fila única).
"""

import sqlite3
from models.configuracion import Configuracion
from database.connection import DatabaseConnection


def _row_to_config(row: sqlite3.Row) -> Configuracion:
    keys = row.keys()
    return Configuracion(
        arriendo=row["arriendo"],
        sueldo=row["sueldo"],
        servicios=row["servicios"],
        otros_gastos=row["otros_gastos"],
        dias_mes=row["dias_mes"],
        comision_bold=row["comision_bold"],
        comision_addi=row["comision_addi"],
        comision_transferencia=row["comision_transferencia"],
        clave_inventario=row["clave_inventario"] if "clave_inventario" in keys else "YJB2026_*",
        nombre_impresora=row["nombre_impresora"] if "nombre_impresora" in keys else "",
    )


def obtener_configuracion() -> Configuracion:
    """Retorna la configuración actual. Siempre existe (seed en schema)."""
    conn = DatabaseConnection.get()
    row = conn.execute("SELECT * FROM configuracion WHERE id = 1").fetchone()
    if row is None:
        return Configuracion()  # fallback con valores en cero
    return _row_to_config(row)


def guardar_configuracion(cfg: Configuracion) -> None:
    """Actualiza la fila única de configuración (siempre id=1)."""
    conn = DatabaseConnection.get()
    conn.execute(
        """
        UPDATE configuracion SET
            arriendo               = ?,
            sueldo                 = ?,
            servicios              = ?,
            otros_gastos           = ?,
            dias_mes               = ?,
            comision_bold          = ?,
            comision_addi          = ?,
            comision_transferencia = ?,
            clave_inventario       = ?,
            nombre_impresora       = ?
        WHERE id = 1
        """,
        (
            cfg.arriendo,
            cfg.sueldo,
            cfg.servicios,
            cfg.otros_gastos,
            cfg.dias_mes,
            cfg.comision_bold,
            cfg.comision_addi,
            cfg.comision_transferencia,
            cfg.clave_inventario,
            cfg.nombre_impresora,
        ),
    )
    conn.commit()
