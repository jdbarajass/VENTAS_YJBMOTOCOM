#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YJBMOTOCOM - Sistema de Control de Rentabilidad
================================================

Aplicación de escritorio para el análisis de rentabilidad real
de un negocio de venta de accesorios para motos.

Autor: YJBMOTOCOM
Versión: 1.0.0
Python: 3.11+
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.main_window import MainWindow
from config import APP_NAME


def main():
    """
    Punto de entrada principal de la aplicación.
    """
    # Configurar alta resolución DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Crear aplicación
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("YJBMOTOCOM")

    # Configurar fuente por defecto
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Crear y mostrar ventana principal
    window = MainWindow()
    window.show()

    # Ejecutar bucle de eventos
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
