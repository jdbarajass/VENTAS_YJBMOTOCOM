"""
ui/cuentas_panel.py
Panel de Cuentas — visible solo para Admin.

3 pestañas:
  • Resumen     — tarjetas de saldo por cuenta + transferencias
  • Movimientos — historial filtrable
  • Cierres     — cierres mensuales
"""

import json
from datetime import date, datetime

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QGridLayout, QDialog, QFormLayout, QLineEdit,
    QDoubleSpinBox, QDialogButtonBox, QComboBox, QDateEdit,
    QTextEdit, QMessageBox, QSizePolicy,
)

from database.cuentas_repo import (
    obtener_todas,
    actualizar_balance_manual,
    registrar_transferencia,
    obtener_movimientos,
    hacer_cierre_mes,
    obtener_cierres,
)
from ui.styles import es_modo_oscuro
from utils.formatters import cop as formatear_cop


# ── Paleta ────────────────────────────────────────────────────────────────────

def _bg() -> str:
    return "#0F172A" if es_modo_oscuro() else "#F8FAFC"

def _card_bg() -> str:
    return "#1E293B" if es_modo_oscuro() else "#FFFFFF"

def _txt() -> str:
    return "#F1F5F9" if es_modo_oscuro() else "#111827"

def _txt_sec() -> str:
    return "#94A3B8" if es_modo_oscuro() else "#6B7280"

def _border() -> str:
    return "#334155" if es_modo_oscuro() else "#E5E7EB"

def _table_alt() -> str:
    return "#1E293B" if es_modo_oscuro() else "#F9FAFB"


# ── Diálogo: ajuste manual de saldo ──────────────────────────────────────────

class _DialogoAjuste(QDialog):
    def __init__(self, cuenta, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Ajustar saldo — {cuenta.nombre}")
        self.setMinimumWidth(360)
        self._cuenta = cuenta

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(20, 16, 20, 16)

        form = QFormLayout()
        form.setSpacing(10)

        lbl_actual = QLabel(formatear_cop(cuenta.balance_actual))
        lbl_actual.setStyleSheet("font-size:15px; font-weight:bold; color:#3B82F6;")
        form.addRow("Saldo actual:", lbl_actual)

        self._spin = QDoubleSpinBox()
        self._spin.setDecimals(0)
        self._spin.setRange(-999_999_999, 999_999_999)
        self._spin.setSingleStep(1000)
        self._spin.setValue(cuenta.balance_actual)
        self._spin.setFixedHeight(34)
        self._spin.setStyleSheet(
            "QDoubleSpinBox { border-radius:6px; padding:0 10px; font-size:13px; "
            "height:34px; border:1px solid #D1D5DB; }"
        )
        form.addRow("Nuevo saldo:", self._spin)

        self._campo_desc = QLineEdit()
        self._campo_desc.setPlaceholderText("Motivo del ajuste (opcional)")
        self._campo_desc.setFixedHeight(34)
        self._campo_desc.setStyleSheet(
            "QLineEdit { border-radius:6px; padding:0 10px; font-size:12px; "
            "height:34px; border:1px solid #D1D5DB; }"
        )
        form.addRow("Descripción:", self._campo_desc)

        lay.addLayout(form)

        bts = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bts.accepted.connect(self.accept)
        bts.rejected.connect(self.reject)
        bts.button(QDialogButtonBox.Ok).setText("Guardar")
        bts.button(QDialogButtonBox.Cancel).setText("Cancelar")
        lay.addWidget(bts)

    @property
    def nuevo_balance(self) -> float:
        return self._spin.value()

    @property
    def descripcion(self) -> str:
        return self._campo_desc.text().strip() or "Ajuste manual"


# ── Diálogo: transferencia entre cuentas ─────────────────────────────────────

class _DialogoTransferencia(QDialog):
    def __init__(self, cuentas, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transferir entre cuentas")
        self.setMinimumWidth(380)

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(20, 16, 20, 16)

        _combo_style = (
            "QComboBox { border-radius:6px; padding:0 10px; font-size:12px; height:34px; "
            "border:1px solid #D1D5DB; background:#FFFFFF; color:#111827; }"
            "QComboBox QAbstractItemView { background:#FFFFFF; color:#111827; "
            "border:1px solid #E5E7EB; selection-background-color:#EFF6FF; "
            "selection-color:#1D4ED8; }"
        )
        _input_style = (
            "QDoubleSpinBox, QLineEdit { border-radius:6px; padding:0 10px; font-size:12px; "
            "height:34px; border:1px solid #D1D5DB; }"
        )

        form = QFormLayout()
        form.setSpacing(10)

        self._combo_desde = QComboBox()
        self._combo_hasta = QComboBox()
        for c in cuentas:
            self._combo_desde.addItem(f"{c.nombre}  ({formatear_cop(c.balance_actual)})", c.id)
            self._combo_hasta.addItem(c.nombre, c.id)
        self._combo_desde.setFixedHeight(34)
        self._combo_hasta.setFixedHeight(34)
        self._combo_desde.setStyleSheet(_combo_style)
        self._combo_hasta.setStyleSheet(_combo_style)
        form.addRow("Desde:", self._combo_desde)
        form.addRow("Hacia:", self._combo_hasta)

        self._spin_monto = QDoubleSpinBox()
        self._spin_monto.setDecimals(0)
        self._spin_monto.setRange(1, 999_999_999)
        self._spin_monto.setSingleStep(10_000)
        self._spin_monto.setFixedHeight(34)
        self._spin_monto.setStyleSheet(_input_style)
        form.addRow("Monto:", self._spin_monto)

        self._campo_desc = QLineEdit()
        self._campo_desc.setPlaceholderText("Descripción (opcional)")
        self._campo_desc.setFixedHeight(34)
        self._campo_desc.setStyleSheet(_input_style)
        form.addRow("Descripción:", self._campo_desc)

        lay.addLayout(form)

        bts = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bts.accepted.connect(self._on_aceptar)
        bts.rejected.connect(self.reject)
        bts.button(QDialogButtonBox.Ok).setText("Transferir")
        bts.button(QDialogButtonBox.Cancel).setText("Cancelar")
        lay.addWidget(bts)

    def _on_aceptar(self):
        if self._combo_desde.currentData() == self._combo_hasta.currentData():
            QMessageBox.warning(self, "Error", "Las cuentas de origen y destino deben ser distintas.")
            return
        self.accept()

    @property
    def desde_id(self) -> int:
        return self._combo_desde.currentData()

    @property
    def hasta_id(self) -> int:
        return self._combo_hasta.currentData()

    @property
    def monto(self) -> float:
        return self._spin_monto.value()

    @property
    def descripcion(self) -> str:
        return self._campo_desc.text().strip()


# ── Diálogo: cierre mensual ───────────────────────────────────────────────────

class _DialogoCierre(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Realizar Cierre del Mes")
        self.setMinimumWidth(360)

        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(20, 16, 20, 16)

        info = QLabel(
            "El cierre guarda el saldo actual de todas las cuentas.\n"
            "Úsalo al final de cada mes para dejar registro del estado."
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size:12px; color:#64748B;")
        lay.addWidget(info)

        form = QFormLayout()
        form.setSpacing(10)

        hoy = date.today()
        self._spin_anio = QDoubleSpinBox()
        self._spin_anio.setDecimals(0)
        self._spin_anio.setRange(2020, 2099)
        self._spin_anio.setValue(hoy.year)
        self._spin_anio.setFixedHeight(34)

        _meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                  "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        self._combo_mes = QComboBox()
        for m in _meses:
            self._combo_mes.addItem(m)
        self._combo_mes.setCurrentIndex(hoy.month - 1)
        self._combo_mes.setFixedHeight(34)

        _st = "font-size:12px; height:34px; border-radius:6px; border:1px solid #D1D5DB; padding:0 10px;"
        self._spin_anio.setStyleSheet(_st)
        self._combo_mes.setStyleSheet(
            "QComboBox { " + _st + " background:#FFFFFF; color:#111827; }"
            "QComboBox QAbstractItemView { background:#FFFFFF; color:#111827; }"
        )

        form.addRow("Año:", self._spin_anio)
        form.addRow("Mes:", self._combo_mes)

        self._campo_notas = QTextEdit()
        self._campo_notas.setPlaceholderText("Notas del cierre (opcional)…")
        self._campo_notas.setFixedHeight(70)
        form.addRow("Notas:", self._campo_notas)

        lay.addLayout(form)

        bts = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bts.accepted.connect(self.accept)
        bts.rejected.connect(self.reject)
        bts.button(QDialogButtonBox.Ok).setText("Hacer Cierre")
        bts.button(QDialogButtonBox.Cancel).setText("Cancelar")
        lay.addWidget(bts)

    @property
    def anio(self) -> int:
        return int(self._spin_anio.value())

    @property
    def mes(self) -> int:
        return self._combo_mes.currentIndex() + 1

    @property
    def notas(self) -> str:
        return self._campo_notas.toPlainText().strip()


# ── Tab 1: Resumen ────────────────────────────────────────────────────────────

class _TabResumen(QWidget):
    saldo_cambiado = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # Barra superior
        barra = QHBoxLayout()
        self._lbl_total = QLabel()
        self._lbl_total.setStyleSheet(f"font-size:16px; font-weight:bold; color:{_txt()};")
        barra.addWidget(self._lbl_total)
        barra.addStretch()

        btn_transferir = QPushButton("↔  Transferir")
        btn_transferir.setFixedHeight(34)
        btn_transferir.setStyleSheet(
            "QPushButton { background:#3B82F6; color:white; border-radius:5px;"
            "padding:0 16px; font-size:12px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#2563EB; }"
        )
        btn_transferir.clicked.connect(self._on_transferir)
        barra.addWidget(btn_transferir)

        btn_refresh = QPushButton("⟳  Actualizar")
        btn_refresh.setFixedHeight(34)
        btn_refresh.setStyleSheet(
            "QPushButton { background:#1E293B; color:#CBD5E1; border-radius:5px;"
            "padding:0 14px; font-size:12px; border:none; }"
            "QPushButton:hover { background:#334155; color:white; }"
        )
        btn_refresh.clicked.connect(self.refresh)
        barra.addWidget(btn_refresh)
        root.addLayout(barra)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{_border()};")
        root.addWidget(sep)

        # Área scroll con grid de tarjetas
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background:transparent; border:none;")

        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet("background:transparent;")
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setContentsMargins(0, 4, 0, 4)
        self._grid.setSpacing(12)
        self._scroll.setWidget(self._grid_widget)
        root.addWidget(self._scroll)

        # Nota informativa
        nota = QLabel(
            "Las ventas nuevas se acreditan automáticamente · "
            "Las ediciones y eliminaciones de ventas también actualizan el saldo automáticamente · "
            "Usa 'Ajustar' solo para correcciones manuales"
        )
        nota.setWordWrap(True)
        nota.setStyleSheet(f"font-size:10px; color:{_txt_sec()}; padding:4px 0;")
        root.addWidget(nota)

    def refresh(self):
        # Limpiar grid
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cuentas = obtener_todas()
        total = sum(c.balance_actual for c in cuentas)
        self._lbl_total.setText(f"Total en cuentas: {formatear_cop(total)}")

        for i, cuenta in enumerate(cuentas):
            row, col = divmod(i, 3)
            self._grid.addWidget(self._crear_tarjeta(cuenta), row, col)

        # Relleno para que no queden columnas vacías
        cols_usadas = min(len(cuentas), 3)
        for col in range(cols_usadas):
            self._grid.setColumnStretch(col, 1)

    def _crear_tarjeta(self, cuenta) -> QWidget:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setStyleSheet(
            f"QFrame {{ background:{_card_bg()}; border-radius:10px; "
            f"border:1px solid {_border()}; }}"
        )

        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        # Nombre con punto de color
        nombre_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{cuenta.color}; font-size:14px;")
        nombre_row.addWidget(dot)
        lbl_nombre = QLabel(cuenta.nombre)
        lbl_nombre.setStyleSheet(f"font-size:13px; font-weight:bold; color:{_txt()};")
        nombre_row.addWidget(lbl_nombre)
        nombre_row.addStretch()
        lay.addLayout(nombre_row)

        # Saldo
        lbl_saldo = QLabel(formatear_cop(cuenta.balance_actual))
        lbl_saldo.setStyleSheet(
            f"font-size:22px; font-weight:bold; color:{cuenta.color}; padding:4px 0;"
        )
        lay.addWidget(lbl_saldo)

        # Método de pago
        lbl_metodo = QLabel(cuenta.metodo_pago or "—")
        lbl_metodo.setStyleSheet(f"font-size:10px; color:{_txt_sec()};")
        lay.addWidget(lbl_metodo)

        # Botón ajustar
        btn_ajustar = QPushButton("✏  Ajustar saldo")
        btn_ajustar.setFixedHeight(30)
        btn_ajustar.setStyleSheet(
            "QPushButton { background:transparent; color:#3B82F6; border:1px solid #3B82F6; "
            "border-radius:5px; font-size:11px; padding:0 10px; }"
            "QPushButton:hover { background:#EFF6FF; }"
        )
        btn_ajustar.clicked.connect(lambda _, c=cuenta: self._on_ajustar(c))
        lay.addWidget(btn_ajustar)

        return card

    def _on_ajustar(self, cuenta):
        dlg = _DialogoAjuste(cuenta, self)
        if dlg.exec() == QDialog.Accepted:
            actualizar_balance_manual(cuenta.id, dlg.nuevo_balance, dlg.descripcion)
            self.refresh()
            self.saldo_cambiado.emit()

    def _on_transferir(self):
        cuentas = obtener_todas()
        if len(cuentas) < 2:
            QMessageBox.information(self, "Sin cuentas", "Se necesitan al menos 2 cuentas.")
            return
        dlg = _DialogoTransferencia(cuentas, self)
        if dlg.exec() == QDialog.Accepted:
            try:
                registrar_transferencia(dlg.desde_id, dlg.hasta_id, dlg.monto, dlg.descripcion)
                self.refresh()
                self.saldo_cambiado.emit()
            except ValueError as e:
                QMessageBox.warning(self, "Error en transferencia", str(e))


# ── Tab 2: Movimientos ────────────────────────────────────────────────────────

class _TabMovimientos(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Filtros
        filtros_row = QHBoxLayout()
        filtros_row.setSpacing(8)

        _combo_st = (
            "QComboBox { border-radius:5px; padding:0 10px; font-size:12px; height:32px; "
            "border:1px solid #D1D5DB; background:#FFFFFF; color:#111827; }"
            "QComboBox QAbstractItemView { background:#FFFFFF; color:#111827; "
            "selection-background-color:#EFF6FF; selection-color:#1D4ED8; }"
        )

        self._combo_cuenta = QComboBox()
        self._combo_cuenta.setFixedHeight(32)
        self._combo_cuenta.setStyleSheet(_combo_st)
        self._combo_cuenta.setMinimumWidth(160)
        filtros_row.addWidget(QLabel("Cuenta:"))
        filtros_row.addWidget(self._combo_cuenta)

        _date_st = (
            "QDateEdit { border-radius:5px; padding:0 8px; font-size:12px; height:32px; "
            "border:1px solid #D1D5DB; }"
        )
        hoy = QDate.currentDate()
        inicio_mes = QDate(hoy.year(), hoy.month(), 1)

        self._desde = QDateEdit(inicio_mes)
        self._desde.setCalendarPopup(True)
        self._desde.setFixedHeight(32)
        self._desde.setStyleSheet(_date_st)
        filtros_row.addWidget(QLabel("Desde:"))
        filtros_row.addWidget(self._desde)

        self._hasta = QDateEdit(hoy)
        self._hasta.setCalendarPopup(True)
        self._hasta.setFixedHeight(32)
        self._hasta.setStyleSheet(_date_st)
        filtros_row.addWidget(QLabel("Hasta:"))
        filtros_row.addWidget(self._hasta)

        btn_filtrar = QPushButton("Filtrar")
        btn_filtrar.setFixedHeight(32)
        btn_filtrar.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:5px; "
            "padding:0 14px; font-size:12px; border:none; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btn_filtrar.clicked.connect(self._cargar_movimientos)
        filtros_row.addWidget(btn_filtrar)
        filtros_row.addStretch()
        root.addLayout(filtros_row)

        # Tabla
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(6)
        self._tabla.setHorizontalHeaderLabels(
            ["Fecha", "Cuenta", "Tipo", "Monto", "Descripción", "ID Venta"]
        )
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        hdr = self._tabla.horizontalHeader()
        hdr.setSectionResizeMode(4, QHeaderView.Stretch)
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._tabla.setStyleSheet(
            f"QTableWidget {{ border:none; gridline-color:{_border()}; font-size:12px; }}"
            f"QHeaderView::section {{ background:{_card_bg()}; color:{_txt()}; "
            f"border-bottom:1px solid {_border()}; padding:6px 8px; font-size:12px; }}"
            f"QTableWidget::item:alternate {{ background:{_table_alt()}; }}"
        )
        self._tabla.setColumnWidth(0, 90)
        self._tabla.setColumnWidth(1, 130)
        self._tabla.setColumnWidth(2, 120)
        self._tabla.setColumnWidth(3, 110)
        self._tabla.setColumnWidth(5, 70)
        root.addWidget(self._tabla)

    def refresh(self):
        self._combo_cuenta.blockSignals(True)
        cuenta_actual_id = self._combo_cuenta.currentData()
        self._combo_cuenta.clear()
        self._combo_cuenta.addItem("Todas las cuentas", None)
        for c in obtener_todas():
            self._combo_cuenta.addItem(c.nombre, c.id)
        # Restaurar selección
        for i in range(self._combo_cuenta.count()):
            if self._combo_cuenta.itemData(i) == cuenta_actual_id:
                self._combo_cuenta.setCurrentIndex(i)
                break
        self._combo_cuenta.blockSignals(False)
        self._cargar_movimientos()

    def _cargar_movimientos(self):
        cuenta_id = self._combo_cuenta.currentData()
        desde_str = self._desde.date().toString("yyyy-MM-dd")
        hasta_str = self._hasta.date().toString("yyyy-MM-dd")

        movs = obtener_movimientos(cuenta_id=cuenta_id, desde=desde_str, hasta=hasta_str)
        cuentas_map = {c.id: c for c in obtener_todas()}

        _TIPOS = {
            "venta": "Ingreso venta",
            "ajuste_manual": "Ajuste manual",
            "transferencia_salida": "Transferencia salida",
            "transferencia_entrada": "Transferencia entrada",
        }

        self._tabla.setRowCount(len(movs))
        for row, m in enumerate(movs):
            cuenta = cuentas_map.get(m.cuenta_id)
            cuenta_nombre = cuenta.nombre if cuenta else str(m.cuenta_id)
            tipo_label = _TIPOS.get(m.tipo, m.tipo)
            es_ingreso = m.monto >= 0
            monto_str = f"+ {formatear_cop(m.monto)}" if es_ingreso else f"- {formatear_cop(abs(m.monto))}"
            color_monto = "#22C55E" if es_ingreso else "#EF4444"

            celdas = [
                (0, m.fecha),
                (1, cuenta_nombre),
                (2, tipo_label),
                (3, monto_str),
                (4, m.descripcion),
                (5, str(m.venta_id) if m.venta_id else ""),
            ]
            for col, texto in celdas:
                item = QTableWidgetItem(str(texto))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if col == 3:
                    item.setForeground(QColor(color_monto))
                self._tabla.setItem(row, col, item)


# ── Tab 3: Cierres ────────────────────────────────────────────────────────────

class _TabCierres(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # Barra superior
        barra = QHBoxLayout()
        lbl = QLabel("Historial de cierres mensuales")
        lbl.setStyleSheet(f"font-size:13px; font-weight:bold; color:{_txt()};")
        barra.addWidget(lbl)
        barra.addStretch()

        btn_cierre = QPushButton("🔒  Realizar Cierre del Mes")
        btn_cierre.setFixedHeight(34)
        btn_cierre.setStyleSheet(
            "QPushButton { background:#7C3AED; color:white; border-radius:5px; "
            "padding:0 16px; font-size:12px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#6D28D9; }"
        )
        btn_cierre.clicked.connect(self._on_cierre)
        barra.addWidget(btn_cierre)
        root.addLayout(barra)

        # Tabla de cierres
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(4)
        self._tabla.setHorizontalHeaderLabels(["Mes / Año", "Fecha Cierre", "Notas", "Detalle"])
        self._tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        hdr = self._tabla.horizontalHeader()
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._tabla.setStyleSheet(
            f"QTableWidget {{ border:none; gridline-color:{_border()}; font-size:12px; }}"
            f"QHeaderView::section {{ background:{_card_bg()}; color:{_txt()}; "
            f"border-bottom:1px solid {_border()}; padding:6px 8px; font-size:12px; }}"
            f"QTableWidget::item:alternate {{ background:{_table_alt()}; }}"
        )
        self._tabla.setColumnWidth(0, 120)
        self._tabla.setColumnWidth(1, 160)
        self._tabla.setColumnWidth(3, 80)
        root.addWidget(self._tabla)

        # Info
        info = QLabel(
            "El cierre guarda un snapshot del saldo de todas las cuentas. "
            "No modifica los saldos — es solo un registro histórico."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"font-size:10px; color:{_txt_sec()};")
        root.addWidget(info)

    def refresh(self):
        _MESES = ["", "Ene","Feb","Mar","Abr","May","Jun",
                  "Jul","Ago","Sep","Oct","Nov","Dic"]
        cierres = obtener_cierres()
        self._tabla.setRowCount(len(cierres))
        for row, cierre in enumerate(cierres):
            mes_label = f"{_MESES[cierre.mes]} {cierre.anio}"
            fecha_fmt = cierre.fecha_cierre[:16].replace("T", "  ")
            celdas = [
                (0, mes_label),
                (1, fecha_fmt),
                (2, cierre.notas or "—"),
            ]
            for col, texto in celdas:
                item = QTableWidgetItem(texto)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self._tabla.setItem(row, col, item)
            # Botón ver detalle
            btn_ver = QPushButton("Ver")
            btn_ver.setStyleSheet(
                "QPushButton { background:#2563EB; color:white; border-radius:4px; "
                "font-size:11px; border:none; }"
                "QPushButton:hover { background:#1D4ED8; }"
            )
            btn_ver.clicked.connect(lambda _, c=cierre: self._ver_detalle(c))
            self._tabla.setCellWidget(row, 3, btn_ver)

    def _on_cierre(self):
        dlg = _DialogoCierre(self)
        if dlg.exec() == QDialog.Accepted:
            cierre = hacer_cierre_mes(dlg.anio, dlg.mes, dlg.notas)
            self.refresh()
            _MESES = ["","Ene","Feb","Mar","Abr","May","Jun",
                      "Jul","Ago","Sep","Oct","Nov","Dic"]
            QMessageBox.information(
                self, "Cierre realizado",
                f"Cierre de {_MESES[cierre.mes]} {cierre.anio} guardado correctamente."
            )

    def _ver_detalle(self, cierre):
        try:
            datos = json.loads(cierre.datos_json)
        except Exception:
            datos = []
        _MESES = ["","Ene","Feb","Mar","Abr","May","Jun",
                  "Jul","Ago","Sep","Oct","Nov","Dic"]
        lineas = [f"Cierre de {_MESES[cierre.mes]} {cierre.anio}\n"]
        for d in datos:
            lineas.append(f"  • {d['nombre']}: {formatear_cop(d['balance'])}")
        total = sum(d['balance'] for d in datos)
        lineas.append(f"\nTotal: {formatear_cop(total)}")
        QMessageBox.information(self, "Detalle del cierre", "\n".join(lineas))


# ── Panel principal ───────────────────────────────────────────────────────────

class CuentasPanel(QWidget):
    """Panel de Cuentas — solo Admin."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Encabezado
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(
            f"QFrame {{ background:{_card_bg()}; border-bottom:1px solid {_border()}; }}"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)

        lbl_titulo = QLabel("💳  Cuentas")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        lbl_titulo.setFont(f)
        lbl_titulo.setStyleSheet(f"color:{_txt()};")
        h_lay.addWidget(lbl_titulo)
        h_lay.addStretch()

        lbl_admin = QLabel("🔒 Solo Admin")
        lbl_admin.setStyleSheet("color:#EF4444; font-size:11px; font-weight:bold;")
        h_lay.addWidget(lbl_admin)

        root.addWidget(header)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            f"QTabWidget::pane {{ border:none; background:{_bg()}; }}"
            "QTabBar::tab { padding:8px 20px; font-size:12px; }"
            "QTabBar::tab:selected { font-weight:bold; border-bottom:2px solid #3B82F6; }"
        )

        self._tab_resumen = _TabResumen()
        self._tab_movimientos = _TabMovimientos()
        self._tab_cierres = _TabCierres()

        self._tabs.addTab(self._tab_resumen, "Resumen")
        self._tabs.addTab(self._tab_movimientos, "Movimientos")
        self._tabs.addTab(self._tab_cierres, "Cierres")

        # Cuando cambia saldo (ajuste/transferencia) → refrescar movimientos
        self._tab_resumen.saldo_cambiado.connect(self._tab_movimientos.refresh)

        root.addWidget(self._tabs)

    def refresh(self):
        """Refresca las tres pestañas."""
        self._tab_resumen.refresh()
        self._tab_movimientos.refresh()
        self._tab_cierres.refresh()
