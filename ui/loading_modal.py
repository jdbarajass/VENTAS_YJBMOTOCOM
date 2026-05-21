"""
ui/loading_modal.py
Modal de carga sin título que bloquea la UI durante operaciones lentas.
Uso como context manager:
    with CargandoModal(parent, "Exportando datos…"):
        operacion_lenta()
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QFrame, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class CargandoModal(QDialog):
    """
    Diálogo modal sin decoración que muestra un mensaje y bloquea la interacción
    mientras el sistema realiza una operación costosa.
    Se usa como context manager — se muestra al entrar y se cierra al salir.
    """

    def __init__(self, parent=None, mensaje: str = "Procesando…"):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedSize(300, 140)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("cardCargando")
        frame.setStyleSheet(
            "QFrame#cardCargando {"
            "  background:#1E293B;"
            "  border-radius:16px;"
            "  border:1px solid #334155;"
            "}"
        )
        lay_f = QVBoxLayout(frame)
        lay_f.setAlignment(Qt.AlignCenter)
        lay_f.setSpacing(8)
        lay_f.setContentsMargins(28, 22, 28, 22)

        lbl_icono = QLabel("⏳")
        lbl_icono.setAlignment(Qt.AlignCenter)
        lbl_icono.setStyleSheet("font-size:26px; background:transparent; border:none;")

        self._lbl_msg = QLabel(mensaje)
        self._lbl_msg.setAlignment(Qt.AlignCenter)
        self._lbl_msg.setWordWrap(True)
        f = QFont()
        f.setPointSize(12)
        f.setBold(True)
        self._lbl_msg.setFont(f)
        self._lbl_msg.setStyleSheet("color:#F8FAFC; background:transparent; border:none;")

        lbl_sub = QLabel("Espera un momento…")
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("color:#64748B; font-size:10px; background:transparent; border:none;")

        lay_f.addWidget(lbl_icono)
        lay_f.addWidget(self._lbl_msg)
        lay_f.addWidget(lbl_sub)
        lay.addWidget(frame)

    def _centrar_en_padre(self):
        p = self.parent()
        if p is None:
            return
        # Usar globalGeometry del padre
        from PySide6.QtCore import QPoint
        centro = p.mapToGlobal(QPoint(p.width() // 2, p.height() // 2))
        self.move(centro.x() - self.width() // 2, centro.y() - self.height() // 2)

    def __enter__(self):
        self._centrar_en_padre()
        self.show()
        QApplication.processEvents()
        return self

    def __exit__(self, *_):
        self.close()
