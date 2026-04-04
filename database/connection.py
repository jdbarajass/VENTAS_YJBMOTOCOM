"""
database/connection.py
Gestión centralizada de la conexión SQLite.

- Una sola conexión por proceso (patrón singleton).
- La base de datos se guarda junto al ejecutable en producción
  y en la raíz del proyecto en desarrollo.
- Compatible con Windows 10 y Windows 11.
"""

import sqlite3
import sys
from pathlib import Path


def get_db_path() -> Path:
    """
    Retorna la ruta absoluta del archivo .db.

    En modo ejecutable (PyInstaller) usa el directorio del .exe.
    En modo desarrollo usa la raíz del proyecto.
    """
    if getattr(sys, "frozen", False):
        # Ejecutable generado por PyInstaller
        base = Path(sys.executable).parent
    else:
        # Desarrollo: raíz del repositorio
        base = Path(__file__).resolve().parent.parent

    return base / "yjbmotocom.db"


class DatabaseConnection:
    """
    Singleton que mantiene la conexión activa a SQLite.
    Uso:
        conn = DatabaseConnection.get()
    """

    _instance: sqlite3.Connection | None = None

    @classmethod
    def get(cls) -> sqlite3.Connection:
        """Retorna la conexión activa, creándola si no existe."""
        if cls._instance is None:
            db_path = get_db_path()
            cls._instance = sqlite3.connect(
                str(db_path),
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False,
            )
            cls._instance.row_factory = sqlite3.Row
            # WAL mode: mejor rendimiento en escrituras concurrentes
            cls._instance.execute("PRAGMA journal_mode=WAL;")
            cls._instance.execute("PRAGMA foreign_keys=ON;")
        return cls._instance

    @classmethod
    def close(cls) -> None:
        """Cierra la conexión limpiamente al salir de la app."""
        if cls._instance is not None:
            cls._instance.close()
            cls._instance = None
