"""
ui/facturas_panel.py
Panel de gestión de facturas y recibos pendientes de pago.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMessageBox, QCheckBox,
    QDateEdit, QSizePolicy, QDialog, QDialogButtonBox, QScrollArea,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont, QColor

from controllers.facturas_controller import FacturasController
from models.factura import Factura
from ui.venta_form import MoneyLineEdit
from utils.formatters import cop


_ESTADO_ESTILO = {
    "pendiente": ("#FEF3C7", "#92400E", "PENDIENTE"),
    "pagada":    ("#DCFCE7", "#15803D", "PAGADA"),
}


class AbonosDialog(QDialog):
    """Diálogo para registrar y ver abonos de una factura."""

    abono_registrado = Signal()

    def __init__(self, factura: Factura, ctrl: FacturasController, parent=None) -> None:
        super().__init__(parent)
        self._factura = factura
        self._ctrl = ctrl
        self.setWindowTitle(f"Abonos — {factura.descripcion[:50]}")
        self.setMinimumWidth(520)
        self._build_ui()
        self._cargar_abonos()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        # Encabezado
        lbl_titulo = QLabel(f"Factura: <b>{self._factura.descripcion}</b>")
        lbl_titulo.setWordWrap(True)
        lbl_titulo.setStyleSheet("font-size:12px; color:#374151;")
        lay.addWidget(lbl_titulo)

        self._lbl_resumen = QLabel("")
        self._lbl_resumen.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#0369A1;"
            "background:#EFF6FF; border-radius:5px; padding:6px 10px;"
        )
        lay.addWidget(self._lbl_resumen)

        # Lista de abonos existentes
        self._lista_abonos = QWidget()
        self._lista_abonos.setStyleSheet("background:transparent;")
        self._lay_lista = QVBoxLayout(self._lista_abonos)
        self._lay_lista.setContentsMargins(0, 0, 0, 0)
        self._lay_lista.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidget(self._lista_abonos)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        scroll.setFrameShape(QFrame.NoFrame)
        lay.addWidget(scroll)

        # Formulario nuevo abono
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#E5E7EB;")
        lay.addWidget(sep)

        lbl_nuevo = QLabel("Registrar nuevo abono")
        f = QFont(); f.setBold(True); f.setPointSize(10)
        lbl_nuevo.setFont(f)
        lbl_nuevo.setStyleSheet("color:#374151;")
        lay.addWidget(lbl_nuevo)

        fila = QHBoxLayout(); fila.setSpacing(8)

        self._f_monto = MoneyLineEdit()
        self._f_monto.setPlaceholderText("Monto abono")
        self._f_monto.setFixedHeight(30)
        self._f_monto.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:4px; padding:0 8px; }"
        )

        self._f_fecha = QDateEdit()
        self._f_fecha.setDate(QDate.currentDate())
        self._f_fecha.setCalendarPopup(True)
        self._f_fecha.setFixedHeight(30); self._f_fecha.setFixedWidth(130)
        self._f_fecha.setDisplayFormat("dd/MM/yyyy")
        self._f_fecha.setStyleSheet(
            "QDateEdit { border:1px solid #D1D5DB; border-radius:4px; padding:0 8px; }"
        )

        self._f_notas = QLineEdit()
        self._f_notas.setPlaceholderText("Notas (opcional)")
        self._f_notas.setFixedHeight(30)
        self._f_notas.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:4px; padding:0 8px; }"
        )

        btn_abonar = QPushButton("Registrar abono")
        btn_abonar.setFixedHeight(30)
        btn_abonar.setStyleSheet(
            "QPushButton { background:#0284C7; color:white; border-radius:4px;"
            "padding:0 14px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#0369A1; }"
        )
        btn_abonar.clicked.connect(self._on_abonar)

        fila.addWidget(self._f_monto, stretch=2)
        fila.addWidget(self._f_fecha)
        fila.addWidget(self._f_notas, stretch=2)
        fila.addWidget(btn_abonar)
        lay.addLayout(fila)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedHeight(30)
        btn_cerrar.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:4px;"
            "padding:0 14px; background:white; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_cerrar.clicked.connect(self.accept)
        lay.addWidget(btn_cerrar)

    def _cargar_abonos(self) -> None:
        # Limpiar lista
        while self._lay_lista.count():
            item = self._lay_lista.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        abonos = self._ctrl.cargar_abonos(self._factura.id)
        total = self._ctrl.total_abonado(self._factura.id)
        saldo = max(0.0, self._factura.monto - total)

        self._lbl_resumen.setText(
            f"Monto total: {cop(self._factura.monto)}   |   "
            f"Abonado: {cop(total)}   |   "
            f"Saldo pendiente: {cop(saldo)}"
        )

        if not abonos:
            lbl = QLabel("Sin abonos registrados aún.")
            lbl.setStyleSheet("color:#9CA3AF; font-size:11px; padding:4px;")
            self._lay_lista.addWidget(lbl)
        else:
            for a in abonos:
                fila = QWidget()
                fila.setStyleSheet("background:#F0FDF4; border-radius:4px;")
                fl = QHBoxLayout(fila)
                fl.setContentsMargins(8, 4, 8, 4)
                fl.setSpacing(8)
                fl.addWidget(QLabel(a.fecha.strftime("%d/%m/%Y")))
                lbl_m = QLabel(cop(a.monto))
                lbl_m.setStyleSheet("font-weight:bold; color:#15803D;")
                fl.addWidget(lbl_m)
                if a.notas:
                    fl.addWidget(QLabel(a.notas))
                fl.addStretch()
                btn_del = QPushButton("🗑")
                btn_del.setFixedSize(24, 22)
                btn_del.setStyleSheet(
                    "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
                    "border-radius:3px; }"
                    "QPushButton:hover { background:#FEE2E2; }"
                )
                btn_del.clicked.connect(lambda _, aid=a.id: self._on_eliminar_abono(aid))
                fl.addWidget(btn_del)
                self._lay_lista.addWidget(fila)

    def _on_abonar(self) -> None:
        monto = float(self._f_monto.valor_int())
        if monto <= 0:
            QMessageBox.warning(self, "Dato inválido", "El monto debe ser mayor a cero.")
            return
        qd = self._f_fecha.date()
        fecha = date(qd.year(), qd.month(), qd.day())
        notas = self._f_notas.text().strip()
        try:
            self._ctrl.registrar_abono(self._factura.id, monto, fecha, notas)
            self._f_monto.clear()
            self._f_notas.clear()
            self._cargar_abonos()
            self.abono_registrado.emit()
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _on_eliminar_abono(self, abono_id: int) -> None:
        resp = QMessageBox.question(
            self, "Eliminar abono", "¿Eliminar este abono?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self._ctrl.eliminar_abono(abono_id)
            self._cargar_abonos()
            self.abono_registrado.emit()


class FacturasPanel(QWidget):
    """Vista de gestión de facturas y recibos."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = FacturasController()
        self._facturas: list[Factura] = []
        self._editando_id: int | None = None
        self._build_ui()
        self._cargar_datos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(10)

        root.addLayout(self._barra_titulo())
        root.addWidget(self._alerta_widget())
        root.addWidget(self._panel_form())
        root.addWidget(self._build_tabla(), stretch=1)
        root.addWidget(self._barra_resumen())

    # ---- Barra de título ----

    def _barra_titulo(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Facturas y Recibos")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)

        desc = QLabel("Seguimiento de pagos pendientes")
        desc.setStyleSheet("color:#6B7280; font-size:12px;")

        self.chk_solo_pendientes = QCheckBox("Solo pendientes")
        self.chk_solo_pendientes.setChecked(True)
        self.chk_solo_pendientes.setStyleSheet("font-size:12px; color:#374151;")
        self.chk_solo_pendientes.toggled.connect(lambda _: self._cargar_datos())

        btn_nuevo = QPushButton("+ Nueva Factura")
        btn_nuevo.setFixedHeight(34)
        btn_nuevo.setStyleSheet(
            "QPushButton { border:1px solid #2563EB; border-radius:5px; padding:0 14px;"
            "color:#2563EB; background:white; font-weight:bold; }"
            "QPushButton:hover { background:#EFF6FF; }"
        )
        btn_nuevo.clicked.connect(self._on_nuevo)

        lay.addWidget(titulo)
        lay.addSpacing(12)
        lay.addWidget(desc)
        lay.addStretch()
        lay.addWidget(self.chk_solo_pendientes)
        lay.addSpacing(12)
        lay.addWidget(btn_nuevo)
        return lay

    # ---- Alerta banner ----

    def _alerta_widget(self) -> QFrame:
        self._frame_alerta = QFrame()
        self._frame_alerta.setStyleSheet(
            "QFrame { background:#FEF3C7; border:1px solid #FDE68A; border-radius:7px; }"
        )
        lay = QHBoxLayout(self._frame_alerta)
        lay.setContentsMargins(14, 8, 14, 8)
        self._lbl_alerta = QLabel("")
        self._lbl_alerta.setStyleSheet(
            "font-size:12px; font-weight:bold; color:#92400E;"
            "background:transparent; border:none;"
        )
        lay.addWidget(self._lbl_alerta)
        lay.addStretch()
        self._frame_alerta.setVisible(False)
        return self._frame_alerta

    def _actualizar_alerta(self) -> None:
        pendientes = [f for f in self._ctrl.cargar_pendientes()]
        n = len(pendientes)
        total_debe = sum(f.monto for f in pendientes)
        if n == 0:
            self._frame_alerta.setVisible(False)
        else:
            self._lbl_alerta.setText(
                f"⚠  {n} factura{'s' if n != 1 else ''} pendiente{'s' if n != 1 else ''}  •  "
                f"Total por pagar: {cop(total_debe)}"
            )
            self._frame_alerta.setVisible(True)

    # ---- Formulario colapsable ----

    def _panel_form(self) -> QFrame:
        self._frame_form = QFrame()
        self._frame_form.setObjectName("formFactura")
        self._frame_form.setStyleSheet(
            "QFrame#formFactura { background:#FFFBEB; border:1px solid #FDE68A;"
            "border-radius:8px; }"
        )
        self._frame_form.setVisible(False)

        lay = QVBoxLayout(self._frame_form)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(8)

        self._lbl_form_titulo = QLabel("Nueva Factura")
        f = QFont(); f.setBold(True); f.setPointSize(11)
        self._lbl_form_titulo.setFont(f)
        self._lbl_form_titulo.setStyleSheet(
            "color:#92400E; background:transparent; border:none;"
        )
        lay.addWidget(self._lbl_form_titulo)

        fila1 = QHBoxLayout(); fila1.setSpacing(10)
        fila2 = QHBoxLayout(); fila2.setSpacing(10)

        def _lbl(texto):
            l = QLabel(texto)
            l.setStyleSheet("color:#374151; font-size:11px; background:transparent; border:none;")
            return l

        def _field(placeholder, w=None):
            fe = QLineEdit()
            fe.setPlaceholderText(placeholder)
            fe.setFixedHeight(30)
            if w:
                fe.setFixedWidth(w)
            fe.setStyleSheet(
                "QLineEdit { border:1px solid #D1D5DB; border-radius:4px;"
                "padding:0 8px; background:white; }"
                "QLineEdit:focus { border:2px solid #F59E0B; }"
            )
            return fe

        # Fila 1: descripcion | proveedor | monto
        self._f_descripcion = _field("Concepto / nombre de la factura")
        self._f_descripcion.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._f_proveedor = _field("Proveedor o emisor", 180)
        self._f_monto = MoneyLineEdit()
        self._f_monto.setPlaceholderText("Monto a pagar")
        self._f_monto.setFixedHeight(30); self._f_monto.setFixedWidth(150)
        self._f_monto.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:4px;"
            "padding:0 8px; background:white; }"
            "QLineEdit:focus { border:2px solid #F59E0B; }"
        )

        for w, l in [
            (self._f_descripcion, "Descripción:"),
            (self._f_proveedor,   "Proveedor:"),
            (self._f_monto,       "Monto ($):"),
        ]:
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(_lbl(l)); col.addWidget(w)
            fila1.addLayout(col)

        # Fila 2: fecha llegada | fecha vencimiento | notas | botones
        self._f_fecha = QDateEdit()
        self._f_fecha.setDate(QDate.currentDate())
        self._f_fecha.setCalendarPopup(True)
        self._f_fecha.setFixedHeight(30); self._f_fecha.setFixedWidth(140)
        self._f_fecha.setDisplayFormat("dd/MM/yyyy")
        self._f_fecha.setStyleSheet(
            "QDateEdit { border:1px solid #D1D5DB; border-radius:4px;"
            "padding:0 8px; background:white; }"
            "QDateEdit:focus { border:2px solid #F59E0B; }"
        )

        # Fecha de vencimiento — checkbox + date picker
        from PySide6.QtWidgets import QCheckBox as _QCheckBox
        self._chk_vence = _QCheckBox("Fecha límite:")
        self._chk_vence.setStyleSheet(
            "color:#374151; font-size:11px; background:transparent; border:none;"
        )
        self._f_vence = QDateEdit()
        self._f_vence.setDate(QDate.currentDate().addDays(30))
        self._f_vence.setCalendarPopup(True)
        self._f_vence.setFixedHeight(30); self._f_vence.setFixedWidth(140)
        self._f_vence.setDisplayFormat("dd/MM/yyyy")
        self._f_vence.setEnabled(False)
        self._f_vence.setStyleSheet(
            "QDateEdit { border:1px solid #D1D5DB; border-radius:4px;"
            "padding:0 8px; background:white; }"
            "QDateEdit:focus { border:2px solid #F59E0B; }"
            "QDateEdit:disabled { background:#F3F4F6; color:#9CA3AF; }"
        )
        self._chk_vence.toggled.connect(self._f_vence.setEnabled)

        self._f_notas = _field("Observaciones (opcional)")
        self._f_notas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._btn_guardar_form = QPushButton("Guardar")
        self._btn_guardar_form.setFixedHeight(30)
        self._btn_guardar_form.setStyleSheet(
            "QPushButton { background:#F59E0B; color:white; border-radius:4px;"
            "padding:0 18px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#D97706; }"
        )
        self._btn_guardar_form.clicked.connect(self._on_guardar_factura)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(30)
        btn_cancelar.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:4px;"
            "padding:0 14px; background:white; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_cancelar.clicked.connect(self._on_cancelar_form)

        # Fecha llegada
        col_fl = QVBoxLayout(); col_fl.setSpacing(2)
        col_fl.addWidget(_lbl("Fecha llegada:")); col_fl.addWidget(self._f_fecha)
        fila2.addLayout(col_fl)

        # Fecha vencimiento (checkbox inline + picker)
        col_fv = QVBoxLayout(); col_fv.setSpacing(2)
        col_fv.addWidget(self._chk_vence); col_fv.addWidget(self._f_vence)
        fila2.addLayout(col_fv)

        # Notas
        col_n = QVBoxLayout(); col_n.setSpacing(2)
        col_n.addWidget(_lbl("Notas:")); col_n.addWidget(self._f_notas)
        fila2.addLayout(col_n)

        fila2.addStretch()
        for btn, label in [(self._btn_guardar_form, ""), (btn_cancelar, "")]:
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(_lbl(label)); col.addWidget(btn)
            fila2.addLayout(col)

        lay.addLayout(fila1)
        lay.addLayout(fila2)
        return self._frame_form

    # ---- Tabla ----

    def _build_tabla(self) -> QTableWidget:
        self.tabla = QTableWidget()
        # Cols: ID(hidden) | Descripción | Proveedor | Monto | Fecha llegada | Vence | Días | Estado | Acciones
        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Descripción", "Proveedor", "Monto",
            "Fecha llegada", "Vencimiento", "Días", "Estado", "Acciones"
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
                background:#1E293B; color:white;
                font-weight:bold; font-size:11px;
                padding:6px; border:none;
            }
            QTableWidget::item:selected { background:#FEF9C3; color:#78350F; }
            QToolTip {
                background:#1E293B; color:#FFFFFF;
                border:1px solid #475569; padding:5px 8px;
                font-size:12px; border-radius:4px;
            }
        """)

        hh = self.tabla.horizontalHeader()
        hh.setMinimumSectionSize(55)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); self.tabla.setColumnWidth(1, 240)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); self.tabla.setColumnWidth(2, 140)
        hh.setSectionResizeMode(3, QHeaderView.Fixed);       self.tabla.setColumnWidth(3, 115)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);       self.tabla.setColumnWidth(4, 105)
        hh.setSectionResizeMode(5, QHeaderView.Fixed);       self.tabla.setColumnWidth(5, 105)
        hh.setSectionResizeMode(6, QHeaderView.Fixed);       self.tabla.setColumnWidth(6, 60)
        hh.setSectionResizeMode(7, QHeaderView.Fixed);       self.tabla.setColumnWidth(7, 100)
        hh.setSectionResizeMode(8, QHeaderView.Fixed);       self.tabla.setColumnWidth(8, 225)
        self.tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

        return self.tabla

    # ---- Barra resumen ----

    def _barra_resumen(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; }"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 6, 14, 6)
        lay.setSpacing(20)

        self._lbl_total_facturas = QLabel("0 facturas")
        self._lbl_total_pendiente = QLabel("Por pagar: $ 0")
        self._lbl_total_pagado = QLabel("Pagado: $ 0")

        for lbl in (self._lbl_total_facturas, self._lbl_total_pendiente, self._lbl_total_pagado):
            lbl.setStyleSheet(
                "font-size:12px; font-weight:bold; color:#374151;"
                "background:transparent; border:none;"
            )
            lay.addWidget(lbl)

        lay.addStretch()
        return frame

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        self._cargar_datos()

    def _cargar_datos(self) -> None:
        if self.chk_solo_pendientes.isChecked():
            self._facturas = self._ctrl.cargar_pendientes()
        else:
            self._facturas = self._ctrl.cargar_todos()
        self._poblar_tabla()
        self._actualizar_alerta()
        self._actualizar_resumen()

    def _poblar_tabla(self) -> None:
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(self._facturas))

        for row, f in enumerate(self._facturas):
            self.tabla.setRowHeight(row, 36)
            self.tabla.setItem(row, 0, QTableWidgetItem(str(f.id)))
            self._celda(row, 1, f.descripcion)
            self._celda(row, 2, f.proveedor)
            self._celda(row, 3, cop(f.monto), Qt.AlignRight | Qt.AlignVCenter)
            self._celda(row, 4, f.fecha_llegada.strftime("%d/%m/%Y"), Qt.AlignCenter)

            # Columna Vencimiento
            if f.fecha_vencimiento:
                self._celda(row, 5, f.fecha_vencimiento.strftime("%d/%m/%Y"), Qt.AlignCenter)
            else:
                item_fv = QTableWidgetItem("—")
                item_fv.setTextAlignment(Qt.AlignCenter)
                item_fv.setForeground(QColor("#9CA3AF"))
                self.tabla.setItem(row, 5, item_fv)

            # Días — si hay vencimiento: días para vencer; si no: días transcurridos
            dias_venc = f.dias_para_vencer
            if dias_venc is not None and f.estado == "pendiente":
                # Días para vencer
                if dias_venc < 0:
                    txt_dias = f"Vencida {abs(dias_venc)}d"
                    color_dias = QColor("#DC2626")
                elif dias_venc == 0:
                    txt_dias = "Hoy"
                    color_dias = QColor("#DC2626")
                elif dias_venc <= 7:
                    txt_dias = f"{dias_venc}d"
                    color_dias = QColor("#D97706")
                else:
                    txt_dias = f"{dias_venc}d"
                    color_dias = QColor("#15803D")
            else:
                # Sin vencimiento: mostrar días transcurridos como antes
                dias_tr = f.dias_transcurridos
                txt_dias = str(dias_tr)
                if f.estado == "pendiente":
                    color_dias = (
                        QColor("#15803D") if dias_tr <= 7
                        else QColor("#D97706") if dias_tr <= 30
                        else QColor("#DC2626")
                    )
                else:
                    color_dias = QColor("#6B7280")
            item_dias = QTableWidgetItem(txt_dias)
            item_dias.setTextAlignment(Qt.AlignCenter)
            item_dias.setForeground(color_dias)
            self.tabla.setItem(row, 6, item_dias)

            self.tabla.setCellWidget(row, 7, self._badge_estado(f.estado))
            self.tabla.setCellWidget(row, 8, self._widget_acciones(f.id, f.estado))

    def _celda(self, row, col, texto, alin=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(alin)
        if texto:
            item.setToolTip(str(texto))
        self.tabla.setItem(row, col, item)

    def _actualizar_resumen(self) -> None:
        todas = self._ctrl.cargar_todos()
        n = len(self._facturas)
        por_pagar = sum(f.monto for f in todas if f.estado == "pendiente")
        pagado    = sum(f.monto for f in todas if f.estado == "pagada")
        self._lbl_total_facturas.setText(
            f"{n} factura{'s' if n != 1 else ''}"
        )
        self._lbl_total_pendiente.setText(f"Por pagar: {cop(por_pagar)}")
        self._lbl_total_pagado.setText(f"Pagado: {cop(pagado)}")

    # ---- Widgets de celda ----

    def _badge_estado(self, estado: str) -> QWidget:
        bg, fg, texto = _ESTADO_ESTILO.get(estado, ("#F3F4F6", "#374151", estado.upper()))
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lbl = QLabel(texto)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedHeight(22)
        lbl.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:4px;"
            "font-size:10px; font-weight:bold; padding:0 8px;"
        )
        lay.addStretch()
        lay.addWidget(lbl)
        lay.addStretch()
        return w

    def _widget_acciones(self, factura_id: int, estado: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(5)

        if estado == "pendiente":
            btn_abonar = QPushButton("Abonar")
            btn_abonar.setFixedHeight(26)
            btn_abonar.setStyleSheet(
                "QPushButton { background:#FEF3C7; color:#92400E; border:1px solid #FDE68A;"
                "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
                "QPushButton:hover { background:#FDE68A; }"
            )
            btn_abonar.clicked.connect(lambda _, fid=factura_id: self._on_abonar_factura(fid))
            lay.addWidget(btn_abonar)

            btn_pagar = QPushButton("Pagada")
            btn_pagar.setFixedHeight(26)
            btn_pagar.setStyleSheet(
                "QPushButton { background:#DCFCE7; color:#15803D; border:1px solid #86EFAC;"
                "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
                "QPushButton:hover { background:#BBF7D0; }"
            )
            btn_pagar.clicked.connect(lambda _, fid=factura_id: self._on_marcar_pagada(fid))
            lay.addWidget(btn_pagar)

        btn_editar = QPushButton("Editar")
        btn_editar.setFixedHeight(26)
        btn_editar.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn_editar.clicked.connect(lambda _, fid=factura_id: self._on_editar(fid))

        btn_borrar = QPushButton("Borrar")
        btn_borrar.setFixedHeight(26)
        btn_borrar.setStyleSheet(
            "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn_borrar.clicked.connect(lambda _, fid=factura_id: self._on_eliminar(fid))

        lay.addWidget(btn_editar)
        lay.addWidget(btn_borrar)
        return w

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_nuevo(self) -> None:
        self._editando_id = None
        self._lbl_form_titulo.setText("Nueva Factura")
        self._btn_guardar_form.setText("Guardar")
        self._limpiar_form()
        self._frame_form.setVisible(True)
        self._f_descripcion.setFocus()

    def _on_cancelar_form(self) -> None:
        self._frame_form.setVisible(False)
        self._editando_id = None

    def _on_editar(self, factura_id: int) -> None:
        f = next((x for x in self._facturas if x.id == factura_id), None)
        if not f:
            todas = self._ctrl.cargar_todos()
            f = next((x for x in todas if x.id == factura_id), None)
        if not f:
            return
        self._editando_id = factura_id
        self._lbl_form_titulo.setText("Editar Factura")
        self._btn_guardar_form.setText("Actualizar")
        self._f_descripcion.setText(f.descripcion)
        self._f_proveedor.setText(f.proveedor)
        self._f_monto.set_valor(int(f.monto))
        qd = QDate(f.fecha_llegada.year, f.fecha_llegada.month, f.fecha_llegada.day)
        self._f_fecha.setDate(qd)
        self._f_notas.setText(f.notas)
        if f.fecha_vencimiento:
            self._chk_vence.setChecked(True)
            qv = QDate(f.fecha_vencimiento.year, f.fecha_vencimiento.month, f.fecha_vencimiento.day)
            self._f_vence.setDate(qv)
        else:
            self._chk_vence.setChecked(False)
            self._f_vence.setDate(QDate.currentDate().addDays(30))
        self._frame_form.setVisible(True)
        self._f_descripcion.setFocus()

    def _on_guardar_factura(self) -> None:
        descripcion = self._f_descripcion.text().strip()
        if not descripcion:
            QMessageBox.warning(self, "Campo requerido",
                                "Ingresa una descripción para la factura.")
            self._f_descripcion.setFocus()
            return

        monto = float(self._f_monto.valor_int())
        proveedor = self._f_proveedor.text().strip()
        notas = self._f_notas.text().strip()
        qd = self._f_fecha.date()
        fecha = date(qd.year(), qd.month(), qd.day())

        fecha_venc = None
        if self._chk_vence.isChecked():
            qv = self._f_vence.date()
            fecha_venc = date(qv.year(), qv.month(), qv.day())

        try:
            if self._editando_id is None:
                self._ctrl.registrar(descripcion, proveedor, monto, fecha, notas, fecha_venc)
            else:
                f = Factura(
                    descripcion=descripcion,
                    proveedor=proveedor,
                    monto=monto,
                    fecha_llegada=fecha,
                    notas=notas,
                    fecha_vencimiento=fecha_venc,
                    estado=next(
                        (x.estado for x in self._ctrl.cargar_todos() if x.id == self._editando_id),
                        "pendiente",
                    ),
                    id=self._editando_id,
                )
                self._ctrl.editar(f)
        except ValueError as exc:
            QMessageBox.warning(self, "Dato inválido", str(exc))
            return

        self._frame_form.setVisible(False)
        self._editando_id = None
        self._cargar_datos()

    def _on_marcar_pagada(self, factura_id: int) -> None:
        f = next((x for x in self._facturas if x.id == factura_id), None)
        nombre = f.descripcion if f else f"id {factura_id}"
        resp = QMessageBox.question(
            self, "Marcar como pagada",
            f"¿Marcar <b>{nombre}</b> como pagada?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if resp == QMessageBox.Yes:
            self._ctrl.marcar_pagada(factura_id)
            self._cargar_datos()

    def _on_eliminar(self, factura_id: int) -> None:
        f = next((x for x in self._facturas if x.id == factura_id), None)
        nombre = f.descripcion if f else f"id {factura_id}"
        resp = QMessageBox.question(
            self, "Eliminar factura",
            f"¿Eliminar <b>{nombre}</b>?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self._ctrl.eliminar(factura_id)
            self._cargar_datos()

    def _on_abonar_factura(self, factura_id: int) -> None:
        todas = self._ctrl.cargar_todos()
        f = next((x for x in todas if x.id == factura_id), None)
        if not f:
            return
        dlg = AbonosDialog(f, self._ctrl, self)
        dlg.abono_registrado.connect(self._cargar_datos)
        dlg.exec()

    def _limpiar_form(self) -> None:
        self._f_descripcion.clear()
        self._f_proveedor.clear()
        self._f_monto.clear()
        self._f_fecha.setDate(QDate.currentDate())
        self._f_notas.clear()
        self._chk_vence.setChecked(False)
        self._f_vence.setDate(QDate.currentDate().addDays(30))
