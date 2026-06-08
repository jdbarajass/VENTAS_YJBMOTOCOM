"""
ui/notas_panel.py
Panel de Notas y Pendientes — 2 pestañas:
  • Por Pedir / Resurtido
  • Tareas Operativas
Incluye fecha límite opcional y badge de vencimiento por nota.
"""

from datetime import date

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QTabWidget, QCheckBox,
    QSizePolicy, QDialog, QFormLayout, QDateEdit, QDialogButtonBox,
)

from database.notas_repo import (
    obtener_notas, insertar_nota, marcar_nota,
    eliminar_nota, actualizar_nota,
)
from models.nota import Nota
from ui.styles import es_modo_oscuro


# ---------------------------------------------------------------------------
# Diálogo de agregar / editar nota
# ---------------------------------------------------------------------------

class _DialogoNota(QDialog):
    """Diálogo para crear o editar una nota con texto y fecha límite opcional."""

    def __init__(self, texto: str = "", fecha_limite: str | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nota / Pendiente")
        self.setMinimumWidth(380)

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(20, 16, 20, 16)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        _estilo = (
            "QLineEdit, QDateEdit { border-radius:6px; padding:0 10px; font-size:12px; height:32px; }"
            "QLineEdit:focus, QDateEdit:focus { border:2px solid #2563EB; }"
        )

        self._campo_texto = QLineEdit(texto)
        self._campo_texto.setPlaceholderText("Texto del pendiente…")
        self._campo_texto.setFixedHeight(34)
        self._campo_texto.setStyleSheet(_estilo)
        form.addRow("Texto:", self._campo_texto)

        self._fecha_edit = QDateEdit()
        self._fecha_edit.setCalendarPopup(True)
        self._fecha_edit.setFixedHeight(34)
        self._fecha_edit.setStyleSheet(_estilo)
        self._fecha_edit.setSpecialValueText("Sin fecha límite")
        self._fecha_edit.setMinimumDate(QDate.currentDate())

        if fecha_limite:
            try:
                d = date.fromisoformat(fecha_limite)
                self._fecha_edit.setDate(QDate(d.year, d.month, d.day))
                self._tiene_fecha = True
            except ValueError:
                self._fecha_edit.setDate(QDate(2000, 1, 1))
                self._tiene_fecha = False
        else:
            self._fecha_edit.setDate(QDate(2000, 1, 1))
            self._tiene_fecha = False

        self._chk_fecha = QCheckBox("Establecer fecha límite")
        self._chk_fecha.setChecked(self._tiene_fecha)
        self._chk_fecha.setStyleSheet("font-size:12px;")
        self._fecha_edit.setEnabled(self._tiene_fecha)
        self._chk_fecha.toggled.connect(self._fecha_edit.setEnabled)

        form.addRow("", self._chk_fecha)
        form.addRow("Vence el:", self._fecha_edit)

        lay.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    @property
    def texto(self) -> str:
        return self._campo_texto.text().strip()

    @property
    def fecha_limite(self) -> str | None:
        if not self._chk_fecha.isChecked():
            return None
        d = self._fecha_edit.date()
        return f"{d.year():04d}-{d.month():02d}-{d.day():02d}"


# ---------------------------------------------------------------------------
# Widget de una nota individual
# ---------------------------------------------------------------------------

class _FilaNota(QFrame):
    def __init__(self, nota: Nota, on_toggle, on_delete, on_edit, parent=None):
        super().__init__(parent)
        self._nota = nota
        self.setObjectName("filaNota")
        self._aplicar_estilo()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(8)

        self._chk = QCheckBox()
        self._chk.setChecked(nota.completado)
        self._chk.setFixedSize(18, 18)
        self._chk.toggled.connect(lambda v: on_toggle(nota.id, v))
        lay.addWidget(self._chk)

        # Columna central: texto + badge vencimiento
        col = QVBoxLayout()
        col.setSpacing(2)
        col.setContentsMargins(0, 0, 0, 0)

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
                "color:#1E293B; font-size:12px; background:transparent; border:none;"
            )
        col.addWidget(lbl_texto)

        # Badge de fecha límite
        if nota.fecha_limite and not nota.completado:
            dias = nota.dias_restantes
            if dias is not None:
                if dias < 0:
                    badge_txt = f"VENCIDA (hace {abs(dias)} día{'s' if abs(dias)!=1 else ''})"
                    badge_color = "#FEE2E2"; badge_text_color = "#DC2626"
                elif dias == 0:
                    badge_txt = "Vence HOY"
                    badge_color = "#FEF3C7"; badge_text_color = "#D97706"
                elif dias <= 3:
                    badge_txt = f"Vence en {dias} día{'s' if dias!=1 else ''}"
                    badge_color = "#FEF3C7"; badge_text_color = "#D97706"
                else:
                    badge_txt = f"Vence {nota.fecha_limite}"
                    badge_color = "#EFF6FF"; badge_text_color = "#2563EB"

                lbl_badge = QLabel(badge_txt)
                lbl_badge.setStyleSheet(
                    f"color:{badge_text_color}; background:{badge_color};"
                    "border-radius:3px; padding:1px 6px; font-size:10px; font-weight:bold;"
                    "border:none;"
                )
                col.addWidget(lbl_badge)

        lay.addLayout(col)

        # Fecha creación
        lbl_fecha = QLabel(nota.fecha_creacion[:10])
        lbl_fecha.setStyleSheet(
            "color:#94A3B8; font-size:10px; background:transparent; border:none;"
        )
        lbl_fecha.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(lbl_fecha)

        btn_edit = QPushButton("✏")
        btn_edit.setFixedSize(26, 24)
        btn_edit.setToolTip("Editar nota")
        btn_edit.setStyleSheet(
            "QPushButton { border:1px solid #BFDBFE; color:#2563EB;"
            "background:#EFF6FF; border-radius:4px; font-size:11px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn_edit.clicked.connect(lambda: on_edit(nota))
        lay.addWidget(btn_edit)

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(26, 24)
        btn_del.setToolTip("Eliminar nota")
        btn_del.setStyleSheet(
            "QPushButton { border:1px solid #FECACA; color:#DC2626;"
            "background:#FEF2F2; border-radius:4px; font-size:11px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn_del.clicked.connect(lambda: on_delete(nota.id))
        lay.addWidget(btn_del)

    def _aplicar_estilo(self):
        dark = es_modo_oscuro()
        if self._nota.vencida:
            bg = "#2D0808" if dark else "#FFF5F5"
            border = "#7F1D1D" if dark else "#FECACA"
        elif self._nota.completado:
            bg = "#1E293B" if dark else "#F9FAFB"
            border = "#334155" if dark else "#E5E7EB"
        else:
            bg = "#162032" if dark else "#FFFFFF"
            border = "#2D3748" if dark else "#E2E8F0"
        self.setStyleSheet(
            f"QFrame#filaNota {{ background:{bg}; border:1px solid {border};"
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

        # Botón agregar
        fila = QHBoxLayout()
        fila.setSpacing(8)

        self._campo = QLineEdit()
        self._campo.setPlaceholderText(self._placeholder)
        self._campo.setFixedHeight(36)
        self._campo.setStyleSheet(
            "QLineEdit { border-radius:6px; padding:0 12px; font-size:12px; }"
            "QLineEdit:focus { border:2px solid #2563EB; }"
        )
        self._campo.returnPressed.connect(self._on_agregar_rapido)

        btn_add = QPushButton("+ Agregar")
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border:none;"
            "border-radius:6px; font-size:12px; font-weight:bold; padding:0 16px; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btn_add.clicked.connect(self._on_agregar_rapido)

        btn_add_fecha = QPushButton("+ Con fecha")
        btn_add_fecha.setFixedHeight(36)
        btn_add_fecha.setStyleSheet(
            "QPushButton { background:#0D9488; color:white; border:none;"
            "border-radius:6px; font-size:12px; font-weight:bold; padding:0 14px; }"
            "QPushButton:hover { background:#0F766E; }"
        )
        btn_add_fecha.setToolTip("Agregar nota con fecha límite")
        btn_add_fecha.clicked.connect(self._on_agregar_con_fecha)

        fila.addWidget(self._campo)
        fila.addWidget(btn_add)
        fila.addWidget(btn_add_fecha)
        root.addLayout(fila)

        # Contador
        self._lbl_count = QLabel()
        self._lbl_count.setStyleSheet("color:#64748B; font-size:11px;")
        root.addWidget(self._lbl_count)

        # Área de scroll
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
        while self._lista_lay.count() > 1:
            item = self._lista_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        notas = obtener_notas(self._tipo)
        for nota in notas:
            fila = _FilaNota(nota, self._on_toggle, self._on_delete, self._on_edit)
            self._lista_lay.insertWidget(self._lista_lay.count() - 1, fila)

        pendientes = sum(1 for n in notas if not n.completado)
        vencidas = sum(1 for n in notas if n.vencida)
        total = len(notas)
        texto = f"{pendientes} pendiente{'s' if pendientes!=1 else ''}  •  {total} en total"
        if vencidas:
            texto += f"  •  ⚠ {vencidas} vencida{'s' if vencidas!=1 else ''}"
        self._lbl_count.setText(texto)

    def _on_agregar_rapido(self):
        texto = self._campo.text().strip()
        if not texto:
            return
        insertar_nota(Nota(texto=texto, tipo=self._tipo))
        self._campo.clear()
        self.refresh()

    def _on_agregar_con_fecha(self):
        texto_pre = self._campo.text().strip()
        dlg = _DialogoNota(texto=texto_pre, parent=self)
        if dlg.exec() == QDialog.Accepted and dlg.texto:
            insertar_nota(Nota(
                texto=dlg.texto,
                tipo=self._tipo,
                fecha_limite=dlg.fecha_limite,
            ))
            self._campo.clear()
            self.refresh()

    def _on_toggle(self, nota_id: int, completado: bool):
        marcar_nota(nota_id, completado)
        self.refresh()

    def _on_edit(self, nota: Nota):
        dlg = _DialogoNota(
            texto=nota.texto,
            fecha_limite=nota.fecha_limite,
            parent=self,
        )
        if dlg.exec() == QDialog.Accepted and dlg.texto:
            actualizar_nota(nota.id, dlg.texto, dlg.fecha_limite)
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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenido = QWidget()
        root = QVBoxLayout(contenido)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        titulo = QLabel("Notas y Pendientes")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)
        root.addWidget(titulo)

        tabs = QTabWidget()

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
        root.addWidget(tabs, stretch=1)

        scroll.setWidget(contenido)
        outer.addWidget(scroll)

    def refresh(self):
        self._tab_resurtido.refresh()
        self._tab_tareas.refresh()
