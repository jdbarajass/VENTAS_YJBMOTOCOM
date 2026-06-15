"""
ui/rendimiento_vendedores_panel.py
Resumen mensual de ventas agrupado por vendedor.
Vista de admin: muestra todos los usuarios registrados y sus ventas del mes.
"""

from datetime import date
from collections import defaultdict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QComboBox, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from utils.formatters import cop, MESES_ES


def _ingreso_real(v) -> float:
    """Ingreso real cobrado — compatible con modelo antiguo y nuevo de descuentos."""
    _d  = getattr(v, "descuento", 0) or 0
    _po = getattr(v, "precio_ofertado", 0.0) or 0.0
    return v.precio * v.cantidad - (0 if _po > 0 else _d)


class RendimientoVendedoresPanel(QWidget):
    """Tabla mensual de ventas por vendedor, con totales al pie."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        # ── Cabecera ──────────────────────────────────────────────────
        lbl_titulo = QLabel("Rendimiento por Vendedor")
        f = QFont(); f.setPointSize(20); f.setBold(True)
        lbl_titulo.setFont(f)
        lbl_titulo.setStyleSheet("color:#1E293B;")

        hoy = date.today()

        self._combo_mes = QComboBox()
        self._combo_mes.setFixedHeight(32)
        self._combo_mes.setFixedWidth(145)
        for num, nombre in sorted(MESES_ES.items()):
            self._combo_mes.addItem(nombre, num)
        self._combo_mes.setCurrentIndex(hoy.month - 1)

        self._combo_año = QComboBox()
        self._combo_año.setFixedHeight(32)
        self._combo_año.setFixedWidth(90)
        for año in range(2024, hoy.year + 2):
            self._combo_año.addItem(str(año), año)
        self._combo_año.setCurrentText(str(hoy.year))

        btn_ver = QPushButton("Ver")
        btn_ver.setFixedHeight(32)
        btn_ver.setFixedWidth(70)
        btn_ver.setStyleSheet(
            "QPushButton { background:#2563EB; color:#FFF; border-radius:6px;"
            " font-size:12px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btn_ver.clicked.connect(self.refresh)

        cab = QHBoxLayout()
        cab.setSpacing(10)
        cab.addWidget(lbl_titulo)
        cab.addStretch()
        cab.addWidget(self._combo_mes)
        cab.addWidget(self._combo_año)
        cab.addWidget(btn_ver)
        root.addLayout(cab)

        # ── Tabla ─────────────────────────────────────────────────────
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(4)
        self._tabla.setHorizontalHeaderLabels(
            ["Vendedor", "Transacciones", "Unidades", "Total Ingresos"]
        )
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setShowGrid(False)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setStyleSheet(
            "QTableWidget { border:1px solid #E5E7EB; border-radius:8px; font-size:13px; }"
            "QHeaderView::section { font-weight:bold; font-size:11px; border:none;"
            " padding:8px 12px; background:#F8FAFC; color:#374151; }"
            "QTableWidget::item { padding:6px 12px; }"
        )
        hh = self._tabla.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        root.addWidget(self._tabla)

        # ── Barra de totales ──────────────────────────────────────────
        frame_tot = QFrame()
        frame_tot.setStyleSheet(
            "QFrame { background:#EFF6FF; border:1px solid #BFDBFE; border-radius:8px; }"
        )
        lay_tot = QHBoxLayout(frame_tot)
        lay_tot.setContentsMargins(20, 12, 20, 12)
        lay_tot.setSpacing(0)

        lbl_etiq = QLabel("TOTAL DEL MES")
        lbl_etiq.setStyleSheet(
            "font-size:11px; color:#64748B; font-weight:bold; background:transparent;"
        )
        lay_tot.addWidget(lbl_etiq)
        lay_tot.addStretch()

        self._lbl_tot_trans = self._mk_total_lbl()
        self._lbl_tot_uds   = self._mk_total_lbl()
        self._lbl_tot_ing   = self._mk_total_lbl()

        lay_tot.addWidget(self._lbl_tot_trans)
        lay_tot.addSpacing(52)
        lay_tot.addWidget(self._lbl_tot_uds)
        lay_tot.addSpacing(52)
        lay_tot.addWidget(self._lbl_tot_ing)

        root.addWidget(frame_tot)

    def _mk_total_lbl(self) -> QLabel:
        lbl = QLabel("—")
        lbl.setStyleSheet(
            "font-size:14px; font-weight:bold; color:#1E40AF; background:transparent;"
        )
        return lbl

    def _item(self, texto: str, align=Qt.AlignLeft | Qt.AlignVCenter) -> QTableWidgetItem:
        it = QTableWidgetItem(texto)
        it.setTextAlignment(align)
        return it

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        from database.ventas_repo import obtener_ventas_por_mes
        from database.usuarios_repo import obtener_todos_usuarios

        mes = self._combo_mes.currentData()
        año = self._combo_año.currentData()

        ventas  = obtener_ventas_por_mes(año, mes)
        usuarios = obtener_todos_usuarios()

        # Inicializar stats con todos los usuarios registrados (incluye los sin ventas)
        stats: dict[str, dict] = {}
        for u in usuarios:
            stats[u.nombre] = {"trans": set(), "uds": 0, "ing": 0.0}

        for v in ventas:
            nombre = (v.vendedor or "").strip() or "Sin asignar"
            if nombre not in stats:
                stats[nombre] = {"trans": set(), "uds": 0, "ing": 0.0}
            stats[nombre]["trans"].add(v.numero_factura or v.id)
            stats[nombre]["uds"] += v.cantidad
            stats[nombre]["ing"] += _ingreso_real(v)

        # Ordenar: mayor ingreso primero; sin ventas al final
        filas = sorted(
            stats.items(),
            key=lambda x: (-x[1]["ing"], x[0].lower()),
        )

        self._tabla.setRowCount(len(filas))
        for row, (nombre, s) in enumerate(filas):
            self._tabla.setRowHeight(row, 38)
            n_trans = len(s["trans"])
            tiene_ventas = s["ing"] > 0

            # Nombre
            it_nombre = self._item(nombre)
            if tiene_ventas:
                f = QFont(); f.setBold(True)
                it_nombre.setFont(f)
            else:
                it_nombre.setForeground(QColor("#9CA3AF"))
            self._tabla.setItem(row, 0, it_nombre)

            # Transacciones
            it_trans = self._item(
                str(n_trans) if n_trans else "—",
                Qt.AlignCenter | Qt.AlignVCenter,
            )
            if not tiene_ventas:
                it_trans.setForeground(QColor("#9CA3AF"))
            self._tabla.setItem(row, 1, it_trans)

            # Unidades
            it_uds = self._item(
                str(s["uds"]) if s["uds"] else "—",
                Qt.AlignCenter | Qt.AlignVCenter,
            )
            if not tiene_ventas:
                it_uds.setForeground(QColor("#9CA3AF"))
            self._tabla.setItem(row, 2, it_uds)

            # Ingresos
            it_ing = self._item(
                cop(s["ing"]) if tiene_ventas else "—",
                Qt.AlignRight | Qt.AlignVCenter,
            )
            if tiene_ventas:
                it_ing.setForeground(QColor("#15803D"))
            else:
                it_ing.setForeground(QColor("#9CA3AF"))
            self._tabla.setItem(row, 3, it_ing)

        # Totales globales
        total_trans = len({(v.numero_factura or v.id) for v in ventas})
        total_uds   = sum(v.cantidad for v in ventas)
        total_ing   = sum(_ingreso_real(v) for v in ventas)

        self._lbl_tot_trans.setText(f"{total_trans} transacciones")
        self._lbl_tot_uds.setText(f"{total_uds} unidades")
        self._lbl_tot_ing.setText(cop(total_ing))
