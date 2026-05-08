"""
ui/recibo_preview_dialog.py
Diálogo de vista previa del recibo POS con opción de imprimir.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QFrame,
)

from services.escpos_printer import generar_texto_recibo


class ReciboPreviewDialog(QDialog):
    """
    Muestra el texto del recibo en fuente monoespaciada.
    Botón Imprimir → imprime via ESC/POS o PDF (mismo flujo de imprimir_recibo).
    """

    def __init__(self, ventas: list, parent=None) -> None:
        super().__init__(parent)
        self._ventas = list(ventas)
        self.setWindowTitle("Vista previa del recibo")
        self.setModal(True)
        self.setMinimumWidth(460)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 14, 16, 14)

        # Título
        lbl = QLabel("Recibo")
        lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E293B;")
        root.addWidget(lbl)

        # Área de texto con estilo recibo
        self._txt = QTextEdit()
        self._txt.setReadOnly(True)
        self._txt.setFont(QFont("Courier New", 9))
        self._txt.setLineWrapMode(QTextEdit.NoWrap)
        self._txt.setStyleSheet(
            "QTextEdit {"
            "  background: #FFFEF7;"
            "  border: 1px solid #D1D5DB;"
            "  border-radius: 6px;"
            "  padding: 10px 12px;"
            "  color: #111827;"
            "}"
        )
        self._txt.setMinimumHeight(480)
        texto = generar_texto_recibo(self._ventas)
        self._txt.setPlainText(texto)
        root.addWidget(self._txt)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #E5E7EB;")
        root.addWidget(sep)

        # Botones
        btns = QHBoxLayout()
        btns.setSpacing(8)

        self._btn_imprimir = QPushButton("Imprimir")
        self._btn_imprimir.setFixedHeight(34)
        self._btn_imprimir.setStyleSheet(
            "QPushButton { background:#1D4ED8; color:white; border:none;"
            "border-radius:6px; font-size:12px; font-weight:bold; padding:0 20px; }"
            "QPushButton:hover { background:#1E40AF; }"
            "QPushButton:disabled { background:#93C5FD; }"
        )
        self._btn_imprimir.clicked.connect(self._on_imprimir)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedHeight(34)
        btn_cerrar.setStyleSheet(
            "QPushButton { background:#F3F4F6; color:#374151; border:1px solid #D1D5DB;"
            "border-radius:6px; font-size:12px; font-weight:bold; padding:0 20px; }"
            "QPushButton:hover { background:#E5E7EB; }"
        )
        btn_cerrar.clicked.connect(self.accept)

        btns.addWidget(self._btn_imprimir)
        btns.addWidget(btn_cerrar)
        root.addLayout(btns)

    def _on_imprimir(self) -> None:
        from utils.pdf_utils import imprimir_recibo
        from PySide6.QtWidgets import QMessageBox

        self._btn_imprimir.setEnabled(False)
        self._btn_imprimir.setText("Imprimiendo…")
        try:
            enviado = imprimir_recibo(self._ventas)
            if not enviado:
                QMessageBox.information(
                    self, "Imprimir recibo",
                    "El PDF se abrió en el visor.\n\n"
                    "Para evitar papel en blanco al imprimir:\n"
                    "  • Selecciona «Tamaño real» (sin escalar) en el diálogo de impresión.\n\n"
                    "Tip: instala SumatraPDF para impresión directa automática:\n"
                    "  sumatrapdfreader.org"
                )
        except Exception as exc:
            QMessageBox.warning(self, "Error al imprimir", str(exc))
        finally:
            self._btn_imprimir.setEnabled(True)
            self._btn_imprimir.setText("Imprimir")
