"""
ui/calculadora_panel.py
Sección Calculadora de Precios.
Módulos: Precio de Venta · Cascos desde Factura · Calculadora Rápida
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QButtonGroup, QCheckBox, QCompleter,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import QFont, QColor

from ui.venta_form import MoneyLineEdit
from utils.formatters import cop

_GANANCIAS        = [25, 30, 35, 40, 45, 50, 55, 60, 65]
_DCTOS_CLIENTE    = [5, 10, 15, 20]
_DCTOS_PROVEEDOR  = [0, 3, 5, 8, 10]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers visuales
# ──────────────────────────────────────────────────────────────────────────────

def _lbl_titulo(texto: str, size: int = 13) -> QLabel:
    lbl = QLabel(texto)
    f = QFont(); f.setBold(True); f.setPointSize(size)
    lbl.setFont(f)
    lbl.setStyleSheet("color:#1E293B;")
    return lbl


def _sep_h() -> QFrame:
    sep = QFrame(); sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet("color:#E2E8F0;")
    return sep


def _sep_v() -> QFrame:
    sep = QFrame(); sep.setFrameShape(QFrame.VLine)
    sep.setStyleSheet("color:#E2E8F0;")
    return sep


class _ChipGroup(QWidget):
    """Fila de chips tipo pill — exclusivos entre sí."""

    def __init__(self, opciones: list[int], callback=None, parent=None):
        super().__init__(parent)
        self._callback = callback
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._btns: dict[int, QPushButton] = {}
        for op in opciones:
            btn = QPushButton(f"{op}%")
            btn.setCheckable(True)
            btn.setFixedHeight(26)
            btn.setFixedWidth(48)
            btn.setStyleSheet(
                "QPushButton{border:1px solid #CBD5E1;border-radius:13px;"
                "background:white;color:#374151;font-size:10px;font-weight:bold;}"
                "QPushButton:hover{background:#F1F5F9;}"
                "QPushButton:checked{background:#2563EB;color:white;border:1px solid #2563EB;}"
            )
            self._group.addButton(btn)
            self._btns[op] = btn
            lay.addWidget(btn)
        lay.addStretch()
        self._group.buttonClicked.connect(lambda _: (callback() if callback else None))

    def valor(self) -> int | None:
        for op, btn in self._btns.items():
            if btn.isChecked():
                return op
        return None

    def set_valor(self, v: int):
        if v in self._btns:
            self._btns[v].setChecked(True)

    def limpiar(self):
        self._group.setExclusive(False)
        for btn in self._btns.values():
            btn.setChecked(False)
        self._group.setExclusive(True)


# ──────────────────────────────────────────────────────────────────────────────
# Panel principal
# ──────────────────────────────────────────────────────────────────────────────

class CalculadoraPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    # ─── Layout principal ────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(10)

        # Cabecera
        cab = QHBoxLayout()
        cab.addWidget(_lbl_titulo("🧮  Calculadora de Precios", 15))
        cab.addSpacing(12)
        lbl_sub = QLabel("Calcula precios de venta, márgenes y costos de cascos desde factura")
        lbl_sub.setStyleSheet("color:#6B7280;font-size:11px;")
        cab.addWidget(lbl_sub)
        cab.addStretch()
        root.addLayout(cab)
        root.addWidget(_sep_h())

        # Cuerpo: izquierda | derecha
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(0)
        cuerpo.addWidget(self._panel_precio_venta(), stretch=5)
        cuerpo.addSpacing(12)
        cuerpo.addWidget(_sep_v())
        cuerpo.addSpacing(12)
        cuerpo.addWidget(self._panel_derecha(), stretch=5)
        root.addLayout(cuerpo, stretch=1)

    # ─── Panel izquierdo: Precio de Venta ────────────────────────────────

    def _panel_precio_venta(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(_lbl_titulo("Precio de Venta"))

        # Toggle Inventario / Manual
        row_toggle = QHBoxLayout(); row_toggle.setSpacing(6)
        self._btn_inv    = QPushButton("Desde Inventario")
        self._btn_manual = QPushButton("Manual")
        for btn, checked in [(self._btn_inv, True), (self._btn_manual, False)]:
            btn.setCheckable(True); btn.setChecked(checked)
            btn.setFixedHeight(28); btn.setFixedWidth(148)
            btn.setStyleSheet(
                "QPushButton{border:1px solid #CBD5E1;border-radius:5px;"
                "background:white;color:#374151;font-size:11px;font-weight:bold;}"
                "QPushButton:checked{background:#1E293B;color:white;border:1px solid #1E293B;}"
                "QPushButton:hover:!checked{background:#F1F5F9;}"
            )
        grp = QButtonGroup(self); grp.setExclusive(True)
        grp.addButton(self._btn_inv); grp.addButton(self._btn_manual)
        grp.buttonClicked.connect(self._on_toggle_modo)
        row_toggle.addWidget(self._btn_inv); row_toggle.addWidget(self._btn_manual)
        row_toggle.addStretch()
        lay.addLayout(row_toggle)

        # Buscar producto (solo visible en modo inventario)
        self._frame_buscar = QFrame()
        lay_b = QVBoxLayout(self._frame_buscar)
        lay_b.setContentsMargins(0, 0, 0, 0); lay_b.setSpacing(3)
        lbl_b = QLabel("Buscar producto en inventario:")
        lbl_b.setStyleSheet("font-size:10px;color:#6B7280;")
        self._campo_buscar = QLineEdit()
        self._campo_buscar.setPlaceholderText("Nombre o código de barras...")
        self._campo_buscar.setFixedHeight(32)
        self._campo_buscar.setStyleSheet(
            "QLineEdit{border:1px solid #D1D5DB;border-radius:5px;padding:0 8px;font-size:12px;}"
            "QLineEdit:focus{border:2px solid #2563EB;}"
        )
        self._cm = QStringListModel()
        self._completer = QCompleter(self._cm, self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._campo_buscar.setCompleter(self._completer)
        self._campo_buscar.textEdited.connect(self._on_buscar)
        self._completer.activated.connect(self._on_seleccionado)
        lay_b.addWidget(lbl_b); lay_b.addWidget(self._campo_buscar)
        lay.addWidget(self._frame_buscar)

        # Costo
        lbl_c = QLabel("Costo unitario ($):")
        lbl_c.setStyleSheet("font-size:10px;color:#6B7280;")
        self._costo = MoneyLineEdit()
        self._costo.setPlaceholderText("Ingresa el costo...")
        self._costo.setFixedHeight(38)
        self._costo.setStyleSheet(
            "QLineEdit{border:2px solid #E2E8F0;border-radius:6px;"
            "padding:0 10px;font-size:14px;font-weight:bold;color:#1E293B;}"
            "QLineEdit:focus{border:2px solid #2563EB;}"
        )
        self._costo.textChanged.connect(self._recalcular)
        lay.addWidget(lbl_c); lay.addWidget(self._costo)

        # % Ganancia
        lay.addWidget(_sep_h())
        lbl_g = QLabel("% Ganancia deseada:")
        lbl_g.setStyleSheet("font-size:10px;color:#6B7280;font-weight:bold;")
        lay.addWidget(lbl_g)
        self._chips_g = _ChipGroup(_GANANCIAS, self._recalcular)
        self._chips_g.set_valor(30)
        lay.addWidget(self._chips_g)

        # Resultado
        self._frame_res = QFrame()
        self._frame_res.setStyleSheet(
            "QFrame{background:#F0FDF4;border:2px solid #86EFAC;border-radius:10px;}"
        )
        lay_r = QVBoxLayout(self._frame_res)
        lay_r.setContentsMargins(16, 12, 16, 12); lay_r.setSpacing(4)
        self._lbl_pv = QLabel("Precio de venta:  —")
        f = QFont(); f.setBold(True); f.setPointSize(15)
        self._lbl_pv.setFont(f)
        self._lbl_pv.setStyleSheet("color:#15803D;background:transparent;border:none;")
        self._lbl_g_pesos = QLabel("Ganancia:  —")
        self._lbl_g_pesos.setStyleSheet("color:#374151;font-size:12px;background:transparent;border:none;")
        self._lbl_margen = QLabel("Margen sobre precio de venta:  —")
        self._lbl_margen.setStyleSheet("color:#6B7280;font-size:10px;background:transparent;border:none;")
        for lbl in (self._lbl_pv, self._lbl_g_pesos, self._lbl_margen):
            lay_r.addWidget(lbl)
        lay.addWidget(self._frame_res)

        # Descuento al cliente
        lay.addWidget(_sep_h())
        lbl_d = QLabel("Descuento al cliente (opcional):")
        lbl_d.setStyleSheet("font-size:10px;color:#6B7280;")
        lay.addWidget(lbl_d)
        self._chips_d = _ChipGroup(_DCTOS_CLIENTE, self._recalcular_dcto)
        lay.addWidget(self._chips_d)

        self._frame_dcto = QFrame()
        self._frame_dcto.setStyleSheet(
            "QFrame{background:#FEF9C3;border:1px solid #FDE68A;border-radius:8px;}"
        )
        lay_d = QHBoxLayout(self._frame_dcto)
        lay_d.setContentsMargins(12, 6, 12, 6)
        self._lbl_precio_dcto  = QLabel("Con descuento: —")
        self._lbl_precio_dcto.setStyleSheet(
            "font-size:12px;font-weight:bold;color:#92400E;background:transparent;border:none;"
        )
        self._lbl_margen_dcto = QLabel("")
        self._lbl_margen_dcto.setStyleSheet(
            "font-size:10px;color:#6B7280;background:transparent;border:none;"
        )
        lay_d.addWidget(self._lbl_precio_dcto)
        lay_d.addStretch()
        lay_d.addWidget(self._lbl_margen_dcto)
        self._frame_dcto.setVisible(False)
        lay.addWidget(self._frame_dcto)

        lay.addStretch()
        return w

    # ─── Panel derecho: Cascos + Rápida ──────────────────────────────────

    def _panel_derecha(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # ── Calculadora de Cascos ─────────────────────────────────────────
        lay.addWidget(_lbl_titulo("Calculadora de Cascos  (Factura proveedor)"))
        lbl_hint = QLabel(
            "Ingresa el precio que aparece en la factura (columna PRECIO, con IVA)"
        )
        lbl_hint.setStyleSheet("font-size:10px;color:#9CA3AF;")
        lay.addWidget(lbl_hint)

        # Precio en factura
        lbl_pf = QLabel("Precio en factura por unidad (con IVA):")
        lbl_pf.setStyleSheet("font-size:10px;color:#6B7280;")
        self._precio_factura = MoneyLineEdit()
        self._precio_factura.setPlaceholderText("ej.  302.500")
        self._precio_factura.setFixedHeight(36)
        self._precio_factura.setStyleSheet(
            "QLineEdit{border:2px solid #E2E8F0;border-radius:6px;"
            "padding:0 10px;font-size:13px;font-weight:bold;}"
            "QLineEdit:focus{border:2px solid #F59E0B;}"
        )
        self._precio_factura.textChanged.connect(self._recalcular_cascos)
        lay.addWidget(lbl_pf); lay.addWidget(self._precio_factura)

        # Descuento proveedor + IVA
        fila_opt = QHBoxLayout(); fila_opt.setSpacing(16)

        col_dp = QVBoxLayout(); col_dp.setSpacing(3)
        lbl_dp = QLabel("% Descuento proveedor:")
        lbl_dp.setStyleSheet("font-size:10px;color:#6B7280;")
        self._chips_dp = _ChipGroup(_DCTOS_PROVEEDOR, self._recalcular_cascos)
        self._chips_dp.set_valor(5)
        col_dp.addWidget(lbl_dp); col_dp.addWidget(self._chips_dp)
        fila_opt.addLayout(col_dp)

        col_iva = QVBoxLayout(); col_iva.setSpacing(3)
        lbl_iva = QLabel("IVA:"); lbl_iva.setStyleSheet("font-size:10px;color:#6B7280;")
        self._chk_iva = QCheckBox("Precio incluye IVA 19%")
        self._chk_iva.setChecked(True)
        self._chk_iva.setStyleSheet("font-size:10px;")
        self._chk_iva.toggled.connect(self._recalcular_cascos)
        col_iva.addWidget(lbl_iva); col_iva.addWidget(self._chk_iva)
        fila_opt.addLayout(col_iva)
        fila_opt.addStretch()
        lay.addLayout(fila_opt)

        # Costo real resultado
        self._frame_costo_real = QFrame()
        self._frame_costo_real.setStyleSheet(
            "QFrame{background:#FFF7ED;border:2px solid #FED7AA;border-radius:8px;}"
        )
        lay_cr = QHBoxLayout(self._frame_costo_real)
        lay_cr.setContentsMargins(12, 8, 12, 8)
        lbl_cr_t = QLabel("Costo real por casco:")
        lbl_cr_t.setStyleSheet("font-size:11px;color:#92400E;background:transparent;border:none;")
        self._lbl_costo_real = QLabel("—")
        fc = QFont(); fc.setBold(True); fc.setPointSize(14)
        self._lbl_costo_real.setFont(fc)
        self._lbl_costo_real.setStyleSheet("color:#C2410C;background:transparent;border:none;")
        lay_cr.addWidget(lbl_cr_t); lay_cr.addStretch(); lay_cr.addWidget(self._lbl_costo_real)
        lay.addWidget(self._frame_costo_real)

        # Tabla comparativa
        lbl_t = QLabel("Tabla de precios de venta según % ganancia:")
        lbl_t.setStyleSheet("font-size:10px;color:#6B7280;font-weight:bold;")
        lay.addWidget(lbl_t)

        self._tabla = QTableWidget()
        self._tabla.setColumnCount(3)
        self._tabla.setHorizontalHeaderLabels(["% Ganancia", "Precio de venta", "Ganancia $"])
        self._tabla.setRowCount(len(_GANANCIAS))
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setShowGrid(False)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setFixedHeight(26 * len(_GANANCIAS) + 32)
        self._tabla.setStyleSheet("""
            QTableWidget{border:none;font-size:11px;}
            QTableWidget::item{padding:2px 8px;}
            QHeaderView::section{background:#334155;color:white;
                font-weight:bold;font-size:10px;padding:4px;border:none;}
            QTableWidget::item:selected{background:#FEF3C7;color:#92400E;}
        """)
        hh = self._tabla.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed);   self._tabla.setColumnWidth(0, 72)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        for i, pct in enumerate(_GANANCIAS):
            self._tabla.setRowHeight(i, 24)
            it = QTableWidgetItem(f"{pct}%")
            it.setTextAlignment(Qt.AlignCenter)
            self._tabla.setItem(i, 0, it)
            self._tabla.setItem(i, 1, QTableWidgetItem("—"))
            self._tabla.setItem(i, 2, QTableWidgetItem("—"))
        lay.addWidget(self._tabla)

        # ── Calculadora Rápida ────────────────────────────────────────────
        lay.addWidget(_sep_h())
        lay.addWidget(_lbl_titulo("Calculadora Rápida", 11))
        lbl_r = QLabel("Costo + precio → ganancia instantánea")
        lbl_r.setStyleSheet("font-size:10px;color:#9CA3AF;")
        lay.addWidget(lbl_r)

        fila_r = QHBoxLayout(); fila_r.setSpacing(8)
        for attr, placeholder in [("_rap_costo", "Costo"), ("_rap_precio", "Precio venta")]:
            campo = MoneyLineEdit()
            campo.setPlaceholderText(placeholder)
            campo.setFixedHeight(28)
            campo.setStyleSheet(
                "QLineEdit{border:1px solid #D1D5DB;border-radius:4px;"
                "padding:0 6px;font-size:11px;}"
            )
            setattr(self, attr, campo)
            lbl = QLabel(f"{placeholder}:")
            lbl.setStyleSheet("font-size:10px;color:#6B7280;")
            fila_r.addWidget(lbl); fila_r.addWidget(campo)
        lay.addLayout(fila_r)

        self._lbl_rapida = QLabel("—")
        self._lbl_rapida.setStyleSheet(
            "font-size:11px;font-weight:bold;color:#1D4ED8;"
            "background:#EFF6FF;border:1px solid #BFDBFE;border-radius:5px;padding:5px 10px;"
        )
        lay.addWidget(self._lbl_rapida)

        self._rap_costo.textChanged.connect(self._recalcular_rapida)
        self._rap_precio.textChanged.connect(self._recalcular_rapida)

        lay.addStretch()
        return w

    # ──────────────────────────────────────────────────────────────────────
    # Lógica — Precio de Venta
    # ──────────────────────────────────────────────────────────────────────

    def _on_toggle_modo(self):
        self._frame_buscar.setVisible(self._btn_inv.isChecked())
        if self._btn_manual.isChecked():
            self._campo_buscar.clear()
        self._recalcular()

    def _on_buscar(self, texto: str):
        if len(texto) < 2:
            self._cm.setStringList([])
            return
        try:
            from database.inventario_repo import (
                buscar_productos_por_nombre, obtener_producto_por_codigo_barras
            )
            por_cb = obtener_producto_por_codigo_barras(texto)
            if por_cb:
                self._campo_buscar.blockSignals(True)
                self._campo_buscar.setText(por_cb.producto)
                self._campo_buscar.blockSignals(False)
                self._costo.set_valor(int(por_cb.costo_unitario))
                self._recalcular()
                return
            prods = buscar_productos_por_nombre(texto)
            self._cm.setStringList([p.producto for p in prods])
            exacto = next((p for p in prods if p.producto.lower() == texto.lower()), None)
            if exacto:
                self._costo.set_valor(int(exacto.costo_unitario))
                self._recalcular()
        except Exception:
            pass

    def _on_seleccionado(self, nombre: str):
        try:
            from database.inventario_repo import obtener_producto_por_nombre_exacto
            p = obtener_producto_por_nombre_exacto(nombre)
            if p:
                self._costo.set_valor(int(p.costo_unitario))
                self._recalcular()
        except Exception:
            pass

    def _recalcular(self):
        costo = self._costo.valor_int()
        pct   = self._chips_g.valor()
        if not costo or not pct:
            self._lbl_pv.setText("Precio de venta:  —")
            self._lbl_g_pesos.setText("Ganancia:  —")
            self._lbl_margen.setText("Margen sobre precio de venta:  —")
            self._frame_dcto.setVisible(False)
            return
        precio   = round(costo * (1 + pct / 100))
        ganancia = precio - costo
        margen   = ganancia / precio * 100
        self._lbl_pv.setText(f"Precio de venta:  {cop(precio)}")
        self._lbl_g_pesos.setText(
            f"Ganancia:  {cop(ganancia)}   •   {pct}% sobre costo"
        )
        self._lbl_margen.setText(f"Margen sobre precio de venta: {margen:.1f}%")
        self._recalcular_dcto()

    def _recalcular_dcto(self):
        costo  = self._costo.valor_int()
        pct_g  = self._chips_g.valor()
        pct_d  = self._chips_d.valor()
        if not costo or not pct_g:
            self._frame_dcto.setVisible(False)
            return
        precio_base = round(costo * (1 + pct_g / 100))
        if not pct_d:
            self._frame_dcto.setVisible(False)
            return
        precio_d  = round(precio_base * (1 - pct_d / 100))
        ganancia_d = precio_d - costo
        margen_d   = ganancia_d / precio_d * 100 if precio_d > 0 else 0
        color = "#15803D" if ganancia_d > 0 else "#DC2626"
        self._lbl_precio_dcto.setText(f"Con {pct_d}% dcto:  {cop(precio_d)}")
        self._lbl_precio_dcto.setStyleSheet(
            f"font-size:12px;font-weight:bold;color:{color};"
            "background:transparent;border:none;"
        )
        self._lbl_margen_dcto.setText(
            f"Ganancia: {cop(ganancia_d)}  •  Margen: {margen_d:.1f}%"
        )
        self._frame_dcto.setVisible(True)

    # ──────────────────────────────────────────────────────────────────────
    # Lógica — Calculadora de Cascos
    # ──────────────────────────────────────────────────────────────────────

    def _recalcular_cascos(self):
        precio_raw = self._precio_factura.valor_int()
        dcto_pct   = self._chips_dp.valor() or 0
        incluye_iva = self._chk_iva.isChecked()

        def _vaciar():
            self._lbl_costo_real.setText("—")
            for i in range(len(_GANANCIAS)):
                for col in (1, 2):
                    it = self._tabla.item(i, col)
                    if it:
                        it.setText("—")
                        it.setForeground(QColor("#9CA3AF"))

        if not precio_raw:
            _vaciar(); return

        precio = float(precio_raw)
        base   = precio / 1.19 if incluye_iva else precio
        costo_real = round(base * (1 - dcto_pct / 100))
        self._lbl_costo_real.setText(cop(costo_real))

        for i, pct in enumerate(_GANANCIAS):
            pv  = round(costo_real * (1 + pct / 100))
            gan = pv - costo_real
            color = (
                QColor("#15803D") if pct >= 45
                else QColor("#1D4ED8") if pct >= 35
                else QColor("#374151")
            )
            for col, txt in [(1, cop(pv)), (2, cop(gan))]:
                it = QTableWidgetItem(txt)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                it.setForeground(color)
                self._tabla.setItem(i, col, it)

    # ──────────────────────────────────────────────────────────────────────
    # Lógica — Calculadora Rápida
    # ──────────────────────────────────────────────────────────────────────

    def _recalcular_rapida(self):
        costo  = self._rap_costo.valor_int()
        precio = self._rap_precio.valor_int()
        if not costo or not precio:
            self._lbl_rapida.setText("—")
            return
        ganancia = precio - costo
        pct_c = ganancia / costo  * 100 if costo  > 0 else 0
        pct_v = ganancia / precio * 100 if precio > 0 else 0
        if ganancia >= 0:
            self._lbl_rapida.setText(
                f"Ganancia: {cop(ganancia)}  •  {pct_c:.1f}% sobre costo  •  {pct_v:.1f}% margen"
            )
            self._lbl_rapida.setStyleSheet(
                "font-size:11px;font-weight:bold;color:#15803D;"
                "background:#F0FDF4;border:1px solid #86EFAC;border-radius:5px;padding:5px 10px;"
            )
        else:
            self._lbl_rapida.setText(
                f"Pérdida: {cop(abs(ganancia))}  —  Estás vendiendo por debajo del costo"
            )
            self._lbl_rapida.setStyleSheet(
                "font-size:11px;font-weight:bold;color:#DC2626;"
                "background:#FEF2F2;border:1px solid #FECACA;border-radius:5px;padding:5px 10px;"
            )
