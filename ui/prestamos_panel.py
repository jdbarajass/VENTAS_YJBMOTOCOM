"""
ui/prestamos_panel.py
Panel de gestión de préstamos a locales/almacenes.
Permite registrar, hacer seguimiento y cerrar préstamos de productos.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QLineEdit, QDateEdit, QMessageBox, QCheckBox, QSizePolicy,
    QDialog, QComboBox, QDialogButtonBox,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont, QColor

from controllers.prestamos_controller import PrestamosController
from models.prestamo import Prestamo
from utils.formatters import fecha_corta


# ──────────────────────────────────────────────────────────────────────────────
# Diálogo de edición de préstamo
# ──────────────────────────────────────────────────────────────────────────────

class EditPrestamoDialog(QDialog):
    """Diálogo sencillo para editar los campos de un préstamo."""

    prestamo_actualizado = Signal(object)

    def __init__(self, prestamo: Prestamo, ctrl: PrestamosController,
                 parent=None) -> None:
        super().__init__(parent)
        self._p = prestamo
        self._ctrl = ctrl
        self.setWindowTitle("Editar Préstamo")
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(12)

        titulo = QLabel("Editar Préstamo")
        f = QFont(); f.setPointSize(13); f.setBold(True)
        titulo.setFont(f)
        lay.addWidget(titulo)

        # Fecha
        fila_fecha = QHBoxLayout()
        fila_fecha.addWidget(QLabel("Fecha:"))
        self.campo_fecha = QDateEdit()
        self.campo_fecha.setCalendarPopup(True)
        self.campo_fecha.setDisplayFormat("dd/MM/yyyy")
        self.campo_fecha.setDate(QDate(self._p.fecha.year,
                                       self._p.fecha.month,
                                       self._p.fecha.day))
        self.campo_fecha.setFixedHeight(32)
        self.campo_fecha.setStyleSheet(self._campo_style())
        fila_fecha.addWidget(self.campo_fecha)
        fila_fecha.addStretch()
        lay.addLayout(fila_fecha)

        # Producto
        lay.addWidget(QLabel("Producto:"))
        self.campo_producto = QLineEdit(self._p.producto)
        self.campo_producto.setFixedHeight(32)
        self.campo_producto.setStyleSheet(self._campo_style())
        lay.addWidget(self.campo_producto)

        # Almacén
        lay.addWidget(QLabel("Almacén / Local:"))
        self.campo_almacen = QLineEdit(self._p.almacen)
        self.campo_almacen.setFixedHeight(32)
        self.campo_almacen.setStyleSheet(self._campo_style())
        lay.addWidget(self.campo_almacen)

        # Observaciones
        lay.addWidget(QLabel("Observaciones:"))
        self.campo_obs = QLineEdit(self._p.observaciones or "")
        self.campo_obs.setFixedHeight(32)
        self.campo_obs.setStyleSheet(self._campo_style())
        lay.addWidget(self.campo_obs)

        # Estado
        lay.addWidget(QLabel("Estado:"))
        self.combo_estado = QComboBox()
        self.combo_estado.setFixedHeight(32)
        self.combo_estado.addItems(["pendiente", "devuelto", "cobrado"])
        self.combo_estado.setCurrentText(self._p.estado)
        self.combo_estado.setStyleSheet(self._campo_style())
        lay.addWidget(self.combo_estado)

        # Botones
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Save).setText("Guardar cambios")
        btns.button(QDialogButtonBox.Cancel).setText("Cancelar")
        btns.button(QDialogButtonBox.Save).setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:5px;"
            "padding:0 16px; font-weight:bold; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btns.accepted.connect(self._on_guardar)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _on_guardar(self) -> None:
        producto = self.campo_producto.text().strip()
        almacen  = self.campo_almacen.text().strip()
        if not producto:
            QMessageBox.warning(self, "Dato requerido", "Ingresa el nombre del producto.")
            return
        if not almacen:
            QMessageBox.warning(self, "Dato requerido", "Ingresa el nombre del almacén.")
            return

        qd = self.campo_fecha.date()
        self._p.fecha        = date(qd.year(), qd.month(), qd.day())
        self._p.producto     = producto
        self._p.almacen      = almacen
        self._p.observaciones = self.campo_obs.text().strip()
        self._p.estado       = self.combo_estado.currentText()

        try:
            self._ctrl.editar(self._p)
            self.prestamo_actualizado.emit(self._p)
            self.accept()
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    @staticmethod
    def _campo_style() -> str:
        return (
            "QLineEdit, QDateEdit, QComboBox {"
            "border:1px solid #D1D5DB; border-radius:6px; padding:0 8px; background:white; }"
            "QLineEdit:focus, QDateEdit:focus, QComboBox:focus {"
            "border:2px solid #2563EB; }"
        )


# Estado → (texto, color fondo, color texto)
ESTADO_ESTILO = {
    "pendiente": ("#FEF3C7", "#92400E", "PENDIENTE"),
    "devuelto":  ("#DCFCE7", "#15803D", "DEVUELTO"),
    "cobrado":   ("#DBEAFE", "#1D4ED8", "COBRADO"),
}


class PrestamosPanel(QWidget):
    """Vista completa de préstamos a locales."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = PrestamosController()
        self._prestamos: list = []
        self._build_ui()
        self._cargar_datos()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(14)

        root.addLayout(self._barra_titulo())
        root.addWidget(self._panel_formulario())
        root.addWidget(self._panel_alerta())
        root.addWidget(self._panel_tabla(), stretch=1)

    # ---- Título ----

    def _barra_titulo(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Préstamos a Locales")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)

        desc = QLabel("Lleva el control de productos prestados a otros almacenes.")
        desc.setStyleSheet("color: #6B7280; font-size: 12px;")

        self.chk_solo_pendientes = QCheckBox("Solo pendientes")
        self.chk_solo_pendientes.setChecked(True)
        self.chk_solo_pendientes.setStyleSheet("color: #374151; font-size: 12px;")
        self.chk_solo_pendientes.toggled.connect(lambda _: self._cargar_datos())

        lay.addWidget(titulo)
        lay.addSpacing(12)
        lay.addWidget(desc)
        lay.addStretch()
        lay.addWidget(self.chk_solo_pendientes)
        return lay

    # ---- Formulario de registro ----

    def _panel_formulario(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("formFrame")
        frame.setStyleSheet(
            "QFrame#formFrame { background:#F0F9FF; border:1px solid #BAE6FD;"
            "border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)

        lbl = QLabel("Registrar nuevo préstamo")
        f = QFont(); f.setPointSize(11); f.setBold(True)
        lbl.setFont(f)
        lbl.setStyleSheet("color: #0369A1; background: transparent; border: none;")
        lay.addWidget(lbl)

        fila = QHBoxLayout()
        fila.setSpacing(10)

        # Fecha
        lbl_f = QLabel("Fecha:")
        lbl_f.setStyleSheet("color:#374151; font-size:12px; background:transparent; border:none;")
        self.campo_fecha = QDateEdit()
        self.campo_fecha.setCalendarPopup(True)
        self.campo_fecha.setDate(QDate.currentDate())
        self.campo_fecha.setDisplayFormat("dd/MM/yyyy")
        self.campo_fecha.setFixedHeight(34)
        self.campo_fecha.setFixedWidth(130)
        self.campo_fecha.setStyleSheet(self._estilo_campo())

        # Producto
        lbl_p = QLabel("Producto:")
        lbl_p.setStyleSheet("color:#374151; font-size:12px; background:transparent; border:none;")
        self.campo_producto = QLineEdit()
        self.campo_producto.setPlaceholderText("Ej: Casco X-Sport, Guantes talla M…")
        self.campo_producto.setFixedHeight(34)
        self.campo_producto.setStyleSheet(self._estilo_campo())

        # Almacén
        lbl_a = QLabel("Almacén:")
        lbl_a.setStyleSheet("color:#374151; font-size:12px; background:transparent; border:none;")
        self.campo_almacen = QLineEdit()
        self.campo_almacen.setPlaceholderText("Nombre del local o almacén")
        self.campo_almacen.setFixedHeight(34)
        self.campo_almacen.setFixedWidth(180)
        self.campo_almacen.setStyleSheet(self._estilo_campo())

        # Observaciones
        lbl_o = QLabel("Observaciones:")
        lbl_o.setStyleSheet("color:#374151; font-size:12px; background:transparent; border:none;")
        self.campo_obs = QLineEdit()
        self.campo_obs.setPlaceholderText("Precio acordado, condiciones, etc. (opcional)")
        self.campo_obs.setFixedHeight(34)
        self.campo_obs.setStyleSheet(self._estilo_campo())

        # Botón
        btn_registrar = QPushButton("Registrar")
        btn_registrar.setFixedHeight(34)
        btn_registrar.setFixedWidth(100)
        btn_registrar.setStyleSheet(
            "QPushButton { background:#0284C7; color:white; border-radius:6px;"
            "font-weight:bold; font-size:12px; border:none; }"
            "QPushButton:hover { background:#0369A1; }"
            "QPushButton:pressed { background:#075985; }"
        )
        btn_registrar.clicked.connect(self._on_registrar)

        fila.addWidget(lbl_f)
        fila.addWidget(self.campo_fecha)
        fila.addWidget(lbl_p)
        fila.addWidget(self.campo_producto, stretch=2)
        fila.addWidget(lbl_a)
        fila.addWidget(self.campo_almacen)
        fila.addWidget(lbl_o)
        fila.addWidget(self.campo_obs, stretch=2)
        fila.addWidget(btn_registrar)
        lay.addLayout(fila)
        return frame

    # ---- Panel de alerta pendientes ----

    def _panel_alerta(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("alertaFrame")
        frame.setStyleSheet(
            "QFrame#alertaFrame { background:#FEF9C3; border:1px solid #FDE047;"
            "border-radius:8px; }"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 8, 16, 8)

        self.lbl_alerta = QLabel("Sin préstamos pendientes.")
        self.lbl_alerta.setStyleSheet(
            "color:#713F12; font-size:13px; font-weight:bold;"
            "background:transparent; border:none;"
        )
        lay.addWidget(self.lbl_alerta)
        lay.addStretch()
        return frame

    # ---- Tabla de préstamos ----

    def _panel_tabla(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)

        # Cols: ID(oculto) | Fecha | Días | Producto | Almacén | Observaciones | Estado | Acciones
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Fecha", "Días", "Producto", "Almacén", "Observaciones", "Estado", "Acciones"
        ])
        self.tabla.setColumnHidden(0, True)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setStyleSheet("""
            QTableWidget { border:none; font-size:12px; }
            QTableWidget::item { padding:4px 8px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:11px; padding:6px; border:none;
            }
            QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }
        """)

        hh = self.tabla.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.Fixed);   self.tabla.setColumnWidth(1, 90)
        hh.setSectionResizeMode(2, QHeaderView.Fixed);   self.tabla.setColumnWidth(2, 68)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);   self.tabla.setColumnWidth(4, 160)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        hh.setSectionResizeMode(6, QHeaderView.Fixed);   self.tabla.setColumnWidth(6, 100)
        hh.setSectionResizeMode(7, QHeaderView.Fixed);   self.tabla.setColumnWidth(7, 260)

        lay.addWidget(self.tabla)
        return frame

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------

    def _cargar_datos(self) -> None:
        """Recarga la tabla según el filtro activo."""
        if self.chk_solo_pendientes.isChecked():
            self._prestamos = self._ctrl.cargar_pendientes()
        else:
            self._prestamos = self._ctrl.cargar_todos()
        self._poblar_tabla()
        self._actualizar_alerta()

    def _poblar_tabla(self) -> None:
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(self._prestamos))

        hoy = date.today()
        for row, p in enumerate(self._prestamos):
            self.tabla.setRowHeight(row, 36)

            self.tabla.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self._celda(row, 1, fecha_corta(p.fecha), Qt.AlignCenter)

            # Días transcurridos
            dias = max(0, (hoy - p.fecha).days)
            self.tabla.setCellWidget(row, 2, self._badge_dias(dias, p.estado))

            self._celda(row, 3, p.producto)
            self._celda(row, 4, p.almacen, Qt.AlignCenter)
            self._celda(row, 5, p.observaciones or "")

            # Estado con badge de color
            self.tabla.setCellWidget(row, 6, self._badge_estado(p.estado))

            # Botones de acción
            self.tabla.setCellWidget(row, 7, self._widget_acciones(p.id, p.estado))

    def _actualizar_alerta(self) -> None:
        """Actualiza el banner de alerta de pendientes."""
        pendientes = [p for p in self._prestamos if p.estado == "pendiente"]
        if not self.chk_solo_pendientes.isChecked():
            pendientes = self._ctrl.cargar_pendientes()

        n = len(pendientes)
        if n == 0:
            self.lbl_alerta.setText("Sin préstamos pendientes. Todo en orden.")
        elif n == 1:
            self.lbl_alerta.setText(
                "1 préstamo pendiente por cobrar o recuperar — no olvides ir a buscarlo."
            )
        else:
            self.lbl_alerta.setText(
                f"{n} préstamos pendientes por cobrar o recuperar — no olvides ir a buscarlos."
            )

    # ------------------------------------------------------------------
    # Widgets de celda
    # ------------------------------------------------------------------

    def _badge_dias(self, dias: int, estado: str) -> QWidget:
        """Badge con días transcurridos; color según urgencia (solo aplica a pendientes)."""
        if estado != "pendiente":
            bg, fg = "#F1F5F9", "#64748B"
        elif dias <= 7:
            bg, fg = "#DCFCE7", "#15803D"
        elif dias <= 30:
            bg, fg = "#FEF3C7", "#92400E"
        else:
            bg, fg = "#FEE2E2", "#DC2626"

        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lbl = QLabel(f"{dias}d")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:4px;"
            f"font-size:11px; font-weight:bold; padding:2px 6px;"
        )
        lay.addWidget(lbl)
        return w

    def _badge_estado(self, estado: str) -> QWidget:
        bg, fg, txt = ESTADO_ESTILO.get(estado, ("#F3F4F6", "#374151", estado.upper()))
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 4, 4, 4)
        lbl = QLabel(txt)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:4px;"
            f"font-size:10px; font-weight:bold; padding:2px 8px;"
        )
        lay.addWidget(lbl)
        return w

    def _widget_acciones(self, prestamo_id: int, estado: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 3, 4, 3)
        lay.setSpacing(5)

        if estado == "pendiente":
            btn_dev = QPushButton("Devuelto")
            btn_dev.setFixedHeight(26)
            btn_dev.setStyleSheet(
                "QPushButton { background:#DCFCE7; color:#15803D; border:1px solid #86EFAC;"
                "border-radius:4px; font-size:11px; font-weight:bold; padding:0 6px; }"
                "QPushButton:hover { background:#BBF7D0; }"
            )
            btn_dev.clicked.connect(
                lambda _, pid=prestamo_id: self._on_devuelto(pid)
            )

            btn_cob = QPushButton("Cobrado")
            btn_cob.setFixedHeight(26)
            btn_cob.setStyleSheet(
                "QPushButton { background:#DBEAFE; color:#1D4ED8; border:1px solid #93C5FD;"
                "border-radius:4px; font-size:11px; font-weight:bold; padding:0 6px; }"
                "QPushButton:hover { background:#BFDBFE; }"
            )
            btn_cob.clicked.connect(
                lambda _, pid=prestamo_id: self._on_cobrado(pid)
            )

            lay.addWidget(btn_dev)
            lay.addWidget(btn_cob)

        # Editar — siempre disponible
        btn_edit = QPushButton("Editar")
        btn_edit.setFixedHeight(26)
        btn_edit.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#2563EB; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn_edit.clicked.connect(lambda _, pid=prestamo_id: self._on_editar(pid))
        lay.addWidget(btn_edit)

        btn_del = QPushButton("Borrar")
        btn_del.setFixedHeight(26)
        btn_del.setStyleSheet(
            "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn_del.clicked.connect(lambda _, pid=prestamo_id: self._on_eliminar(pid))
        lay.addWidget(btn_del)
        lay.addStretch()
        return w

    def _celda(self, row: int, col: int, texto: str,
               alin: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alin)
        self.tabla.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_registrar(self) -> None:
        producto = self.campo_producto.text().strip()
        almacen  = self.campo_almacen.text().strip()
        obs      = self.campo_obs.text().strip()
        qd       = self.campo_fecha.date()
        fecha    = date(qd.year(), qd.month(), qd.day())

        if not producto:
            QMessageBox.warning(self, "Dato requerido", "Ingresa el nombre del producto.")
            self.campo_producto.setFocus()
            return
        if not almacen:
            QMessageBox.warning(self, "Dato requerido", "Ingresa el nombre del almacén.")
            self.campo_almacen.setFocus()
            return

        try:
            p = self._ctrl.registrar(producto, almacen, fecha, obs)
            # Limpiar campos de texto (no la fecha, es más útil mantenerla)
            self.campo_producto.clear()
            self.campo_almacen.clear()
            self.campo_obs.clear()
            self.campo_producto.setFocus()
            self._cargar_datos()
            QMessageBox.information(
                self, "Préstamo registrado",
                f"Préstamo de <b>{p.producto}</b> a <b>{p.almacen}</b> registrado.\n"
                "Aparecerá en la lista como pendiente."
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _on_editar(self, prestamo_id: int) -> None:
        p = next((x for x in self._prestamos if x.id == prestamo_id), None)
        if p is None:
            return
        dlg = EditPrestamoDialog(p, self._ctrl, self)
        dlg.prestamo_actualizado.connect(lambda _: self._cargar_datos())
        dlg.exec()

    def _on_devuelto(self, prestamo_id: int) -> None:
        p = next((x for x in self._prestamos if x.id == prestamo_id), None)
        nombre = f"{p.producto} → {p.almacen}" if p else f"id {prestamo_id}"
        resp = QMessageBox.question(
            self, "Confirmar devolución",
            f"¿Marcar como devuelto?\n<b>{nombre}</b>",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if resp == QMessageBox.Yes:
            self._ctrl.marcar_devuelto(prestamo_id)
            self._cargar_datos()

    def _on_cobrado(self, prestamo_id: int) -> None:
        p = next((x for x in self._prestamos if x.id == prestamo_id), None)
        nombre = f"{p.producto} → {p.almacen}" if p else f"id {prestamo_id}"
        resp = QMessageBox.question(
            self, "Confirmar cobro",
            f"¿Marcar como cobrado (lo vendieron y pagaron)?\n<b>{nombre}</b>",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if resp == QMessageBox.Yes:
            self._ctrl.marcar_cobrado(prestamo_id)
            self._cargar_datos()

    def _on_eliminar(self, prestamo_id: int) -> None:
        p = next((x for x in self._prestamos if x.id == prestamo_id), None)
        nombre = f"{p.producto} → {p.almacen}" if p else f"id {prestamo_id}"
        resp = QMessageBox.question(
            self, "Eliminar préstamo",
            f"¿Eliminar este registro del historial?\n<b>{nombre}</b>\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self._ctrl.eliminar(prestamo_id)
            self._cargar_datos()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _estilo_campo() -> str:
        return (
            "QLineEdit, QDateEdit {"
            "border:1px solid #D1D5DB; border-radius:6px;"
            "padding:0 8px; background:white; }"
            "QLineEdit:focus, QDateEdit:focus {"
            "border:2px solid #0284C7; }"
        )

    def refresh(self) -> None:
        self._cargar_datos()
