"""
utils/pdf_utils.py
Utilidades para abrir PDFs generados con el visor predeterminado del SO.
"""

import os
import sys


def abrir_pdf(path: str) -> None:
    """Abre el archivo PDF en el visor predeterminado del sistema operativo."""
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')
