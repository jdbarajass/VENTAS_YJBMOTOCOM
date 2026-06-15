"""
ui/mi_cuadre_panel.py
Cuadre del día para el vendedor: ventas, ingresos y desglose por método de pago.
Sin costos ni márgenes (datos internos del negocio).
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from utils.formatters import cop, fecha_corta


def _ingreso_real(v) -> float:
    """Ingreso real cobrado por una venta, compatible con modelo antiguo y nuevo."""
    _d  = getattr(v, "descuento", 0) or 0
    _po = getattr(v, "precio_ofertado", 0.0) or 0.0
    # Nuevo modelo: precio ya es el precio real cobrado (precio_ofertado = anunciado)
    # Modelo antiguo: precio = precio anunciado, descuento = valor descontado (solo en v0)
    return v.precio * v.cantidad - (0 if _po > 0 else _d)


class MiCuadrePanel(QWidget):
    """Cuadre del día para el vendedor — sin datos sensibles de costos."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()
        timer = QTimer(self)
        timer.timeout.connect(self.refresh)
        timer.start(60_000)

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        # Cabecera
        self._lbl_fecha = QLabel(fecha_corta(date.today()))
        f = QFont(); f.setPointSize(22); f.setBold(True)
        self._lbl_fecha.setFont(f)
        self._lbl_fecha.setStyleSheet("color:#1E293B;")

        lbl_sub = QLabel("Cuadre del Día")
        lbl_sub.setStyleSheet("color:#64748B; font-size:14px;")

        btn_refresh = QPushButton("↻ Actualizar")
        btn_refresh.setFixedHeight(34)
        btn_refresh.setStyleSheet(
            "QPushButton { border:1px solid #CBD5E1; border-radius:6px;"
            "padding:0 16px; font-size:12px; background:#F8FAFC; }"
            "QPushButton:hover { background:#E2E8F0; }"
        )
        btn_refresh.clicked.connect(self.refresh)

        cab = QHBoxLayout()
        v = QVBoxLayout(); v.setSpacing(2)
        v.addWidget(self._lbl_fecha)
        v.addWidget(lbl_sub)
        cab.addLayout(v)
        cab.addStretch()
        cab.addWidget(btn_refresh)
        root.addLayout(cab)

        # Tarjetas resumen
        fila_cards = QHBoxLayout(); fila_cards.setSpacing(16)
        self._card_ventas  = self._card("Unidades vendidas", "0",   "#2563EB")
        self._card_ingreso = self._card("Total recaudado",   "$ 0", "#15803D")
        for c in (self._card_ventas, self._card_ingreso):
            fila_cards.addWidget(c)
        root.addLayout(fila_cards)

        # Desglose por método de pago
        frame_metodos = QFrame()
        frame_metodos.setFrameShape(QFrame.StyledPanel)
        frame_metodos.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        self._lay_metodos = QVBoxLayout(frame_metodos)
        self._lay_metodos.setContentsMargins(20, 14, 20, 14)
        self._lay_metodos.setSpacing(8)
        lbl_titulo_metodos = QLabel("CUADRE POR MÉTODO DE PAGO")
        lbl_titulo_metodos.setStyleSheet("color:#9CA3AF; font-size:10px; font-weight:bold;")
        self._lay_metodos.addWidget(lbl_titulo_metodos)
        self._metodos_widgets: list[QWidget] = []
        root.addWidget(frame_metodos)

        root.addStretch()

    def _card(self, titulo: str, valor: str, color: str) -> QFrame:
        w = QFrame()
        w.setFrameShape(QFrame.StyledPanel)
        w.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(4)
        lbl_t = QLabel(titulo.upper())
        lbl_t.setStyleSheet("color:#9CA3AF; font-size:10px; font-weight:bold;")
        lbl_v = QLabel(valor)
        f = QFont(); f.setPointSize(26); f.setBold(True)
        lbl_v.setFont(f)
        lbl_v.setStyleSheet(f"color:{color};")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)
        w._lbl_v = lbl_v
        return w

    # ------------------------------------------------------------------

    def refresh(self) -> None:
        from database.ventas_repo import obtener_ventas_por_fecha
        hoy = date.today()
        self._lbl_fecha.setText(fecha_corta(hoy))
        ventas = obtener_ventas_por_fecha(hoy)

        cantidad = sum(v.cantidad for v in ventas)
        total_recaudado = sum(_ingreso_real(v) for v in ventas)

        self._card_ventas._lbl_v.setText(str(cantidad))
        self._card_ingreso._lbl_v.setText(cop(total_recaudado))

        # Desglose por método
        for w in self._metodos_widgets:
            w.setParent(None)
        self._metodos_widgets.clear()

        from collections import defaultdict
        por_metodo: dict[str, float] = defaultdict(float)
        for v in ventas:
            metodo = v.metodo_pago or "Otro"
            por_metodo[metodo] += _ingreso_real(v)

        if not por_metodo:
            lbl_vacio = QLabel("Sin ventas registradas hoy.")
            lbl_vacio.setStyleSheet("color:#9CA3AF; font-size:13px; padding:8px 0;")
            self._lay_metodos.addWidget(lbl_vacio)
            self._metodos_widgets.append(lbl_vacio)
        else:
            for metodo, monto in sorted(por_metodo.items(), key=lambda x: -x[1]):
                fila = QWidget()
                fila.setStyleSheet("background:transparent;")
                fl = QHBoxLayout(fila)
                fl.setContentsMargins(0, 2, 0, 2)
                lbl_m = QLabel(metodo)
                lbl_m.setStyleSheet("font-size:13px; color:#374151;")
                lbl_v = QLabel(cop(monto))
                f2 = QFont(); f2.setPointSize(13); f2.setBold(True)
                lbl_v.setFont(f2)
                lbl_v.setStyleSheet("color:#15803D;")
                fl.addWidget(lbl_m)
                fl.addStretch()
                fl.addWidget(lbl_v)
                self._lay_metodos.addWidget(fila)
                self._metodos_widgets.append(fila)
