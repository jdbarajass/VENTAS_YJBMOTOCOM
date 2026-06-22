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
        comision_nequi=float(row["comision_nequi"])         if "comision_nequi"     in keys else 0.0,
        comision_nu=float(row["comision_nu"])               if "comision_nu"        in keys else 0.0,
        comision_qr=float(row["comision_qr"])               if "comision_qr"        in keys else 0.0,
        comision_daviplata=float(row["comision_daviplata"]) if "comision_daviplata" in keys else 0.0,
        comision_datafono=float(row["comision_datafono"])   if "comision_datafono"  in keys else 0.0,
        clave_inventario=row["clave_inventario"] if "clave_inventario" in keys else "YJB2026_*",
        nombre_impresora=row["nombre_impresora"] if "nombre_impresora" in keys else "",
        modo_oscuro=bool(row["modo_oscuro"]) if "modo_oscuro" in keys else False,
        timeout_minutos=int(row["timeout_minutos"]) if "timeout_minutos" in keys else 10,
        backup_automatico_activo=bool(row["backup_automatico_activo"]) if "backup_automatico_activo" in keys else True,
        backup_intervalo_horas=int(row["backup_intervalo_horas"]) if "backup_intervalo_horas" in keys else 24,
    )


def obtener_configuracion() -> Configuracion:
    """Retorna la configuración actual. Siempre existe (seed en schema)."""
    conn = DatabaseConnection.get()
    row = conn.execute("SELECT * FROM configuracion WHERE id = 1").fetchone()
    if row is None:
        return Configuracion()  # fallback con valores en cero
    return _row_to_config(row)


def guardar_configuracion(cfg: Configuracion, commit: bool = True) -> None:
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
            comision_nequi         = ?,
            comision_nu            = ?,
            comision_qr            = ?,
            comision_daviplata     = ?,
            comision_datafono      = ?,
            clave_inventario       = ?,
            nombre_impresora       = ?,
            modo_oscuro            = ?,
            timeout_minutos        = ?,
            backup_automatico_activo = ?,
            backup_intervalo_horas   = ?
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
            cfg.comision_nequi,
            cfg.comision_nu,
            cfg.comision_qr,
            cfg.comision_daviplata,
            cfg.comision_datafono,
            cfg.clave_inventario,
            cfg.nombre_impresora,
            int(cfg.modo_oscuro),
            cfg.timeout_minutos,
            int(cfg.backup_automatico_activo),
            cfg.backup_intervalo_horas,
        ),
    )
    if commit:
        conn.commit()
