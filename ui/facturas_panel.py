"""
ui/facturas_panel.py
Panel de gestión de facturas — dos pestañas:
  • Facturas por pagar (gestión CRUD + abonos)
  • Cargue de pedidos  (importar PDF → inventario de cascos)
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMessageBox, QCheckBox,
    QDateEdit, QSizePolicy, QDialog, QScrollArea, QTabWidget,
    QComboBox,
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

        # Selector de cuenta de pago
        fila_cuenta = QHBoxLayout(); fila_cuenta.setSpacing(8)
        lbl_cta = QLabel("Cuenta de pago:")
        lbl_cta.setStyleSheet("font-size:11px; color:#374151;")
        lbl_cta.setFixedWidth(110)
        self._combo_cuenta = QComboBox()
        self._combo_cuenta.setFixedHeight(28)
        self._combo_cuenta.setStyleSheet(
            "QComboBox { border:1px solid #D1D5DB; border-radius:4px; padding:0 8px;"
            " font-size:12px; }"
        )
        self._combo_cuenta.addItem("— Sin descontar de cuentas —", None)
        try:
            from database.cuentas_repo import obtener_todas as _cuentas
            from utils.formatters import cop as _cop
            for c in _cuentas():
                self._combo_cuenta.addItem(
                    f"{c.nombre}  ({_cop(c.balance_actual)})", c.id
                )
        except Exception:
            pass
        fila_cuenta.addWidget(lbl_cta)
        fila_cuenta.addWidget(self._combo_cuenta, stretch=1)
        lay.addLayout(fila_cuenta)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedHeight(30)
        btn_cerrar.setStyleSheet(
            "QPushButton { border-radius:4px; padding:0 14px; }"
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

        # Cargar mapa cuenta_id → nombre para mostrar en abonos
        cuentas_dict: dict[int, str] = {}
        try:
            from database.cuentas_repo import obtener_todas as _cuentas
            cuentas_dict = {c.id: c.nombre for c in _cuentas()}
        except Exception:
            pass

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
                cuenta_nombre = cuentas_dict.get(
                    getattr(a, "cuenta_id", None) or -1, ""
                )
                if cuenta_nombre:
                    lbl_cta = QLabel(f"({cuenta_nombre})")
                    lbl_cta.setStyleSheet("color:#6B7280; font-size:10px;")
                    fl.addWidget(lbl_cta)
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
        cuenta_id = self._combo_cuenta.currentData()
        try:
            self._ctrl.registrar_abono(self._factura.id, monto, fecha, notas, cuenta_id)
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


class _ItemsFacturaDialog(QDialog):
    """Dialog para gestionar los items (líneas) de una factura."""

    def __init__(self, factura: "Factura", parent=None) -> None:
        super().__init__(parent)
        self._factura = factura
        self.setWindowTitle(f"Items — {factura.descripcion[:55]}")
        self.setMinimumWidth(560)
        self.setMinimumHeight(400)
        self._build_ui()
        self._cargar_items()

    def _build_ui(self) -> None:
        from ui.venta_form import MoneyLineEdit as _MLE
        from PySide6.QtWidgets import QDoubleSpinBox as _DSB
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        # Título
        lbl = QLabel(f"Items de: <b>{self._factura.descripcion}</b>")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size:12px; color:#374151;")
        lay.addWidget(lbl)

        # Tabla de items existentes
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(5)
        self._tabla.setHorizontalHeaderLabels(["#", "Descripción", "Cant.", "P. Unit.", "Subtotal"])
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setShowGrid(False)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setMaximumHeight(180)
        self._tabla.setStyleSheet(
            "QTableWidget { border:1px solid #E5E7EB; border-radius:6px; font-size:11px; }"
            "QHeaderView::section { background:#1E293B; color:white; font-weight:bold;"
            "  border:none; padding:5px; font-size:10px; }"
            "QTableWidget::item:selected { background:#FEF3C7; color:#78350F; }"
        )
        hh = self._tabla.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed); self._tabla.setColumnWidth(0, 30)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed); self._tabla.setColumnWidth(2, 60)
        hh.setSectionResizeMode(3, QHeaderView.Fixed); self._tabla.setColumnWidth(3, 100)
        hh.setSectionResizeMode(4, QHeaderView.Fixed); self._tabla.setColumnWidth(4, 110)
        lay.addWidget(self._tabla)

        # Resumen total
        self._lbl_total = QLabel("Total items: $ 0")
        self._lbl_total.setAlignment(Qt.AlignRight)
        self._lbl_total.setStyleSheet(
            "font-size:13px; font-weight:bold; color:#1D4ED8;"
            "background:#EFF6FF; border-radius:5px; padding:4px 10px;"
        )
        lay.addWidget(self._lbl_total)

        # Formulario nuevo item
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#E5E7EB;")
        lay.addWidget(sep)

        lbl_nuevo = QLabel("Agregar item:")
        lbl_nuevo.setStyleSheet("font-size:11px; font-weight:bold; color:#374151;")
        lay.addWidget(lbl_nuevo)

        fila = QHBoxLayout(); fila.setSpacing(8)

        self._f_desc = QLineEdit()
        self._f_desc.setPlaceholderText("Descripción del item")
        self._f_desc.setFixedHeight(32)
        self._f_desc.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:4px; padding:0 8px; }"
        )

        self._f_cant = _DSB()
        self._f_cant.setRange(0.01, 9999)
        self._f_cant.setValue(1)
        self._f_cant.setDecimals(2)
        self._f_cant.setFixedWidth(70)
        self._f_cant.setFixedHeight(32)

        self._f_precio = _MLE()
        self._f_precio.setPlaceholderText("Precio")
        self._f_precio.setFixedWidth(110)
        self._f_precio.setFixedHeight(32)
        self._f_precio.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:4px; padding:0 8px; }"
        )

        btn_add = QPushButton("+ Agregar")
        btn_add.setFixedHeight(32)
        btn_add.setStyleSheet(
            "QPushButton { background:#F59E0B; color:white; border-radius:4px;"
            "padding:0 14px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#D97706; }"
        )
        btn_add.clicked.connect(self._on_agregar)

        fila.addWidget(self._f_desc, stretch=2)
        fila.addWidget(self._f_cant)
        fila.addWidget(self._f_precio)
        fila.addWidget(btn_add)
        lay.addLayout(fila)

        self._lbl_fb = QLabel("")
        self._lbl_fb.setStyleSheet("font-size:11px; color:#DC2626;")
        lay.addWidget(self._lbl_fb)

        # Botón borrar seleccionado
        btn_row = QHBoxLayout()
        btn_del = QPushButton("🗑 Borrar seleccionado")
        btn_del.setFixedHeight(28)
        btn_del.setStyleSheet(
            "QPushButton { border:1px solid #FECACA; background:#FEF2F2; color:#DC2626;"
            "border-radius:4px; font-size:11px; padding:0 10px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn_del.clicked.connect(self._on_eliminar)
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedHeight(28)
        btn_cerrar.setStyleSheet(
            "QPushButton { border-radius:4px; padding:0 14px; font-size:11px; }"
        )
        btn_cerrar.clicked.connect(self.accept)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_row.addWidget(btn_cerrar)
        lay.addLayout(btn_row)

    def _cargar_items(self) -> None:
        from database.facturas_items_repo import obtener_items_factura
        self._items = obtener_items_factura(self._factura.id)
        self._tabla.setRowCount(0)
        self._tabla.setRowCount(len(self._items))
        total = 0.0
        for row, it in enumerate(self._items):
            self._tabla.setRowHeight(row, 26)
            self._tabla.setItem(row, 0, QTableWidgetItem(str(row + 1)))
            self._tabla.setItem(row, 1, QTableWidgetItem(it["descripcion_item"]))
            it2 = QTableWidgetItem(f'{it["cantidad"]:.2f}')
            it2.setTextAlignment(Qt.AlignCenter)
            self._tabla.setItem(row, 2, it2)
            it3 = QTableWidgetItem(cop(it["precio_unitario"]))
            it3.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._tabla.setItem(row, 3, it3)
            sub = it["subtotal"]
            total += sub
            it4 = QTableWidgetItem(cop(sub))
            it4.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._tabla.setItem(row, 4, it4)
        self._lbl_total.setText(f"Total items: {cop(total)}")

    def _on_agregar(self) -> None:
        from database.facturas_items_repo import insertar_item
        desc = self._f_desc.text().strip()
        if not desc:
            self._lbl_fb.setText("La descripción es obligatoria.")
            return
        cant = self._f_cant.value()
        precio = float(self._f_precio.valor_int())
        insertar_item(self._factura.id, desc, cant, precio)
        self._f_desc.clear()
        self._f_cant.setValue(1)
        self._f_precio.clear()
        self._lbl_fb.setText("")
        self._cargar_items()

    def _on_eliminar(self) -> None:
        from database.facturas_items_repo import eliminar_item
        row = self._tabla.currentRow()
        if row < 0 or row >= len(self._items):
            self._lbl_fb.setText("Selecciona un item de la tabla.")
            return
        item_id = self._items[row]["id"]
        eliminar_item(item_id)
        self._cargar_items()


class _FacturasPorPagarPanel(QWidget):
    """Vista de gestión de facturas y recibos (sub-panel interno)."""

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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

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
            "color:#2563EB; font-weight:bold; }"
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
                "QLineEdit { border-radius:4px; padding:0 8px; }"
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
            "QLineEdit { border-radius:4px; padding:0 8px; }"
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
            "QDateEdit { border-radius:4px; padding:0 8px; }"
            "QDateEdit:focus { border:2px solid #F59E0B; }"
        )

        # Fecha vencimiento — siempre editable; botón para activar/desactivar
        self._f_vence = QDateEdit()
        self._f_vence.setDate(QDate.currentDate().addDays(30))
        self._f_vence.setCalendarPopup(True)
        self._f_vence.setFixedHeight(30); self._f_vence.setFixedWidth(140)
        self._f_vence.setDisplayFormat("dd/MM/yyyy")
        self._f_vence.setStyleSheet(
            "QDateEdit { border-radius:4px; padding:0 8px; }"
            "QDateEdit:focus { border:2px solid #F59E0B; }"
        )
        self._tiene_fecha_vence = True   # estado: ¿hay fecha límite activa?

        self._btn_limpiar_vence = QPushButton("× Sin fecha")
        self._btn_limpiar_vence.setFixedHeight(30)
        self._btn_limpiar_vence.setStyleSheet(
            "QPushButton { background:#FEF3C7; color:#92400E; border:1px solid #FDE68A;"
            "border-radius:4px; font-size:10px; padding:0 6px; }"
            "QPushButton:hover { background:#FDE68A; }"
        )
        self._btn_limpiar_vence.clicked.connect(self._toggle_fecha_vence)

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
            "QPushButton { border-radius:4px; padding:0 14px; }"
        )
        btn_cancelar.clicked.connect(self._on_cancelar_form)

        # Fecha llegada
        col_fl = QVBoxLayout(); col_fl.setSpacing(2)
        col_fl.addWidget(_lbl("Fecha llegada:")); col_fl.addWidget(self._f_fecha)
        fila2.addLayout(col_fl)

        # Fecha vencimiento (siempre visible + botón para quitar)
        col_fv = QVBoxLayout(); col_fv.setSpacing(2)
        fila_vence_lbl = QHBoxLayout(); fila_vence_lbl.setSpacing(4)
        fila_vence_lbl.addWidget(_lbl("Fecha límite:"))
        fila_vence_lbl.addWidget(self._btn_limpiar_vence)
        fila_vence_lbl.addStretch()
        col_fv.addLayout(fila_vence_lbl)
        col_fv.addWidget(self._f_vence)
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
        # Cols: ID(hidden)|Descripción|Proveedor|Monto|Fecha llegada|Vencimiento|Días|Estado|Fecha pago|Acciones
        self.tabla.setColumnCount(10)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Descripción", "Proveedor", "Monto",
            "Fecha llegada", "Vencimiento", "Días", "Estado", "Fecha pago", "Acciones"
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
        hh.setMinimumSectionSize(50)
        hh.setStretchLastSection(False)
        for col, w in [(1, 230), (2, 140), (3, 115), (4, 105), (5, 105),
                       (6, 60), (7, 100), (8, 105), (9, 210)]:
            hh.setSectionResizeMode(col, QHeaderView.Interactive)
            self.tabla.setColumnWidth(col, w)
        self.tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tabla.setMinimumHeight(180)

        return self.tabla

    # ---- Barra resumen ----

    def _barra_resumen(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; }"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 6, 14, 6)
        lay.setSpacing(16)

        self._lbl_total_facturas  = QLabel("0 facturas")
        self._lbl_total_pendiente = QLabel("Por pagar: $ 0")
        self._lbl_total_pagado    = QLabel("Pagado: $ 0")

        for lbl in (self._lbl_total_facturas, self._lbl_total_pendiente, self._lbl_total_pagado):
            lbl.setStyleSheet(
                "font-size:12px; font-weight:bold; color:#374151;"
                "background:transparent; border:none;"
            )
            lay.addWidget(lbl)

        # Separador
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#CBD5E1;")
        sep.setFixedHeight(18)
        lay.addWidget(sep)

        # Flujo de caja: vencidas | próx. 7d | próx. 30d
        lbl_flujo = QLabel("Flujo:")
        lbl_flujo.setStyleSheet(
            "font-size:11px; color:#6B7280; background:transparent; border:none;"
        )
        lay.addWidget(lbl_flujo)

        self._lbl_vencidas  = QLabel("Vencidas: $ 0")
        self._lbl_prox7     = QLabel("7 días: $ 0")
        self._lbl_prox30    = QLabel("30 días: $ 0")

        for lbl, color in (
            (self._lbl_vencidas, "#DC2626"),
            (self._lbl_prox7,    "#D97706"),
            (self._lbl_prox30,   "#1D4ED8"),
        ):
            lbl.setStyleSheet(
                f"font-size:11px; font-weight:bold; color:{color};"
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

            # Columna Fecha pago
            if f.fecha_pago:
                item_fp = QTableWidgetItem(f.fecha_pago.strftime("%d/%m/%Y"))
                item_fp.setTextAlignment(Qt.AlignCenter)
                item_fp.setForeground(QColor("#15803D"))
                self.tabla.setItem(row, 8, item_fp)
            else:
                item_fp = QTableWidgetItem("—")
                item_fp.setTextAlignment(Qt.AlignCenter)
                item_fp.setForeground(QColor("#9CA3AF"))
                self.tabla.setItem(row, 8, item_fp)

            self.tabla.setCellWidget(row, 9, self._widget_acciones(f.id, f.estado))

    def _celda(self, row, col, texto, alin=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(alin)
        if texto:
            item.setToolTip(str(texto))
        self.tabla.setItem(row, col, item)

    def _actualizar_resumen(self) -> None:
        todas = self._ctrl.cargar_todos()
        n = len(self._facturas)
        pendientes = [f for f in todas if f.estado == "pendiente"]
        por_pagar  = sum(f.monto for f in pendientes)
        pagado     = sum(f.monto for f in todas if f.estado == "pagada")

        self._lbl_total_facturas.setText(f"{n} factura{'s' if n != 1 else ''}")
        self._lbl_total_pendiente.setText(f"Por pagar: {cop(por_pagar)}")
        self._lbl_total_pagado.setText(f"Pagado: {cop(pagado)}")

        # Flujo de caja por rango de vencimiento
        vencidas = sum(
            f.monto for f in pendientes
            if f.dias_para_vencer is not None and f.dias_para_vencer < 0
        )
        prox7 = sum(
            f.monto for f in pendientes
            if f.dias_para_vencer is not None and 0 <= f.dias_para_vencer <= 7
        )
        prox30 = sum(
            f.monto for f in pendientes
            if f.dias_para_vencer is not None and 0 <= f.dias_para_vencer <= 30
        )
        self._lbl_vencidas.setText(f"Vencidas: {cop(vencidas)}")
        self._lbl_prox7.setText(f"7 días: {cop(prox7)}")
        self._lbl_prox30.setText(f"30 días: {cop(prox30)}")

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
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(5)

        _ESTILO_ICON = (
            "QPushButton {{ background:{bg}; color:{fg}; border:1px solid {brd};"
            "border-radius:4px; font-size:14px; }}"
            "QPushButton:hover {{ background:{hov}; }}"
        )

        def _icon_btn(emoji, tooltip, bg, fg, brd, hov, handler):
            btn = QPushButton(emoji)
            btn.setFixedSize(30, 26)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(
                _ESTILO_ICON.format(bg=bg, fg=fg, brd=brd, hov=hov)
            )
            btn.clicked.connect(handler)
            return btn

        if estado == "pendiente":
            btn_abonar = QPushButton("Abonar")
            btn_abonar.setFixedHeight(26)
            btn_abonar.setMinimumWidth(62)
            btn_abonar.setStyleSheet(
                "QPushButton { background:#FEF3C7; color:#92400E; border:1px solid #FDE68A;"
                "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
                "QPushButton:hover { background:#FDE68A; }"
            )
            btn_abonar.clicked.connect(lambda _, fid=factura_id: self._on_abonar_factura(fid))
            lay.addWidget(btn_abonar)

            btn_pagar = QPushButton("Pagada ✓")
            btn_pagar.setFixedHeight(26)
            btn_pagar.setMinimumWidth(76)
            btn_pagar.setStyleSheet(
                "QPushButton { background:#DCFCE7; color:#15803D; border:1px solid #86EFAC;"
                "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
                "QPushButton:hover { background:#BBF7D0; }"
            )
            btn_pagar.clicked.connect(lambda _, fid=factura_id: self._on_marcar_pagada(fid))
            lay.addWidget(btn_pagar)

        lay.addWidget(_icon_btn(
            "📋", "Ver ítems",
            "#F0FDF4", "#15803D", "#86EFAC", "#DCFCE7",
            lambda _, fid=factura_id: self._on_ver_items(fid),
        ))
        lay.addWidget(_icon_btn(
            "✏", "Editar factura",
            "#EFF6FF", "#1D4ED8", "#BFDBFE", "#DBEAFE",
            lambda _, fid=factura_id: self._on_editar(fid),
        ))
        lay.addWidget(_icon_btn(
            "🗑", "Borrar factura",
            "#FEF2F2", "#DC2626", "#FECACA", "#FEE2E2",
            lambda _, fid=factura_id: self._on_eliminar(fid),
        ))
        lay.addStretch()
        return w

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_ver_items(self, factura_id: int) -> None:
        f = next((x for x in self._facturas if x.id == factura_id), None)
        if not f:
            todas = self._ctrl.cargar_todos()
            f = next((x for x in todas if x.id == factura_id), None)
        if not f:
            return
        dlg = _ItemsFacturaDialog(f, self)
        dlg.exec()

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
            self._tiene_fecha_vence = True
            self._f_vence.setEnabled(True)
            self._f_vence.setStyleSheet(
                "QDateEdit { border-radius:4px; padding:0 8px; }"
                "QDateEdit:focus { border:2px solid #F59E0B; }"
            )
            self._btn_limpiar_vence.setText("× Sin fecha")
            qv = QDate(f.fecha_vencimiento.year, f.fecha_vencimiento.month, f.fecha_vencimiento.day)
            self._f_vence.setDate(qv)
        else:
            self._tiene_fecha_vence = False
            self._f_vence.setEnabled(False)
            self._f_vence.setStyleSheet(
                "QDateEdit { border-radius:4px; padding:0 8px; color:#9CA3AF; }"
            )
            self._btn_limpiar_vence.setText("+ Con fecha")
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
        if self._tiene_fecha_vence:
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

        # Calcular monto restante (descontando abonos ya registrados)
        ya_abonado = self._ctrl.total_abonado(factura_id)
        monto_total = f.monto if f else 0.0
        restante = max(0.0, monto_total - ya_abonado)

        dlg = QDialog(self)
        dlg.setWindowTitle("Registrar pago")
        dlg.setFixedWidth(400)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        lbl = QLabel(f"Factura: <b>{nombre}</b>")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size:12px; color:#374151;")
        lay.addWidget(lbl)

        # Resumen de montos (visible si hay abonos previos)
        if ya_abonado > 0:
            lbl_montos = QLabel(
                f"Total: {cop(monto_total)}  |  Abonado: {cop(ya_abonado)}  "
                f"|  A pagar ahora: {cop(restante)}"
            )
            lbl_montos.setStyleSheet(
                "font-size:11px; color:#0369A1; background:#EFF6FF;"
                "border-radius:5px; padding:5px 8px;"
            )
            lay.addWidget(lbl_montos)

        lbl_fecha = QLabel("Fecha de pago:")
        lbl_fecha.setStyleSheet("font-size:11px; color:#6B7280;")
        lay.addWidget(lbl_fecha)

        f_picker = QDateEdit()
        f_picker.setDate(QDate.currentDate())
        f_picker.setCalendarPopup(True)
        f_picker.setDisplayFormat("dd/MM/yyyy")
        f_picker.setFixedHeight(30)
        f_picker.setStyleSheet(
            "QDateEdit { border:1px solid #D1D5DB; border-radius:4px; padding:0 8px; }"
        )
        lay.addWidget(f_picker)

        # Selector de cuenta de pago
        lbl_cta = QLabel(
            f"Cuenta de pago ({cop(restante)}):" if restante > 0 else "Cuenta de pago:"
        )
        lbl_cta.setStyleSheet("font-size:11px; color:#6B7280;")
        lay.addWidget(lbl_cta)

        combo_cuenta = QComboBox()
        combo_cuenta.setFixedHeight(30)
        combo_cuenta.setStyleSheet(
            "QComboBox { border:1px solid #D1D5DB; border-radius:4px; padding:0 8px;"
            " font-size:12px; }"
        )
        combo_cuenta.addItem("— Sin descontar de cuentas —", None)
        try:
            from database.cuentas_repo import obtener_todas as _cuentas
            for c in _cuentas():
                combo_cuenta.addItem(f"{c.nombre}  ({cop(c.balance_actual)})", c.id)
        except Exception:
            pass
        lay.addWidget(combo_cuenta)

        btns = QHBoxLayout(); btns.setSpacing(8)
        btn_ok = QPushButton("Confirmar pago")
        btn_ok.setFixedHeight(30)
        btn_ok.setStyleSheet(
            "QPushButton { background:#15803D; color:white; border-radius:4px;"
            "padding:0 14px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#166534; }"
        )
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setFixedHeight(30)
        btn_cancel.setStyleSheet(
            "QPushButton { border-radius:4px; padding:0 14px; }"
        )
        btn_ok.clicked.connect(dlg.accept)
        btn_cancel.clicked.connect(dlg.reject)
        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)
        lay.addLayout(btns)

        if dlg.exec() == QDialog.Accepted:
            qd = f_picker.date()
            fecha_pago = date(qd.year(), qd.month(), qd.day())
            cuenta_id = combo_cuenta.currentData()
            self._ctrl.marcar_pagada(factura_id, fecha_pago, cuenta_id)
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

    def _toggle_fecha_vence(self) -> None:
        self._tiene_fecha_vence = not self._tiene_fecha_vence
        self._f_vence.setEnabled(self._tiene_fecha_vence)
        if self._tiene_fecha_vence:
            self._btn_limpiar_vence.setText("× Sin fecha")
            self._f_vence.setDate(QDate.currentDate().addDays(30))
            self._f_vence.setStyleSheet(
                "QDateEdit { border-radius:4px; padding:0 8px; color:#111827; }"
                "QDateEdit:focus { border:2px solid #F59E0B; }"
            )
        else:
            self._btn_limpiar_vence.setText("+ Con fecha")
            self._f_vence.setStyleSheet(
                "QDateEdit { border-radius:4px; padding:0 8px; color:#9CA3AF; }"
            )

    def _limpiar_form(self) -> None:
        self._f_descripcion.clear()
        self._f_proveedor.clear()
        self._f_monto.clear()
        self._f_fecha.setDate(QDate.currentDate())
        self._f_notas.clear()
        self._tiene_fecha_vence = True
        self._f_vence.setEnabled(True)
        self._f_vence.setDate(QDate.currentDate().addDays(30))
        self._f_vence.setStyleSheet(
            "QDateEdit { border-radius:4px; padding:0 8px; }"
            "QDateEdit:focus { border:2px solid #F59E0B; }"
        )
        self._btn_limpiar_vence.setText("× Sin fecha")


# ──────────────────────────────────────────────────────────────────────────────
# Wrapper público con pestañas
# ──────────────────────────────────────────────────────────────────────────────

class _DetalleProveedorDialog(QDialog):
    """Muestra todas las facturas de un proveedor con resumen de pagos."""

    def __init__(self, proveedor: str, facturas: list, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Facturas — {proveedor}")
        self.setMinimumSize(720, 440)
        self._proveedor = proveedor
        self._facturas = facturas
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # Encabezado con chips de resumen
        h = QHBoxLayout(); h.setSpacing(12)
        lbl = QLabel(f"📦  {self._proveedor}")
        fnt = QFont(); fnt.setPointSize(13); fnt.setBold(True)
        lbl.setFont(fnt)
        h.addWidget(lbl); h.addStretch()

        total     = sum(f.monto for f in self._facturas)
        pagado    = sum(f.monto for f in self._facturas if f.estado == "pagada")
        pendiente = total - pagado

        for titulo, valor, color in [
            ("Total facturado", total,     "#1E293B"),
            ("Total pagado",    pagado,    "#15803D"),
            ("Total pendiente", pendiente, "#DC2626" if pendiente > 0 else "#15803D"),
        ]:
            chip = QFrame()
            chip.setStyleSheet(
                "QFrame { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; }"
            )
            cl = QVBoxLayout(chip); cl.setContentsMargins(12, 6, 12, 6); cl.setSpacing(2)
            lt = QLabel(titulo.upper())
            lt.setStyleSheet("color:#9CA3AF; font-size:9px; font-weight:bold;")
            lv = QLabel(cop(valor))
            fnt2 = QFont(); fnt2.setPointSize(12); fnt2.setBold(True)
            lv.setFont(fnt2); lv.setStyleSheet(f"color:{color};")
            cl.addWidget(lt); cl.addWidget(lv)
            h.addWidget(chip)

        root.addLayout(h)

        # Tabla de facturas del proveedor
        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels(
            ["Fecha llegada", "Descripción", "Monto", "Estado", "Fecha pago"]
        )
        tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabla.verticalHeader().setVisible(False)
        tabla.setShowGrid(False)
        tabla.setAlternatingRowColors(True)
        tabla.setStyleSheet("""
            QTableWidget { border:1px solid #E5E7EB; border-radius:6px; font-size:12px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:11px; padding:6px; border:none;
            }
        """)
        hh = tabla.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Interactive); tabla.setColumnWidth(0, 110)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); tabla.setColumnWidth(2, 120)
        hh.setSectionResizeMode(3, QHeaderView.Interactive); tabla.setColumnWidth(3, 90)
        hh.setSectionResizeMode(4, QHeaderView.Interactive); tabla.setColumnWidth(4, 110)

        facturas_ord = sorted(self._facturas, key=lambda x: x.fecha_llegada, reverse=True)
        tabla.setRowCount(len(facturas_ord))
        for row, fac in enumerate(facturas_ord):
            tabla.setRowHeight(row, 30)
            it0 = QTableWidgetItem(fac.fecha_llegada.strftime("%d/%m/%Y"))
            it0.setTextAlignment(Qt.AlignCenter)
            tabla.setItem(row, 0, it0)
            tabla.setItem(row, 1, QTableWidgetItem(fac.descripcion))
            it_m = QTableWidgetItem(cop(fac.monto))
            it_m.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tabla.setItem(row, 2, it_m)
            estilo = _ESTADO_ESTILO.get(fac.estado, ("#F3F4F6", "#374151", fac.estado.upper()))
            it_e = QTableWidgetItem(estilo[2])
            it_e.setTextAlignment(Qt.AlignCenter)
            it_e.setForeground(QColor(estilo[1]))
            tabla.setItem(row, 3, it_e)
            fp = fac.fecha_pago.strftime("%d/%m/%Y") if fac.fecha_pago else "—"
            it_fp = QTableWidgetItem(fp)
            it_fp.setTextAlignment(Qt.AlignCenter)
            tabla.setItem(row, 4, it_fp)

        root.addWidget(tabla)

        btn = QPushButton("Cerrar")
        btn.setFixedHeight(36)
        btn.clicked.connect(self.accept)
        fila = QHBoxLayout(); fila.addStretch(); fila.addWidget(btn)
        root.addLayout(fila)


class _ProveedoresPanel(QWidget):
    """Reporte de proveedores: KPIs globales + tabla detallada + drill-down por proveedor."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._datos_cache: list[dict] = []
        self._facturas_por_prov: dict[str, list] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        # ── Barra superior ────────────────────────────────────────
        barra = QHBoxLayout()
        titulo = QLabel("Reporte de Proveedores")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        titulo.setFont(f)

        self._busq = QLineEdit()
        self._busq.setPlaceholderText("Filtrar por proveedor…")
        self._busq.setFixedHeight(32)
        self._busq.setFixedWidth(200)
        self._busq.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:5px; padding:0 10px; }"
        )
        self._busq.textChanged.connect(self._filtrar)

        lbl_hint = QLabel("Doble clic en un proveedor para ver sus facturas")
        lbl_hint.setStyleSheet("color:#9CA3AF; font-size:11px; font-style:italic;")

        barra.addWidget(titulo)
        barra.addSpacing(16)
        barra.addWidget(self._busq)
        barra.addStretch()
        barra.addWidget(lbl_hint)
        root.addLayout(barra)

        # ── KPI cards ─────────────────────────────────────────────
        kpi_row = QHBoxLayout(); kpi_row.setSpacing(12)
        self._kpi_proveedores = self._kpi("Proveedores",      "0",   "#2563EB")
        self._kpi_total       = self._kpi("Total facturado",  "$ 0", "#374151")
        self._kpi_pagado      = self._kpi("Total pagado",     "$ 0", "#15803D")
        self._kpi_pendiente   = self._kpi("Total pendiente",  "$ 0", "#DC2626")
        for w in (self._kpi_proveedores, self._kpi_total, self._kpi_pagado, self._kpi_pendiente):
            kpi_row.addWidget(w)
        root.addLayout(kpi_row)

        # ── Tabla ─────────────────────────────────────────────────
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(8)
        self._tabla.setHorizontalHeaderLabels([
            "Proveedor", "Facturas", "Pendientes", "Pagadas",
            "Total facturado", "Total pagado", "Total pendiente", "% pagado",
        ])
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setShowGrid(False)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setStyleSheet("""
            QTableWidget { border:1px solid #E5E7EB; border-radius:8px; font-size:12px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:11px; padding:6px; border:none;
            }
            QTableWidget::item:selected { background:#FEF9C3; color:#78350F; }
        """)
        hh = self._tabla.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); self._tabla.setColumnWidth(1, 75)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); self._tabla.setColumnWidth(2, 90)
        hh.setSectionResizeMode(3, QHeaderView.Interactive); self._tabla.setColumnWidth(3, 75)
        hh.setSectionResizeMode(4, QHeaderView.Interactive); self._tabla.setColumnWidth(4, 130)
        hh.setSectionResizeMode(5, QHeaderView.Interactive); self._tabla.setColumnWidth(5, 115)
        hh.setSectionResizeMode(6, QHeaderView.Interactive); self._tabla.setColumnWidth(6, 130)
        hh.setSectionResizeMode(7, QHeaderView.Interactive); self._tabla.setColumnWidth(7, 80)
        self._tabla.doubleClicked.connect(self._on_doble_clic)
        root.addWidget(self._tabla, stretch=1)

    def _kpi(self, titulo: str, valor: str, color: str) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(2)
        lt = QLabel(titulo.upper())
        lt.setStyleSheet("color:#9CA3AF; font-size:9px; font-weight:bold;")
        lv = QLabel(valor)
        fnt = QFont(); fnt.setPointSize(15); fnt.setBold(True)
        lv.setFont(fnt)
        lv.setStyleSheet(f"color:{color};")
        lay.addWidget(lt)
        lay.addWidget(lv)
        frame._lbl = lv
        return frame

    def refresh(self) -> None:
        from collections import defaultdict
        todas = FacturasController().cargar_todos()

        grupos: dict[str, dict] = defaultdict(
            lambda: {"total": 0, "pendientes": 0, "pagadas": 0,
                     "monto_total": 0.0, "monto_pendiente": 0.0}
        )
        self._facturas_por_prov = defaultdict(list)

        for f in todas:
            prov = f.proveedor or "(Sin proveedor)"
            g = grupos[prov]
            g["total"] += 1
            g["monto_total"] += f.monto
            if f.estado == "pendiente":
                g["pendientes"] += 1
                g["monto_pendiente"] += f.monto
            else:
                g["pagadas"] += 1
            self._facturas_por_prov[prov].append(f)

        self._datos_cache = [
            {"proveedor": prov, **d}
            for prov, d in sorted(grupos.items(), key=lambda x: -x[1]["monto_total"])
        ]

        gran_total     = sum(d["monto_total"]     for d in self._datos_cache)
        gran_pendiente = sum(d["monto_pendiente"] for d in self._datos_cache)
        gran_pagado    = gran_total - gran_pendiente
        self._kpi_proveedores._lbl.setText(str(len(self._datos_cache)))
        self._kpi_total._lbl.setText(cop(gran_total))
        self._kpi_pagado._lbl.setText(cop(gran_pagado))
        self._kpi_pendiente._lbl.setText(cop(gran_pendiente))

        self._filtrar(self._busq.text())

    def _filtrar(self, texto: str = "") -> None:
        texto = texto.strip().lower()
        datos = [
            d for d in self._datos_cache
            if not texto or texto in d["proveedor"].lower()
        ]
        self._tabla.setRowCount(0)
        self._tabla.setRowCount(len(datos))
        for row, d in enumerate(datos):
            self._tabla.setRowHeight(row, 32)
            self._tabla.setItem(row, 0, QTableWidgetItem(d["proveedor"]))

            for col, val in [(1, d["total"]), (2, d["pendientes"]), (3, d["pagadas"])]:
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                if col == 2 and val > 0:
                    it.setForeground(QColor("#D97706"))
                self._tabla.setItem(row, col, it)

            monto_pagado = d["monto_total"] - d["monto_pendiente"]
            pct = round(monto_pagado / d["monto_total"] * 100) if d["monto_total"] > 0 else 0

            it_mt = QTableWidgetItem(cop(d["monto_total"]))
            it_mt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._tabla.setItem(row, 4, it_mt)

            it_pg = QTableWidgetItem(cop(monto_pagado))
            it_pg.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_pg.setForeground(QColor("#15803D"))
            self._tabla.setItem(row, 5, it_pg)

            it_pend = QTableWidgetItem(cop(d["monto_pendiente"]))
            it_pend.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_pend.setForeground(
                QColor("#DC2626") if d["monto_pendiente"] > 0 else QColor("#15803D")
            )
            self._tabla.setItem(row, 6, it_pend)

            it_pct = QTableWidgetItem(f"{pct} %")
            it_pct.setTextAlignment(Qt.AlignCenter)
            color_pct = "#15803D" if pct >= 90 else "#D97706" if pct >= 50 else "#DC2626"
            it_pct.setForeground(QColor(color_pct))
            self._tabla.setItem(row, 7, it_pct)

    def _on_doble_clic(self, index) -> None:
        it = self._tabla.item(index.row(), 0)
        if it is None:
            return
        prov = it.text()
        facturas = list(self._facturas_por_prov.get(prov, []))
        dlg = _DetalleProveedorDialog(prov, facturas, self)
        dlg.exec()


class FacturasPanel(QWidget):
    """
    Contenedor de dos pestañas:
      • Facturas por pagar  → _FacturasPorPagarPanel (CRUD existente)
      • Cargue de pedidos   → CarguesPedidosWidget   (importar PDF de cascos)
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        from ui.cargue_pedidos_widget import CarguesPedidosWidget

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #F8FAFC;
            }
            QTabBar::tab {
                background: #E2E8F0;
                color: #374151;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 3px;
            }
            QTabBar::tab:selected {
                background: #1E293B;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background: #CBD5E1;
            }
        """)

        self._panel_facturas = _FacturasPorPagarPanel()
        self._panel_cargue   = CarguesPedidosWidget()
        self._panel_prov     = _ProveedoresPanel()

        self._tabs.addTab(self._panel_facturas, "🧾  Facturas por pagar")
        self._tabs.addTab(self._panel_prov,     "🏭  Proveedores")
        self._tabs.addTab(self._panel_cargue,   "📦  Cargue de pedidos → Inventario")
        self._tabs.currentChanged.connect(self._on_tab_changed)

        lay.addWidget(self._tabs)

    def _on_tab_changed(self, idx: int) -> None:
        if self._tabs.tabText(idx).startswith("🏭"):
            self._panel_prov.refresh()

    def refresh(self) -> None:
        self._panel_facturas.refresh()
