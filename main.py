"""
main.py — Punto de entrada de YJBMOTOCOM.

Responsabilidades:
- Inicializar QApplication con configuración global.
- Instanciar MainWindow.
- Arrancar el event loop.

NO contiene lógica de negocio ni acceso a datos.
"""

import sys
from PySide6.QtWidgets import QApplication
from database.schema import initialize_schema
from database.connection import DatabaseConnection
from ui.main_window import MainWindow
from ui.styles import GLOBAL_STYLESHEET
from utils.backup import hacer_backup


def main() -> None:
    """Punto de entrada principal."""
    # Qt6 habilita DPI scaling automáticamente — no se necesitan atributos manuales.
    # Compatible con Windows 10 y Windows 11.
    app = QApplication(sys.argv)
    app.setApplicationName("YJBMOTOCOM")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("YJBMOTOCOM")

    # Estilo Fusion como base + hoja de estilos global del sistema de diseño
    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_STYLESHEET)

    # Inicializar base de datos antes de mostrar la ventana
    initialize_schema()

    # Backup automático al arrancar (guarda hasta 7 copias en backups/)
    hacer_backup()

    window = MainWindow()
    window.showMaximized()

    # Cerrar BD limpiamente al salir
    app.aboutToQuit.connect(DatabaseConnection.close)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
