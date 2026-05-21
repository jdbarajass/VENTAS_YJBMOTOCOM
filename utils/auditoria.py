"""
utils/auditoria.py
Registro de auditoría: quién hizo qué y cuándo.
Usa un módulo-level para trackear el usuario activo de la sesión.
"""
from datetime import date, datetime

_usuario_actual: str = "Sistema"


def set_usuario(nombre: str) -> None:
    global _usuario_actual
    _usuario_actual = nombre


def get_usuario() -> str:
    return _usuario_actual


def registrar(accion: str, detalle: str = "") -> None:
    """Inserta un registro en log_acciones. Silencia cualquier error para no bloquear la UI."""
    try:
        from database.connection import DatabaseConnection
        conn = DatabaseConnection.get()
        conn.execute(
            "INSERT INTO log_acciones (fecha, hora, accion, detalle, usuario) VALUES (?, ?, ?, ?, ?)",
            (
                date.today().isoformat(),
                datetime.now().strftime("%H:%M:%S"),
                accion,
                (detalle or "")[:500],
                _usuario_actual,
            ),
        )
        conn.commit()
    except Exception:
        pass


def obtener_log(limite: int = 50) -> list[dict]:
    """Retorna los últimos `limite` registros de auditoría, más recientes primero."""
    try:
        from database.connection import DatabaseConnection
        conn = DatabaseConnection.get()
        rows = conn.execute(
            "SELECT fecha, hora, accion, detalle, usuario FROM log_acciones ORDER BY id DESC LIMIT ?",
            (limite,),
        ).fetchall()
        return [
            {"fecha": r[0], "hora": r[1], "accion": r[2], "detalle": r[3], "usuario": r[4]}
            for r in rows
        ]
    except Exception:
        return []
