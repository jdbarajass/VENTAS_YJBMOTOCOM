"""
ui/fiado_panel.py
Panel de control de clientes deudores (fiado).
Permite registrar, abonar y dar por pagadas deudas de clientes.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMessageBox, QCheckBox,
    QDateEdit, QSizePolicy, QDialog, QScrollArea,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont, QColor

from controllers.fiado_controller import FiadoController
from models.fiado import Fiado
from ui.venta_form import MoneyLineEdit
from utils.formatters import cop


_ESTADO_ESTILO = {
    "pendiente": ("#FEE2E2", "#991B1B", "PENDIENTE"),
    "pagado":    ("#DCFCE7", "#15803D", "PAGADO"),
}


class _AbonosFiadoDialog(QDialog):
    """Diálogo para registrar y ver abonos de una deuda."""

    abono_registrado = Signal()

    def __init__(self, fiado: Fiado, ctrl: FiadoController, parent=None) -> None:
        super().__init__(parent)
        self._fiado = fiado
        self._ctrl = ctrl
        self.setWindowTitle(f"Abonos — {fiado.cliente_nombre}")
        self.setMinimumWidth(540)
        self._build_ui()
        self._cargar_abonos()

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(12)

        lbl = QLabel(
            f"Cliente: <b>{self._fiado.cliente_nombre}</b>"
            + (f"  •  Cédula: {self._fiado.cliente_cedula}" if self._fiado.cliente_cedula else "")
            + (f"  •  Tel: {self._fiado.cliente_tel}" if self._fiado.cliente_tel else "")
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size:12px; color:#374151;")
        lay.addWidget(lbl)

        lbl_desc = QLabel(f"Deuda: {self._fiado.descripcion}")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size:11px; color:#6B7280;")
        lay.addWidget(lbl_desc)

        self._lbl_resumen = QLabel("")
        self._lbl_resumen.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#991B1B;"
            "background:#FEF2F2; border-radius:5px; padding:6px 10px;"
        )
        lay.addWidget(self._lbl_resumen)

        # Lista de abonos
        self._lista = QWidget()
        self._lista.setStyleSheet("background:transparent;")
        self._lay_lista = QVBoxLayout(self._lista)
        self._lay_lista.setContentsMargins(0, 0, 0, 0)
        self._lay_lista.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidget(self._lista)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(140)
        scroll.setFrameShape(QFrame.NoFrame)
        lay.addWidget(scroll)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#E5E7EB;")
        lay.addWidget(sep)

        lbl_nuevo = QLabel("Registrar nuevo abono")
        f = QFont(); f.setBold(True); f.setPointSize(10)
        lbl_nuevo.setFont(f)
        lay.addWidget(lbl_nuevo)

        fila = QHBoxLayout(); fila.setSpacing(8)
        self._f_monto = MoneyLineEdit()
        self._f_monto.setPlaceholderText("Monto")
        self._f_monto.setFixedHeight(30)
        self._f_monto.setStyleSheet(
            "QLineEdit{border:1px solid #D1D5DB;border-radius:4px;padding:0 8px;}"
        )
        self._f_fecha = QDateEdit()
        self._f_fecha.setDate(QDate.currentDate())
        self._f_fecha.setCalendarPopup(True)
        self._f_fecha.setFixedHeight(30); self._f_fecha.setFixedWidth(130)
        self._f_fecha.setDisplayFormat("dd/MM/yyyy")
        self._f_fecha.setStyleSheet(
            "QDateEdit{border:1px solid #D1D5DB;border-radius:4px;padding:0 8px;}"
        )
        self._f_notas = QLineEdit()
        self._f_notas.setPlaceholderText("Notas (opcional)")
        self._f_notas.setFixedHeight(30)
        self._f_notas.setStyleSheet(
            "QLineEdit{border:1px solid #D1D5DB;border-radius:4px;padding:0 8px;}"
        )
        btn = QPushButton("Registrar abono")
        btn.setFixedHeight(30)
        btn.setStyleSheet(
            "QPushButton{background:#DC2626;color:white;border-radius:4px;"
            "padding:0 14px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#B91C1C;}"
        )
        btn.clicked.connect(self._on_abonar)
        fila.addWidget(self._f_monto, stretch=2)
        fila.addWidget(self._f_fecha)
        fila.addWidget(self._f_notas, stretch=2)
        fila.addWidget(btn)
        lay.addLayout(fila)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedHeight(30)
        btn_cerrar.clicked.connect(self.accept)
        lay.addWidget(btn_cerrar)

    def _cargar_abonos(self) -> None:
        while self._lay_lista.count():
            item = self._lay_lista.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        abonos = self._ctrl.cargar_abonos(self._fiado.id)
        total = self._ctrl.total_abonado(self._fiado.id)
        saldo = max(0.0, self._fiado.monto_total - total)

        self._lbl_resumen.setText(
            f"Deuda total: {cop(self._fiado.monto_total)}   |   "
            f"Abonado: {cop(total)}   |   "
            f"Saldo pendiente: {cop(saldo)}"
        )
        if saldo <= 0:
            self._lbl_resumen.setStyleSheet(
                "font-size:13px; font-weight:bold; color:#15803D;"
                "background:#DCFCE7; border-radius:5px; padding:6px 10px;"
            )

        if not abonos:
            lbl = QLabel("Sin abonos registrados.")
            lbl.setStyleSheet("color:#9CA3AF;font-size:11px;padding:4px;")
            self._lay_lista.addWidget(lbl)
        else:
            for a in abonos:
                fila = QWidget()
                fila.setStyleSheet("background:#FEF2F2;border-radius:4px;")
                fl = QHBoxLayout(fila)
                fl.setContentsMargins(8, 4, 8, 4); fl.setSpacing(8)
                fl.addWidget(QLabel(a.fecha.strftime("%d/%m/%Y")))
                lm = QLabel(cop(a.monto))
                lm.setStyleSheet("font-weight:bold;color:#15803D;")
                fl.addWidget(lm)
                if a.notas:
                    fl.addWidget(QLabel(a.notas))
                fl.addStretch()
                btn_del = QPushButton("🗑")
                btn_del.setFixedSize(24, 22)
                btn_del.setStyleSheet(
                    "QPushButton{background:#FEF2F2;color:#DC2626;"
                    "border:1px solid #FECACA;border-radius:3px;}"
                    "QPushButton:hover{background:#FEE2E2;}"
                )
                btn_del.clicked.connect(lambda _, aid=a.id: self._on_eliminar(aid))
                fl.addWidget(btn_del)
                self._lay_lista.addWidget(fila)

    def _on_abonar(self) -> None:
        monto = float(self._f_monto.valor_int())
        if monto <= 0:
            QMessageBox.warning(self, "Dato inválido", "El monto debe ser mayor a cero.")
            return
        qd = self._f_fecha.date()
        fecha = date(qd.year(), qd.month(), qd.day())
        try:
            self._ctrl.registrar_abono(self._fiado.id, monto, fecha, self._f_notas.text().strip())
            self._f_monto.clear(); self._f_notas.clear()
            self._cargar_abonos()
            self.abono_registrado.emit()
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _on_eliminar(self, abono_id: int) -> None:
        if QMessageBox.question(
            self, "Eliminar abono", "¿Eliminar este abono?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) == QMessageBox.Yes:
            self._ctrl.eliminar_abono(abono_id)
            self._cargar_abonos()
            self.abono_registrado.emit()


class FiadoPanel(QWidget):
    """Panel de control de clientes deudores."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = FiadoController()
        self._fiados: list[Fiado] = []
        self._editando_id: int | None = None
        self._build_ui()
        self._cargar_datos()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        contenido = QWidget()
        root = QVBoxLayout(contenido)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(10)

        root.addLayout(self._barra_titulo())
        root.addWidget(self._alerta_widget())
        root.addWidget(self._panel_form())
        root.addWidget(self._build_tabla(), stretch=1)
        root.addWidget(self._barra_resumen())

        scroll.setWidget(contenido)
        outer.addWidget(scroll)

    def _barra_titulo(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        titulo = QLabel("Apartados y Abonos de Clientes")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)
        desc = QLabel("Productos apartados o fiados a clientes, con sus abonos hasta saldar la deuda")
        desc.setStyleSheet("color:#6B7280;font-size:12px;")

        self._chk_pendientes = QCheckBox("Solo pendientes")
        self._chk_pendientes.setChecked(True)
        self._chk_pendientes.setStyleSheet("font-size:12px;color:#374151;")
        self._chk_pendientes.toggled.connect(lambda _: self._cargar_datos())

        btn_nuevo = QPushButton("+ Nueva Deuda")
        btn_nuevo.setFixedHeight(34)
        btn_nuevo.setStyleSheet(
            "QPushButton{border:1px solid #DC2626;border-radius:5px;"
            "padding:0 14px;color:#DC2626;font-weight:bold;}"
            "QPushButton:hover{background:#FEF2F2;}"
        )
        btn_nuevo.clicked.connect(self._on_nuevo)

        lay.addWidget(titulo); lay.addSpacing(12); lay.addWidget(desc)
        lay.addStretch()
        lay.addWidget(self._chk_pendientes); lay.addSpacing(12)
        lay.addWidget(btn_nuevo)
        return lay

    def _alerta_widget(self) -> QFrame:
        self._frame_alerta = QFrame()
        self._frame_alerta.setStyleSheet(
            "QFrame{background:#FEF2F2;border:1px solid #FECACA;border-radius:7px;}"
        )
        lay = QHBoxLayout(self._frame_alerta)
        lay.setContentsMargins(14, 8, 14, 8)
        self._lbl_alerta = QLabel("")
        self._lbl_alerta.setStyleSheet(
            "font-size:12px;font-weight:bold;color:#991B1B;"
            "background:transparent;border:none;"
        )
        lay.addWidget(self._lbl_alerta); lay.addStretch()
        self._frame_alerta.setVisible(False)
        return self._frame_alerta

    def _actualizar_alerta(self) -> None:
        pendientes = self._ctrl.cargar_pendientes()
        n = len(pendientes)
        total = sum(
            max(0.0, f.monto_total - self._ctrl.total_abonado(f.id))
            for f in pendientes
        )
        if n == 0:
            self._frame_alerta.setVisible(False)
        else:
            self._lbl_alerta.setText(
                f"⚠  {n} cliente{'s' if n != 1 else ''} con deuda pendiente  •  "
                f"Total por cobrar: {cop(total)}"
            )
            self._frame_alerta.setVisible(True)

    def _panel_form(self) -> QFrame:
        self._frame_form = QFrame()
        self._frame_form.setObjectName("formFiado")
        self._frame_form.setStyleSheet(
            "QFrame#formFiado{background:#FFF5F5;border:1px solid #FECACA;border-radius:8px;}"
        )
        self._frame_form.setVisible(False)

        lay = QVBoxLayout(self._frame_form)
        lay.setContentsMargins(14, 10, 14, 10); lay.setSpacing(8)

        self._lbl_form_titulo = QLabel("Nueva Deuda")
        f = QFont(); f.setBold(True); f.setPointSize(11)
        self._lbl_form_titulo.setFont(f)
        self._lbl_form_titulo.setStyleSheet("color:#991B1B;background:transparent;border:none;")
        lay.addWidget(self._lbl_form_titulo)

        fila1 = QHBoxLayout(); fila1.setSpacing(10)
        fila2 = QHBoxLayout(); fila2.setSpacing(10)

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet("color:#374151;font-size:11px;background:transparent;border:none;")
            return l

        def _field(ph, w=None):
            fe = QLineEdit(); fe.setPlaceholderText(ph); fe.setFixedHeight(30)
            if w: fe.setFixedWidth(w)
            fe.setStyleSheet(
                "QLineEdit{border-radius:4px;padding:0 8px;}"
                "QLineEdit:focus{border:2px solid #DC2626;}"
            )
            return fe

        self._f_cliente  = _field("Nombre del cliente")
        self._f_cliente.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._f_cedula   = _field("Cédula (opcional)", 150)
        self._f_tel      = _field("Teléfono (opcional)", 150)
        self._f_desc     = _field("Descripción (qué se llevó)")
        self._f_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._f_monto = MoneyLineEdit()
        self._f_monto.setPlaceholderText("Monto de la deuda")
        self._f_monto.setFixedHeight(30); self._f_monto.setFixedWidth(160)
        self._f_monto.setStyleSheet(
            "QLineEdit{border-radius:4px;padding:0 8px;}"
            "QLineEdit:focus{border:2px solid #DC2626;}"
        )
        self._f_abono_inicial = MoneyLineEdit()
        self._f_abono_inicial.setPlaceholderText("Abono inicial (opcional)")
        self._f_abono_inicial.setFixedHeight(30); self._f_abono_inicial.setFixedWidth(160)
        self._f_abono_inicial.setStyleSheet(
            "QLineEdit{border-radius:4px;padding:0 8px;}"
            "QLineEdit:focus{border:2px solid #DC2626;}"
        )

        for w, l in [(self._f_cliente, "Cliente:"), (self._f_cedula, "Cédula:"),
                     (self._f_tel, "Teléfono:"), (self._f_monto, "Monto ($):")]:
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(_lbl(l)); col.addWidget(w)
            fila1.addLayout(col)

        self._lbl_abono_inicial = _lbl("Abono inicial ($):")
        self._col_abono_inicial = QVBoxLayout(); self._col_abono_inicial.setSpacing(2)
        self._col_abono_inicial.addWidget(self._lbl_abono_inicial)
        self._col_abono_inicial.addWidget(self._f_abono_inicial)
        fila1.addLayout(self._col_abono_inicial)

        self._f_fecha = QDateEdit()
        self._f_fecha.setDate(QDate.currentDate())
        self._f_fecha.setCalendarPopup(True)
        self._f_fecha.setFixedHeight(30); self._f_fecha.setFixedWidth(140)
        self._f_fecha.setDisplayFormat("dd/MM/yyyy")
        self._f_fecha.setStyleSheet(
            "QDateEdit{border-radius:4px;padding:0 8px;}"
            "QDateEdit:focus{border:2px solid #DC2626;}"
        )
        self._f_notas = _field("Observaciones (opcional)")
        self._f_notas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._btn_guardar = QPushButton("Guardar")
        self._btn_guardar.setFixedHeight(30)
        self._btn_guardar.setStyleSheet(
            "QPushButton{background:#DC2626;color:white;border-radius:4px;"
            "padding:0 18px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#B91C1C;}"
        )
        self._btn_guardar.clicked.connect(self._on_guardar)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(30)
        btn_cancelar.clicked.connect(self._on_cancelar)

        for w, l in [(self._f_desc, "Descripción:"), (self._f_fecha, "Fecha:")]:
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(_lbl(l)); col.addWidget(w)
            fila2.addLayout(col)
        col_n = QVBoxLayout(); col_n.setSpacing(2)
        col_n.addWidget(_lbl("Notas:")); col_n.addWidget(self._f_notas)
        fila2.addLayout(col_n)
        fila2.addStretch()
        for btn, label in [(self._btn_guardar, ""), (btn_cancelar, "")]:
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(_lbl(label)); col.addWidget(btn)
            fila2.addLayout(col)

        lay.addLayout(fila1)
        lay.addLayout(fila2)
        return self._frame_form

    def _build_tabla(self) -> QTableWidget:
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Cliente", "Cédula", "Descripción",
            "Deuda", "Abonado", "Saldo", "Días", "Acciones"
        ])
        self.tabla.setColumnHidden(0, True)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setStyleSheet("""
            QTableWidget{border:none;font-size:12px;}
            QTableWidget::item{padding:4px 8px;}
            QHeaderView::section{
                background:#7F1D1D;color:white;font-weight:bold;
                font-size:11px;padding:6px;border:none;
            }
            QTableWidget::item:selected{background:#FEE2E2;color:#7F1D1D;}
        """)
        hh = self.tabla.horizontalHeader()
        for col, w in [(1,150),(2,110),(3,200),(4,110),(5,110),(6,110),(7,55),(8,220)]:
            hh.setSectionResizeMode(col, QHeaderView.Interactive)
            self.tabla.setColumnWidth(col, w)
        self.tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tabla.setMinimumHeight(180)
        return self.tabla

    def _barra_resumen(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;}"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 6, 14, 6); lay.setSpacing(16)
        self._lbl_total_deudas   = QLabel("0 deudas")
        self._lbl_total_pendiente = QLabel("Por cobrar: $ 0")
        self._lbl_total_cobrado   = QLabel("Cobrado: $ 0")
        for lbl in (self._lbl_total_deudas, self._lbl_total_pendiente, self._lbl_total_cobrado):
            lbl.setStyleSheet(
                "font-size:12px;font-weight:bold;color:#374151;"
                "background:transparent;border:none;"
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
        if self._chk_pendientes.isChecked():
            self._fiados = self._ctrl.cargar_pendientes()
        else:
            self._fiados = self._ctrl.cargar_todos()
        self._poblar_tabla()
        self._actualizar_alerta()
        self._actualizar_resumen()

    def _poblar_tabla(self) -> None:
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(self._fiados))
        for row, f in enumerate(self._fiados):
            self.tabla.setRowHeight(row, 36)
            self.tabla.setItem(row, 0, QTableWidgetItem(str(f.id)))
            self._celda(row, 1, f.cliente_nombre)
            self._celda(row, 2, f.cliente_cedula or "—")
            self._celda(row, 3, f.descripcion)
            self._celda(row, 4, cop(f.monto_total), Qt.AlignRight | Qt.AlignVCenter)

            abonado = self._ctrl.total_abonado(f.id)
            saldo   = max(0.0, f.monto_total - abonado)

            item_ab = QTableWidgetItem(cop(abonado))
            item_ab.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_ab.setForeground(QColor("#15803D"))
            self.tabla.setItem(row, 5, item_ab)

            item_s = QTableWidgetItem(cop(saldo))
            item_s.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_s.setForeground(QColor("#DC2626") if saldo > 0 else QColor("#15803D"))
            self.tabla.setItem(row, 6, item_s)

            dias = f.dias_transcurridos
            item_d = QTableWidgetItem(str(dias))
            item_d.setTextAlignment(Qt.AlignCenter)
            item_d.setForeground(
                QColor("#DC2626") if dias > 30
                else QColor("#D97706") if dias > 7
                else QColor("#15803D")
            )
            self.tabla.setItem(row, 7, item_d)

            self.tabla.setCellWidget(row, 8, self._widget_acciones(f.id, f.estado))

    def _celda(self, row, col, texto, alin=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(alin)
        if texto:
            item.setToolTip(str(texto))
        self.tabla.setItem(row, col, item)

    def _actualizar_resumen(self) -> None:
        todas = self._ctrl.cargar_todos()
        n = len(self._fiados)
        pendientes = [f for f in todas if f.estado == "pendiente"]
        por_cobrar = sum(
            max(0.0, f.monto_total - self._ctrl.total_abonado(f.id))
            for f in pendientes
        )
        cobrado = sum(self._ctrl.total_abonado(f.id) for f in todas if f.estado == "pagado")
        self._lbl_total_deudas.setText(f"{n} deuda{'s' if n != 1 else ''}")
        self._lbl_total_pendiente.setText(f"Por cobrar: {cop(por_cobrar)}")
        self._lbl_total_cobrado.setText(f"Cobrado: {cop(cobrado)}")

    def _widget_acciones(self, fiado_id: int, estado: str) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2); lay.setSpacing(5)

        if estado == "pendiente":
            btn_abonar = QPushButton("Abonar")
            btn_abonar.setFixedHeight(26)
            btn_abonar.setStyleSheet(
                "QPushButton{background:#FEE2E2;color:#991B1B;border:1px solid #FECACA;"
                "border-radius:4px;font-size:11px;font-weight:bold;padding:0 8px;}"
                "QPushButton:hover{background:#FECACA;}"
            )
            btn_abonar.clicked.connect(lambda _, fid=fiado_id: self._on_abonar(fid))
            lay.addWidget(btn_abonar)

            btn_pagar = QPushButton("Pagado")
            btn_pagar.setFixedHeight(26)
            btn_pagar.setStyleSheet(
                "QPushButton{background:#DCFCE7;color:#15803D;border:1px solid #86EFAC;"
                "border-radius:4px;font-size:11px;font-weight:bold;padding:0 8px;}"
                "QPushButton:hover{background:#BBF7D0;}"
            )
            btn_pagar.clicked.connect(lambda _, fid=fiado_id: self._on_marcar_pagado(fid))
            lay.addWidget(btn_pagar)

        btn_editar = QPushButton("Editar")
        btn_editar.setFixedHeight(26)
        btn_editar.setStyleSheet(
            "QPushButton{background:#EFF6FF;color:#1D4ED8;border:1px solid #BFDBFE;"
            "border-radius:4px;font-size:11px;font-weight:bold;padding:0 8px;}"
            "QPushButton:hover{background:#DBEAFE;}"
        )
        btn_editar.clicked.connect(lambda _, fid=fiado_id: self._on_editar(fid))

        btn_borrar = QPushButton("Borrar")
        btn_borrar.setFixedHeight(26)
        btn_borrar.setStyleSheet(
            "QPushButton{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;"
            "border-radius:4px;font-size:11px;font-weight:bold;padding:0 8px;}"
            "QPushButton:hover{background:#FEE2E2;}"
        )
        btn_borrar.clicked.connect(lambda _, fid=fiado_id: self._on_eliminar(fid))

        lay.addWidget(btn_editar)
        lay.addWidget(btn_borrar)
        return w

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_nuevo(self) -> None:
        self._editando_id = None
        self._lbl_form_titulo.setText("Nueva Deuda")
        self._btn_guardar.setText("Guardar")
        self._limpiar_form()
        self._lbl_abono_inicial.setVisible(True)
        self._f_abono_inicial.setVisible(True)
        self._frame_form.setVisible(True)
        self._f_cliente.setFocus()

    def _on_cancelar(self) -> None:
        self._frame_form.setVisible(False)
        self._editando_id = None

    def _on_editar(self, fiado_id: int) -> None:
        f = next((x for x in self._ctrl.cargar_todos() if x.id == fiado_id), None)
        if not f:
            return
        self._editando_id = fiado_id
        self._lbl_form_titulo.setText("Editar Deuda")
        self._btn_guardar.setText("Actualizar")
        self._f_cliente.setText(f.cliente_nombre)
        self._f_cedula.setText(f.cliente_cedula)
        self._f_tel.setText(f.cliente_tel)
        self._f_desc.setText(f.descripcion)
        self._f_monto.set_valor(int(f.monto_total))
        self._f_fecha.setDate(QDate(f.fecha.year, f.fecha.month, f.fecha.day))
        self._f_notas.setText(f.notas)
        self._lbl_abono_inicial.setVisible(False)
        self._f_abono_inicial.setVisible(False)
        self._frame_form.setVisible(True)
        self._f_cliente.setFocus()

    def _on_guardar(self) -> None:
        cliente = self._f_cliente.text().strip()
        if not cliente:
            QMessageBox.warning(self, "Campo requerido", "Ingresa el nombre del cliente.")
            self._f_cliente.setFocus()
            return
        desc = self._f_desc.text().strip()
        if not desc:
            QMessageBox.warning(self, "Campo requerido", "Ingresa la descripción de la deuda.")
            self._f_desc.setFocus()
            return
        monto = float(self._f_monto.valor_int())
        if monto <= 0:
            QMessageBox.warning(self, "Campo requerido", "El monto debe ser mayor a cero.")
            return
        abono_inicial = float(self._f_abono_inicial.valor_int()) if self._editando_id is None else 0.0
        if abono_inicial > monto:
            QMessageBox.warning(
                self, "Dato inválido",
                "El abono inicial no puede ser mayor al monto de la deuda."
            )
            return
        qd = self._f_fecha.date()
        fecha = date(qd.year(), qd.month(), qd.day())
        try:
            if self._editando_id is None:
                nuevo_id = self._ctrl.registrar(
                    cliente, desc, monto, fecha,
                    self._f_cedula.text().strip(),
                    self._f_tel.text().strip(),
                    self._f_notas.text().strip(),
                )
                if abono_inicial > 0:
                    self._ctrl.registrar_abono(nuevo_id, abono_inicial, fecha, "Abono inicial")
            else:
                todas = self._ctrl.cargar_todos()
                f_orig = next((x for x in todas if x.id == self._editando_id), None)
                f = Fiado(
                    id=self._editando_id,
                    cliente_nombre=cliente,
                    descripcion=desc,
                    monto_total=monto,
                    fecha=fecha,
                    cliente_cedula=self._f_cedula.text().strip(),
                    cliente_tel=self._f_tel.text().strip(),
                    notas=self._f_notas.text().strip(),
                    estado=f_orig.estado if f_orig else "pendiente",
                )
                self._ctrl.editar(f)
        except ValueError as exc:
            QMessageBox.warning(self, "Dato inválido", str(exc))
            return
        self._frame_form.setVisible(False)
        self._editando_id = None
        self._cargar_datos()

    def _on_marcar_pagado(self, fiado_id: int) -> None:
        f = next((x for x in self._fiados if x.id == fiado_id), None)
        nombre = f.cliente_nombre if f else f"id {fiado_id}"
        if QMessageBox.question(
            self, "Marcar como pagado",
            f"¿Marcar la deuda de <b>{nombre}</b> como pagada?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) == QMessageBox.Yes:
            self._ctrl.marcar_pagado(fiado_id)
            self._cargar_datos()

    def _on_abonar(self, fiado_id: int) -> None:
        todas = self._ctrl.cargar_todos()
        f = next((x for x in todas if x.id == fiado_id), None)
        if not f:
            return
        dlg = _AbonosFiadoDialog(f, self._ctrl, self)
        dlg.abono_registrado.connect(self._cargar_datos)
        dlg.exec()

    def _on_eliminar(self, fiado_id: int) -> None:
        f = next((x for x in self._ctrl.cargar_todos() if x.id == fiado_id), None)
        nombre = f.cliente_nombre if f else f"id {fiado_id}"
        if QMessageBox.question(
            self, "Eliminar deuda",
            f"¿Eliminar la deuda de <b>{nombre}</b> y todos sus abonos?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) == QMessageBox.Yes:
            self._ctrl.eliminar(fiado_id)
            self._cargar_datos()

    def _limpiar_form(self) -> None:
        self._f_cliente.clear(); self._f_cedula.clear(); self._f_tel.clear()
        self._f_desc.clear(); self._f_monto.clear(); self._f_notas.clear()
        self._f_abono_inicial.clear()
        self._f_fecha.setDate(QDate.currentDate())
