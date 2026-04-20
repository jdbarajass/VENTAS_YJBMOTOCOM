"""
utils/busy.py
Indicador de carga: cursor de espera + mensaje en barra de estado.
Uso:
    with ocupado(status_bar, "Guardando venta..."):
        guardar_carrito(...)
"""
from contextlib import contextmanager

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


@contextmanager
def ocupado(status_bar=None, mensaje: str = "Procesando..."):
    """
    Context manager que muestra el cursor de espera mientras dura el bloque.
    Opcionalmente actualiza una QStatusBar.
    """
    QApplication.setOverrideCursor(Qt.WaitCursor)
    QApplication.processEvents()
    if status_bar is not None:
        status_bar.showMessage(f"⏳  {mensaje}")
        QApplication.processEvents()
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()
        if status_bar is not None:
            status_bar.showMessage("Listo")
