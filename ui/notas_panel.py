"""
ui/notas_panel.py
Panel de Notas y Pendientes — 2 pestañas:
  • Por Pedir / Resurtido
  • Tareas Operativas
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QTabWidget, QCheckBox,
    QSizePolicy,
)

from database.notas_repo import obtener_notas, insertar_nota, marcar_nota, eliminar_nota
from models.nota import Nota


# ---------------------------------------------------------------------------
# Widget de una nota individual
# ---------------------------------------------------------------------------

class _FilaNota(QFrame):
    def __init__(self, nota: Nota, on_toggle, on_delete, parent=None):
        super().__init__(parent)
        self._nota = nota
        self.setObjectName("filaNota")
        self._aplicar_estilo()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        self._chk = QCheckBox()
        self._chk.setChecked(nota.completado)
        self._chk.setFixedSize(18, 18)
        self._chk.toggled.connect(lambda v: on_toggle(nota.id, v))
        lay.addWidget(self._chk)

        lbl_texto = QLabel(nota.texto)
        lbl_texto.setWordWrap(True)
        lbl_texto.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        if nota.completado:
            lbl_texto.setStyleSheet(
                "color:#9CA3AF; text-decoration:line-through; font-size:12px;"
                "background:transparent; border:none;"
            )
        else:
            lbl_texto.setStyleSheet(
                "color:#1E293B; font-size:12px;"
                "background:transparent; border:none;"
            )
        lay.addWidget(lbl_texto)

        lbl_fecha = QLabel(nota.fecha_creacion[:10])
        lbl_fecha.setStyleSheet(
            "color:#94A3B8; font-size:10px; background:transparent; border:none;"
        )
        lbl_fecha.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(lbl_fecha)

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(22, 22)
        btn_del.setStyleSheet(
            "QPushButton { border:none; color:#9CA3AF; font-size:12px; background:transparent; }"
            "QPushButton:hover { color:#DC2626; }"
        )
        btn_del.clicked.connect(lambda: on_delete(nota.id))
        lay.addWidget(btn_del)

    def _aplicar_estilo(self):
        if self._nota.completado:
            self.setStyleSheet(
                "QFrame#filaNota { background:#F9FAFB; border:1px solid #E5E7EB;"
                "border-radius:6px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#filaNota { background:white; border:1px solid #E2E8F0;"
                "border-radius:6px; }"
            )


# ---------------------------------------------------------------------------
# Panel de una pestaña (resurtido o tarea)
# ---------------------------------------------------------------------------

class _TabNotas(QWidget):
    def __init__(self, tipo: str, placeholder: str, parent=None):
        super().__init__(parent)
        self._tipo = tipo
        self._placeholder = placeholder
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 12, 0, 0)
        root.setSpacing(10)

        # Fila de entrada
        fila = QHBoxLayout()
        fila.setSpacing(8)

        self._campo = QLineEdit()
        self._campo.setPlaceholderText(self._placeholder)
        self._campo.setFixedHeight(36)
        self._campo.setStyleSheet(
            "QLineEdit { border:1px solid #CBD5E1; border-radius:6px; padding:0 12px;"
            "font-size:12px; background:white; }"
            "QLineEdit:focus { border:2px solid #2563EB; }"
        )
        self._campo.returnPressed.connect(self._on_agregar)

        btn_add = QPushButton("+ Agregar")
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border:none;"
            "border-radius:6px; font-size:12px; font-weight:bold; padding:0 16px; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btn_add.clicked.connect(self._on_agregar)

        fila.addWidget(self._campo)
        fila.addWidget(btn_add)
        root.addLayout(fila)

        # Contador
        self._lbl_count = QLabel()
        self._lbl_count.setStyleSheet("color:#64748B; font-size:11px;")
        root.addWidget(self._lbl_count)

        # Área de scroll con la lista
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")

        self._contenedor = QWidget()
        self._contenedor.setStyleSheet("background: transparent;")
        self._lista_lay = QVBoxLayout(self._contenedor)
        self._lista_lay.setContentsMargins(0, 0, 0, 0)
        self._lista_lay.setSpacing(6)
        self._lista_lay.addStretch()

        self._scroll.setWidget(self._contenedor)
        root.addWidget(self._scroll)

    def refresh(self):
        # Limpiar lista actual
        while self._lista_lay.count() > 1:   # conservar el stretch al final
            item = self._lista_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        notas = obtener_notas(self._tipo)
        for nota in notas:
            fila = _FilaNota(nota, self._on_toggle, self._on_delete)
            self._lista_lay.insertWidget(self._lista_lay.count() - 1, fila)

        pendientes = sum(1 for n in notas if not n.completado)
        total = len(notas)
        self._lbl_count.setText(
            f"{pendientes} pendiente{'s' if pendientes != 1 else ''}  •  {total} en total"
        )

    def _on_agregar(self):
        texto = self._campo.text().strip()
        if not texto:
            return
        insertar_nota(Nota(texto=texto, tipo=self._tipo))
        self._campo.clear()
        self.refresh()

    def _on_toggle(self, nota_id: int, completado: bool):
        marcar_nota(nota_id, completado)
        self.refresh()

    def _on_delete(self, nota_id: int):
        eliminar_nota(nota_id)
        self.refresh()


# ---------------------------------------------------------------------------
# Panel principal con QTabWidget
# ---------------------------------------------------------------------------

class NotasPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        # Título
        titulo = QLabel("Notas y Pendientes")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)
        root.addWidget(titulo)

        # Tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background: #F8FAFC;
                padding: 12px;
            }
            QTabBar::tab {
                background: #F1F5F9;
                color: #475569;
                border: 1px solid #E2E8F0;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
                min-width: 160px;
            }
            QTabBar::tab:selected {
                background: white;
                color: #1E293B;
                border-bottom: 2px solid white;
            }
            QTabBar::tab:hover:!selected {
                background: #E2E8F0;
            }
        """)

        self._tab_resurtido = _TabNotas(
            tipo="resurtido",
            placeholder="Ej: Cascos XTR-M70 talla M × 5…",
        )
        self._tab_tareas = _TabNotas(
            tipo="tarea",
            placeholder="Ej: Revisar cuentas de Addi del mes…",
        )

        tabs.addTab(self._tab_resurtido, "📦  Por Pedir / Resurtido")
        tabs.addTab(self._tab_tareas,    "✅  Tareas Operativas")

        root.addWidget(tabs)

    def refresh(self):
        self._tab_resurtido.refresh()
        self._tab_tareas.refresh()
