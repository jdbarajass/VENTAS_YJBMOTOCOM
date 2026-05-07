"""
utils/pdf_utils.py
Utilidades para abrir e imprimir PDFs.

imprimir_pdf_pos() intenta usar SumatraPDF (sin escalado) si está disponible,
lo que evita el problema de papel en blanco en impresoras térmicas POS cuando
el visor del SO imprime en papel A4/Carta en lugar del tamaño exacto del PDF.
"""

import os
import shutil
import subprocess
import sys


def abrir_pdf(path: str) -> None:
    """Abre el archivo PDF en el visor predeterminado del sistema operativo."""
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{path}"')
    else:
        os.system(f'xdg-open "{path}"')


# Rutas comunes de SumatraPDF en Windows
_SUMATRA_PATHS = [
    r"C:\Program Files\SumatraPDF\SumatraPDF.exe",
    r"C:\Program Files (x86)\SumatraPDF\SumatraPDF.exe",
    r"C:\Users\ACER\AppData\Local\SumatraPDF\SumatraPDF.exe",
]


def _buscar_sumatra() -> str | None:
    """Retorna la ruta a SumatraPDF si está instalado, o None."""
    en_path = shutil.which("SumatraPDF")
    if en_path:
        return en_path
    return next((p for p in _SUMATRA_PATHS if os.path.exists(p)), None)


def imprimir_pdf_pos(path: str) -> bool:
    """
    Imprime el PDF directamente a la impresora por defecto usando SumatraPDF
    con opción 'noscale' para que el tamaño del ticket sea exacto (sin papel
    en blanco). Si SumatraPDF no está disponible, abre el PDF en el visor
    normal para impresión manual.

    Retorna True si se envió a la impresora, False si se abrió en el visor.

    Para instalar SumatraPDF (gratuito): https://www.sumatrapdfreader.org
    """
    if sys.platform != "win32":
        abrir_pdf(path)
        return False

    sumatra = _buscar_sumatra()
    if sumatra:
        subprocess.Popen(
            [sumatra, "-print-to-default", "-print-settings", "noscale", path],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True

    # Fallback: abrir en visor para impresión manual
    abrir_pdf(path)
    return False


def imprimir_recibo(ventas) -> bool:
    """
    Punto de entrada unificado para imprimir un recibo POS.
    Acepta una Venta o lista de Ventas.

    Orden de intento:
      1. ESC/POS directo (si hay impresora configurada) — sin papel en blanco.
      2. SumatraPDF con noscale (si está instalado).
      3. Visor del SO para impresión manual (fallback).

    Retorna True si se envió a la impresora física.
    """
    from models.venta import Venta
    if isinstance(ventas, Venta):
        ventas = [ventas]
    ventas = list(ventas)

    # 1. ESC/POS directo
    try:
        from database.config_repo import obtener_configuracion
        from services.escpos_printer import imprimir_recibo_escpos
        cfg = obtener_configuracion()
        if cfg.nombre_impresora:
            if imprimir_recibo_escpos(ventas, cfg.nombre_impresora):
                return True
    except Exception:
        pass

    # 2 & 3. PDF (SumatraPDF o visor)
    from services.recibo_generator import generar_recibo
    path = generar_recibo(ventas)
    return imprimir_pdf_pos(path)
