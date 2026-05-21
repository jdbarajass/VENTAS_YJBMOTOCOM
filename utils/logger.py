"""
utils/logger.py
Logger centralizado. Escribe a errors.log junto a la BD y también a consola en desarrollo.
Usar: from utils.logger import log; log.error("mensaje", exc_info=True)
"""

import logging
import sys
from pathlib import Path


def _ruta_log() -> Path:
    """Devuelve la ruta del archivo de log junto al ejecutable o al proyecto."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent
    return base / "errors.log"


def _configurar_logger() -> logging.Logger:
    logger = logging.getLogger("yjbmotocom")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler a archivo (siempre activo)
    fh = logging.FileHandler(_ruta_log(), encoding="utf-8")
    fh.setLevel(logging.WARNING)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Handler a consola (solo en desarrollo, no en .exe compilado)
    if not getattr(sys, "frozen", False):
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    return logger


log = _configurar_logger()
