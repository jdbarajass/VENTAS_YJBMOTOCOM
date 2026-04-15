"""
utils/backup.py
Backup automático de la base de datos SQLite.

- Crea una copia en <directorio_db>/backups/ con timestamp.
- Conserva únicamente los últimos N backups (por defecto 7).
- Seguro de llamar sin que afecte el funcionamiento normal si falla.
"""

import shutil
import logging
from datetime import datetime
from pathlib import Path

from database.connection import get_db_path

_log = logging.getLogger(__name__)

# Máximo de copias que se mantienen (las más antiguas se eliminan)
MAX_BACKUPS = 7


def hacer_backup() -> Path | None:
    """
    Copia la base de datos activa a la carpeta backups/.

    Retorna la ruta del archivo creado, o None si ocurrió un error.
    El proceso de backup no interrumpe la app aunque falle.
    """
    try:
        db_path = get_db_path()
        if not db_path.exists():
            return None

        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = backup_dir / f"yjbmotocom_{timestamp}.db"

        shutil.copy2(str(db_path), str(destino))
        _log.info("Backup creado: %s", destino.name)

        _limpiar_backups_viejos(backup_dir)
        return destino

    except Exception as exc:  # noqa: BLE001
        _log.warning("No se pudo crear el backup: %s", exc)
        return None


def _limpiar_backups_viejos(backup_dir: Path) -> None:
    """Elimina backups sobrantes, manteniendo los MAX_BACKUPS más recientes."""
    archivos = sorted(backup_dir.glob("yjbmotocom_*.db"), key=lambda p: p.stat().st_mtime)
    sobrantes = archivos[:-MAX_BACKUPS] if len(archivos) > MAX_BACKUPS else []
    for viejo in sobrantes:
        try:
            viejo.unlink()
            _log.info("Backup antiguo eliminado: %s", viejo.name)
        except Exception as exc:  # noqa: BLE001
            _log.warning("No se pudo eliminar backup %s: %s", viejo.name, exc)
