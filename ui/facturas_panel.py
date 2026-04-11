"""
ui/facturas_panel.py
Panel de gestión de facturas y recibos pendientes de pago.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMessageBox, QCheckBox,
    QDateEdit, QSizePolicy,
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

        # Fila 2: fecha llegada | notas | botones
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

        for w, l in [
            (self._f_fecha, "Fecha llegada:"),
            (self._f_notas, "Notas:"),
        ]:
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(_lbl(l)); col.addWidget(w)
            fila2.addLayout(col)

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
        # Cols: ID(hidden) | Descripción | Proveedor | Monto | Fecha llegada | Días | Estado | Acciones
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Descripción", "Proveedor", "Monto",
            "Fecha llegada", "Días", "Estado", "Acciones"
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
        """)

        hh = self.tabla.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.Stretch)       # Descripción
        hh.setSectionResizeMode(2, QHeaderView.Interactive); self.tabla.setColumnWidth(2, 160)
        hh.setSectionResizeMode(3, QHeaderView.Fixed);       self.tabla.setColumnWidth(3, 120)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);       self.tabla.setColumnWidth(4, 110)
        hh.setSectionResizeMode(5, QHeaderView.Fixed);       self.tabla.setColumnWidth(5, 60)
        hh.setSectionResizeMode(6, QHeaderView.Fixed);       self.tabla.setColumnWidth(6, 100)
        hh.setSectionResizeMode(7, QHeaderView.Fixed);       self.tabla.setColumnWidth(7, 175)

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

            # Días — colorear según antigüedad
            dias = f.dias_transcurridos
            item_dias = QTableWidgetItem(str(dias))
            item_dias.setTextAlignment(Qt.AlignCenter)
            if f.estado == "pendiente":
                if dias <= 7:
                    item_dias.setForeground(QColor("#15803D"))
                elif dias <= 30:
                    item_dias.setForeground(QColor("#D97706"))
                else:
                    item_dias.setForeground(QColor("#DC2626"))
            else:
                item_dias.setForeground(QColor("#6B7280"))
            self.tabla.setItem(row, 5, item_dias)

            self.tabla.setCellWidget(row, 6, self._badge_estado(f.estado))
            self.tabla.setCellWidget(row, 7, self._widget_acciones(f.id, f.estado))

    def _celda(self, row, col, texto, alin=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(alin)
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
            btn_pagar = QPushButton("Marcar Pagada")
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
            # Puede estar oculta por filtro; buscar en todas
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

        try:
            if self._editando_id is None:
                self._ctrl.registrar(descripcion, proveedor, monto, fecha, notas)
            else:
                f = Factura(
                    descripcion=descripcion,
                    proveedor=proveedor,
                    monto=monto,
                    fecha_llegada=fecha,
                    notas=notas,
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

    def _limpiar_form(self) -> None:
        self._f_descripcion.clear()
        self._f_proveedor.clear()
        self._f_monto.clear()
        self._f_fecha.setDate(QDate.currentDate())
        self._f_notas.clear()
