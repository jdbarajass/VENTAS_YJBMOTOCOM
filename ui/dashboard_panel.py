"""
ui/dashboard_panel.py
Dashboard diario: métricas, desglose por método de pago, productos del día,
proyección mensual y alertas de facturas/préstamos pendientes.

Layout (vertical, scrollable):
  ─ Barra superior (navegación + fecha + estado)
  ─ Banner alertas (condicional)
  ─ Fila 1: 4 tarjetas pequeñas (ventas / ingresos / costos / comisiones)
  ─ Fila 2: 3 tarjetas grandes (g. bruta / g. neta / utilidad real)
  ─ Fila 3: 2 columnas — Ingresos por método  |  Gastos del día (grid 2×2)
  ─ Fila 4: Proyección del mes (4 tarjetas full-width)
  ─ Fila 5: Comisiones del mes (chips, oculta si no hay)
  ─ Fila 6: Productos vendidos hoy (tabla scrollable)
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QDateEdit, QFrame, QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from controllers.dashboard_controller import DashboardController
from services.reportes import ResumenDiario
from utils.formatters import cop, porcentaje, fecha_corta
from ui.styles import aplicar_sombra


# Colores por método de pago (mismos que VentasDiaPanel)
_COLORES_METODO = {
    "Efectivo":      ("#DCFCE7", "#15803D"),
    "Bold":          ("#FEF3C7", "#92400E"),
    "Addi":          ("#EDE9FE", "#6D28D9"),
    "Transferencia": ("#DBEAFE", "#1D4ED8"),
    "Combinado":     ("#FFF7ED", "#C2410C"),
    "Otro":          ("#F3F4F6", "#374151"),
}

# ──────────────────────────────────────────────────────────────────────────────
# Componentes reutilizables
# ──────────────────────────────────────────────────────────────────────────────

class MetricCard(QFrame):
    """Tarjeta de métrica: título + valor grande + subtítulo."""

    def __init__(self, titulo, valor="—", subtitulo="",
                 color_valor="#111827", fondo="#FFFFFF", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._aplicar_fondo(fondo)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)

        self._lbl_titulo = QLabel(titulo.upper())
        self._lbl_titulo.setStyleSheet(
            "color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;"
        )
        lay.addWidget(self._lbl_titulo)

        self._lbl_valor = QLabel(valor)
        fv = QFont(); fv.setPointSize(20); fv.setBold(True)
        self._lbl_valor.setFont(fv)
        self._lbl_valor.setStyleSheet(f"color:{color_valor};")
        lay.addWidget(self._lbl_valor)

        self._lbl_sub = QLabel(subtitulo)
        self._lbl_sub.setStyleSheet("color:#9CA3AF; font-size:11px;")
        self._lbl_sub.setVisible(bool(subtitulo))
        lay.addWidget(self._lbl_sub)

    def actualizar(self, valor, subtitulo="", color_valor="#111827", fondo="#FFFFFF"):
        self._lbl_valor.setText(valor)
        self._lbl_valor.setStyleSheet(f"color:{color_valor};")
        self._lbl_sub.setText(subtitulo)
        self._lbl_sub.setVisible(bool(subtitulo))
        self._aplicar_fondo(fondo)

    def _aplicar_fondo(self, fondo):
        self.setStyleSheet(f"""
            MetricCard {{
                background-color:{fondo};
                border:1px solid #E5E7EB;
                border-radius:10px;
            }}
        """)


class UtilityCard(QFrame):
    """Tarjeta grande y prominente para la UTILIDAD REAL del día."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(6)

        self._lbl_titulo = QLabel("UTILIDAD REAL DEL DÍA")
        self._lbl_titulo.setStyleSheet(
            "font-size:11px; font-weight:bold; letter-spacing:0.5px;"
        )
        lay.addWidget(self._lbl_titulo)

        self._lbl_valor = QLabel("$ 0")
        fv = QFont(); fv.setPointSize(30); fv.setBold(True)
        self._lbl_valor.setFont(fv)
        lay.addWidget(self._lbl_valor)

        self._lbl_formula = QLabel("Ganancia neta  −  Gasto operativo diario")
        self._lbl_formula.setStyleSheet("font-size:11px;")
        lay.addWidget(self._lbl_formula)

        self._set_neutro()

    def actualizar(self, utilidad, ganancia_neta, gasto_diario, gastos_op=0.0):
        self._lbl_valor.setText(cop(utilidad))
        if gastos_op > 0:
            self._lbl_formula.setText(
                f"{cop(ganancia_neta)}  −  {cop(gasto_diario)} (fijo)"
                f"  −  {cop(gastos_op)} (extra)  =  {cop(utilidad)}"
            )
        else:
            self._lbl_formula.setText(
                f"{cop(ganancia_neta)}  −  {cop(gasto_diario)}  =  {cop(utilidad)}"
            )
        if utilidad > 0:
            self._set_positivo()
        elif utilidad < 0:
            self._set_negativo()
        else:
            self._set_neutro()

    def _set_positivo(self):  self._estilo("#DCFCE7", "#15803D", "#166534")
    def _set_negativo(self):  self._estilo("#FEE2E2", "#DC2626", "#991B1B")
    def _set_neutro(self):    self._estilo("#F8FAFC", "#374151", "#6B7280")

    def _estilo(self, fondo, ct, cv):
        self.setStyleSheet(f"""
            UtilityCard {{
                background-color:{fondo};
                border:2px solid {cv}40;
                border-radius:12px;
            }}
        """)
        self._lbl_titulo.setStyleSheet(
            f"font-size:11px; font-weight:bold; letter-spacing:0.5px; color:{ct};"
        )
        self._lbl_valor.setStyleSheet(f"color:{cv};")
        self._lbl_formula.setStyleSheet(f"font-size:11px; color:{ct};")


class _MiniCard(QFrame):
    """Mini tarjeta de información: etiqueta + valor prominente."""

    def __init__(self, etiqueta: str, valor: str = "—",
                 color_valor: str = "#111827", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._base_style = (
            "background:#FFFFFF; border:1px solid #E5E7EB; border-radius:8px;"
        )
        self.setStyleSheet(f"_MiniCard {{ {self._base_style} }}")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(4)

        self._lbl_e = QLabel(etiqueta.upper())
        self._lbl_e.setStyleSheet(
            "color:#6B7280; font-size:9px; font-weight:bold; letter-spacing:0.5px;"
        )
        self._lbl_e.setWordWrap(True)
        lay.addWidget(self._lbl_e)

        self._lbl_v = QLabel(valor)
        fv = QFont(); fv.setPointSize(14); fv.setBold(True)
        self._lbl_v.setFont(fv)
        self._lbl_v.setStyleSheet(f"color:{color_valor};")
        lay.addWidget(self._lbl_v)

    def set_valor(self, valor: str, color: str = "#111827"):
        self._lbl_v.setText(valor)
        self._lbl_v.setStyleSheet(f"color:{color};")

    def set_fondo(self, bg: str, border: str):
        self.setStyleSheet(
            f"_MiniCard {{ background:{bg}; border:1px solid {border}; border-radius:8px; }}"
        )

    def reset_fondo(self):
        self.setStyleSheet(
            f"_MiniCard {{ {self._base_style} }}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Panel principal
# ──────────────────────────────────────────────────────────────────────────────

class DashboardPanel(QWidget):
    """Vista de dashboard con métricas del día, desglose y proyección mensual."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ctrl = DashboardController()
        self._build_ui()
        self.refresh()

    # ──────────────────────────────────────────────────────────────────────────
    # Construcción de UI
    # ──────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # Scroll área que envuelve todo el contenido
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background:#F1F5F9; border:none; }")

        contenido = QWidget()
        contenido.setStyleSheet("background:#F1F5F9;")
        lay = QVBoxLayout(contenido)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(16)

        lay.addLayout(self._barra_superior())          # navegación
        lay.addWidget(self._banner_alertas())          # alertas amarillo (condicional)
        lay.addWidget(self._banner_urgente())          # alertas rojo — facturas vencidas/urgentes
        lay.addLayout(self._fila_tarjetas_pequeñas())  # ventas|ingresos|costos|comisiones
        lay.addLayout(self._fila_tarjetas_grandes())   # g.bruta|g.neta|utilidad
        lay.addLayout(self._fila_metodos_gastos())     # métodos|gastos 2×2
        lay.addWidget(self._panel_proyeccion())        # proyección full-width
        lay.addWidget(self._panel_comisiones_mes())    # comisiones full-width
        lay.addWidget(self._panel_productos())         # productos vendidos
        lay.addStretch()

        scroll.setWidget(contenido)
        root_lay.addWidget(scroll)

    # ── Barra superior ────────────────────────────────────────────────────────

    def _barra_superior(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Dashboard Diario")
        ft = QFont(); ft.setPointSize(16); ft.setBold(True)
        titulo.setFont(ft)

        btn_ant = QPushButton("← Anterior")
        btn_sig = QPushButton("Siguiente →")
        for b in (btn_ant, btn_sig):
            b.setFixedHeight(34)
            b.setStyleSheet(
                "QPushButton { border:1px solid #D1D5DB; border-radius:5px;"
                "padding:0 12px; font-size:12px; background:white; }"
                "QPushButton:hover { background:#F3F4F6; }"
            )
        btn_ant.clicked.connect(self._dia_anterior)
        btn_sig.clicked.connect(self._dia_siguiente)

        self.date_selector = QDateEdit()
        self.date_selector.setCalendarPopup(True)
        self.date_selector.setDate(QDate.currentDate())
        self.date_selector.setDisplayFormat("dd/MM/yyyy")
        self.date_selector.setFixedHeight(34)
        self.date_selector.setFixedWidth(130)
        self.date_selector.setStyleSheet(
            "QDateEdit { border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 8px; background:white; }"
        )
        self.date_selector.dateChanged.connect(lambda _: self.refresh())

        btn_hoy = QPushButton("Hoy")
        btn_hoy.setFixedHeight(34)
        btn_hoy.setFixedWidth(55)
        btn_hoy.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px; background:white; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_hoy.clicked.connect(lambda: self.date_selector.setDate(QDate.currentDate()))

        self._lbl_estado = QLabel("")
        self._lbl_estado.setFixedHeight(28)
        self._lbl_estado.setStyleSheet(
            "font-weight:bold; font-size:12px; border-radius:5px; padding:0 12px;"
        )

        lay.addWidget(titulo)
        lay.addSpacing(12)
        lay.addWidget(btn_ant)
        lay.addWidget(QLabel("Fecha:"))
        lay.addWidget(self.date_selector)
        lay.addWidget(btn_sig)
        lay.addWidget(btn_hoy)
        lay.addSpacing(16)
        lay.addWidget(self._lbl_estado)
        lay.addStretch()
        return lay

    # ── Banner de alertas ─────────────────────────────────────────────────────

    def _banner_alertas(self) -> QFrame:
        self._banner = QFrame()
        self._banner.setVisible(False)
        self._banner.setStyleSheet(
            "QFrame { background:#FFFBEB; border:1px solid #FDE68A; border-radius:7px; }"
        )
        lay = QHBoxLayout(self._banner)
        lay.setContentsMargins(14, 8, 14, 8)
        self._lbl_alertas = QLabel("")
        self._lbl_alertas.setStyleSheet("color:#92400E; font-size:12px;")
        lay.addWidget(self._lbl_alertas)
        lay.addStretch()
        return self._banner

    # ── Banner de urgencias (rojo) ────────────────────────────────────────────

    def _banner_urgente(self) -> QFrame:
        self._banner_urgente_frame = QFrame()
        self._banner_urgente_frame.setVisible(False)
        self._banner_urgente_frame.setStyleSheet(
            "QFrame { background:#FEE2E2; border:1px solid #FECACA; border-radius:7px; }"
        )
        lay = QHBoxLayout(self._banner_urgente_frame)
        lay.setContentsMargins(14, 8, 14, 8)
        self._lbl_urgente = QLabel("")
        self._lbl_urgente.setStyleSheet("color:#991B1B; font-size:12px; font-weight:bold;")
        lay.addWidget(self._lbl_urgente)
        lay.addStretch()
        return self._banner_urgente_frame

    # ── Fila 1: 4 tarjetas pequeñas ──────────────────────────────────────────

    def _fila_tarjetas_pequeñas(self) -> QHBoxLayout:
        lay = QHBoxLayout(); lay.setSpacing(14)
        self.card_ventas     = MetricCard("Ventas registradas", "0",  color_valor="#1D4ED8")
        self.card_ingresos   = MetricCard("Ingresos totales",   "$ 0")
        self.card_costos     = MetricCard("Costos totales",     "$ 0")
        self.card_comisiones = MetricCard("Comisiones pagadas", "$ 0", color_valor="#92400E")
        for c in (self.card_ventas, self.card_ingresos, self.card_costos, self.card_comisiones):
            aplicar_sombra(c)
            lay.addWidget(c)
        return lay

    # ── Fila 2: 3 tarjetas grandes ───────────────────────────────────────────

    def _fila_tarjetas_grandes(self) -> QHBoxLayout:
        lay = QHBoxLayout(); lay.setSpacing(14)
        self.card_g_bruta  = MetricCard("Ganancia bruta",          "$ 0", subtitulo="Precio − Costo")
        self.card_g_neta   = MetricCard("Ganancia neta de ventas", "$ 0", subtitulo="Bruta − Comisiones")
        self.card_utilidad = UtilityCard()
        aplicar_sombra(self.card_g_bruta)
        aplicar_sombra(self.card_g_neta)
        aplicar_sombra(self.card_utilidad, radio=16, opacidad=22)
        lay.addWidget(self.card_g_bruta,  stretch=1)
        lay.addWidget(self.card_g_neta,   stretch=1)
        lay.addWidget(self.card_utilidad, stretch=2)
        return lay

    # ── Fila 3: ingresos por método | gastos del día ──────────────────────────

    def _fila_metodos_gastos(self) -> QHBoxLayout:
        lay = QHBoxLayout(); lay.setSpacing(14)
        lay.addWidget(self._panel_metodos(),    stretch=1)
        lay.addWidget(self._panel_gastos_dia(), stretch=2)
        return lay

    def _panel_metodos(self) -> QFrame:
        """Panel izquierdo: ingresos por método de pago."""
        self._frame_metodos = QFrame()
        self._frame_metodos.setFrameShape(QFrame.StyledPanel)
        self._frame_metodos.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        aplicar_sombra(self._frame_metodos)
        lay = QVBoxLayout(self._frame_metodos)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        lbl = QLabel("INGRESOS POR MÉTODO")
        lbl.setStyleSheet(
            "color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;"
        )
        lay.addWidget(lbl)

        self._lay_metodos = QVBoxLayout()
        self._lay_metodos.setSpacing(6)
        lay.addLayout(self._lay_metodos)
        lay.addStretch()
        return self._frame_metodos

    def _panel_gastos_dia(self) -> QFrame:
        """Panel derecho: 4 mini-tarjetas en grid 2×2 con los gastos del día."""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        aplicar_sombra(frame)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        lbl = QLabel("GASTOS DEL DÍA")
        lbl.setStyleSheet(
            "color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;"
        )
        lay.addWidget(lbl)

        grid = QGridLayout(); grid.setSpacing(8)

        self._card_gasto_dia   = _MiniCard("Gasto fijo diario",     "$ 0")
        self._card_gasto_extra = _MiniCard("Gastos extra hoy",      "$ 0")
        self._card_gasto_mes   = _MiniCard("Gastos fijos del mes",  "$ 0")
        self._card_margen      = _MiniCard("Util % sobre ingresos", "0.0 %")

        for c in (self._card_gasto_dia, self._card_gasto_extra,
                  self._card_gasto_mes, self._card_margen):
            aplicar_sombra(c, radio=6, opacidad=10)

        grid.addWidget(self._card_gasto_dia,   0, 0)
        grid.addWidget(self._card_gasto_extra, 0, 1)
        grid.addWidget(self._card_gasto_mes,   1, 0)
        grid.addWidget(self._card_margen,      1, 1)
        lay.addLayout(grid)
        lay.addStretch()
        return frame

    # ── Fila 4: proyección mensual (full-width) ───────────────────────────────

    def _panel_proyeccion(self) -> QFrame:
        """4 tarjetas de proyección del mes a ancho completo."""
        self._frame_proy = QFrame()
        self._frame_proy.setFrameShape(QFrame.StyledPanel)
        self._frame_proy.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        aplicar_sombra(self._frame_proy)
        lay = QVBoxLayout(self._frame_proy)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(10)

        lbl = QLabel("PROYECCIÓN DEL MES")
        lbl.setStyleSheet(
            "color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;"
        )
        lay.addWidget(lbl)

        cards_lay = QHBoxLayout(); cards_lay.setSpacing(12)

        self._card_proy_dia  = _MiniCard("Día del mes",        "—")
        self._card_proy_meta = _MiniCard("Meta acumulada",     "$ 0")
        self._card_proy_util = _MiniCard("Utilidad acumulada", "$ 0")
        self._card_proy_dif  = _MiniCard("Situación",          "—",  color_valor="#374151")

        for c in (self._card_proy_dia, self._card_proy_meta,
                  self._card_proy_util, self._card_proy_dif):
            aplicar_sombra(c, radio=6, opacidad=10)
            cards_lay.addWidget(c)

        lay.addLayout(cards_lay)
        return self._frame_proy

    # ── Fila 5: comisiones del mes (full-width, oculto si no hay) ─────────────

    def _panel_comisiones_mes(self) -> QFrame:
        self._frame_comisiones_panel = QFrame()
        self._frame_comisiones_panel.setFrameShape(QFrame.StyledPanel)
        self._frame_comisiones_panel.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        aplicar_sombra(self._frame_comisiones_panel)
        self._frame_comisiones_panel.setVisible(False)

        lay = QVBoxLayout(self._frame_comisiones_panel)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(8)

        lbl = QLabel("COMISIONES DEL MES")
        lbl.setStyleSheet(
            "color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;"
        )
        lay.addWidget(lbl)

        self._frame_comisiones = QFrame()
        self._frame_comisiones.setStyleSheet(
            "QFrame { background:transparent; border:none; }"
        )
        self._lay_comisiones = QHBoxLayout(self._frame_comisiones)
        self._lay_comisiones.setContentsMargins(0, 0, 0, 0)
        self._lay_comisiones.setSpacing(8)
        lay.addWidget(self._frame_comisiones)
        return self._frame_comisiones_panel

    # ── Fila 6: productos vendidos (full-width) ───────────────────────────────

    def _panel_productos(self) -> QFrame:
        self._frame_productos = QFrame()
        self._frame_productos.setFrameShape(QFrame.StyledPanel)
        self._frame_productos.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        aplicar_sombra(self._frame_productos)

        lay = QVBoxLayout(self._frame_productos)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(8)

        lbl = QLabel("PRODUCTOS VENDIDOS HOY")
        lbl.setStyleSheet(
            "color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;"
        )
        lay.addWidget(lbl)

        # Encabezado de columnas
        hdr = QHBoxLayout()
        for texto, stretch, alin in [
            ("Producto",      5, Qt.AlignLeft),
            ("Cant.",         1, Qt.AlignCenter),
            ("Ingresos",      2, Qt.AlignRight),
            ("Ganancia neta", 2, Qt.AlignRight),
        ]:
            l = QLabel(texto)
            l.setStyleSheet("color:#6B7280; font-size:10px; font-weight:bold;")
            l.setAlignment(alin)
            hdr.addWidget(l, stretch=stretch)
        lay.addLayout(hdr)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#E5E7EB;")
        lay.addWidget(sep)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(120)
        scroll.setMaximumHeight(240)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")

        self._contenedor_prods = QWidget()
        self._contenedor_prods.setStyleSheet("background:transparent;")
        self._lay_productos = QVBoxLayout(self._contenedor_prods)
        self._lay_productos.setContentsMargins(0, 0, 0, 0)
        self._lay_productos.setSpacing(2)

        scroll.setWidget(self._contenedor_prods)
        lay.addWidget(scroll)
        return self._frame_productos

    # ──────────────────────────────────────────────────────────────────────────
    # Navegación
    # ──────────────────────────────────────────────────────────────────────────

    def _dia_anterior(self):
        self.date_selector.setDate(self.date_selector.date().addDays(-1))

    def _dia_siguiente(self):
        self.date_selector.setDate(self.date_selector.date().addDays(1))

    # ──────────────────────────────────────────────────────────────────────────
    # Datos
    # ──────────────────────────────────────────────────────────────────────────

    def refresh(self):
        qd = self.date_selector.date()
        fecha = date(qd.year(), qd.month(), qd.day())
        datos = self._ctrl.get_datos_dia(fecha)
        self._actualizar_cards(datos["resumen"])
        self._actualizar_desglose(datos["por_metodo"], datos["productos"])
        self._actualizar_proyeccion(datos["proyeccion"])
        self._actualizar_alertas(datos["alertas"])

    def _actualizar_cards(self, r: ResumenDiario):
        self.card_ventas.actualizar(
            str(r.cantidad_ventas),
            subtitulo=f"Fecha: {fecha_corta(r.fecha)}",
            color_valor="#1D4ED8",
        )
        self.card_ingresos.actualizar(cop(r.total_ingresos))
        self.card_costos.actualizar(cop(r.total_costos))
        self.card_comisiones.actualizar(
            cop(r.total_comisiones),
            color_valor="#B45309" if r.total_comisiones > 0 else "#374151",
        )

        color_bruta = "#16A34A" if r.ganancia_bruta >= 0 else "#DC2626"
        self.card_g_bruta.actualizar(cop(r.ganancia_bruta), color_valor=color_bruta)

        color_neta = "#16A34A" if r.ganancia_neta >= 0 else "#DC2626"
        self.card_g_neta.actualizar(
            cop(r.ganancia_neta),
            subtitulo=f"G.Neta %: {porcentaje(r.margen_ganancia, 1)} sobre ingresos",
            color_valor=color_neta,
        )

        self.card_utilidad.actualizar(
            r.utilidad_real, r.ganancia_neta, r.gasto_diario, r.gastos_operativos
        )

        # Gastos del día — mini-cards grid
        from database.config_repo import obtener_configuracion
        cfg = obtener_configuracion()
        self._card_gasto_dia.set_valor(cop(r.gasto_diario), "#374151")
        self._card_gasto_extra.set_valor(
            cop(r.gastos_operativos),
            "#DC2626" if r.gastos_operativos > 0 else "#6B7280",
        )
        self._card_gasto_mes.set_valor(cop(cfg.total_gastos_mes), "#374151")
        margen_val = porcentaje(r.margen_porcentual, 1)
        margen_color = "#15803D" if r.margen_porcentual >= 20 else (
            "#D97706" if r.margen_porcentual >= 10 else "#DC2626"
        )
        self._card_margen.set_valor(margen_val, margen_color)

        # Badge de estado
        if r.cantidad_ventas == 0:
            self._lbl_estado.setText("Sin ventas registradas")
            self._lbl_estado.setStyleSheet(
                "font-weight:bold; font-size:12px; border-radius:5px; padding:0 12px;"
                "background:#F1F5F9; color:#6B7280;"
            )
        elif r.es_positivo:
            self._lbl_estado.setText("  DÍA POSITIVO  ")
            self._lbl_estado.setStyleSheet(
                "font-weight:bold; font-size:12px; border-radius:5px; padding:0 12px;"
                "background:#DCFCE7; color:#15803D;"
            )
        else:
            self._lbl_estado.setText("  DÍA EN PÉRDIDA  ")
            self._lbl_estado.setStyleSheet(
                "font-weight:bold; font-size:12px; border-radius:5px; padding:0 12px;"
                "background:#FEE2E2; color:#DC2626;"
            )

    def _actualizar_desglose(self, por_metodo: dict, productos: list):
        # ── Chips de métodos de pago ──────────────────────────────────────────
        while self._lay_metodos.count():
            item = self._lay_metodos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not por_metodo:
            lbl = QLabel("Sin ventas hoy")
            lbl.setStyleSheet("color:#9CA3AF; font-size:12px; font-style:italic;")
            self._lay_metodos.addWidget(lbl)
        else:
            for metodo, total in sorted(por_metodo.items()):
                bg, fg = _COLORES_METODO.get(metodo, ("#F3F4F6", "#374151"))
                chip = QWidget()
                chip.setStyleSheet(
                    f"background:{bg}; border-radius:6px;"
                )
                ch_lay = QHBoxLayout(chip)
                ch_lay.setContentsMargins(10, 6, 10, 6)
                lbl_m = QLabel(metodo)
                lbl_m.setStyleSheet(
                    f"color:{fg}; font-size:12px; font-weight:bold;"
                    "background:transparent;"
                )
                lbl_v = QLabel(cop(total))
                lbl_v.setStyleSheet(
                    f"color:{fg}; font-size:13px; font-weight:bold;"
                    "background:transparent;"
                )
                lbl_v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                ch_lay.addWidget(lbl_m)
                ch_lay.addStretch()
                ch_lay.addWidget(lbl_v)
                self._lay_metodos.addWidget(chip)

            # Cuadre de caja: Efectivo vs Digital
            sep = QFrame(); sep.setFrameShape(QFrame.HLine)
            sep.setStyleSheet("color:#E5E7EB; margin:2px 0;")
            self._lay_metodos.addWidget(sep)

            efectivo = por_metodo.get("Efectivo", 0.0)
            digital  = sum(v for k, v in por_metodo.items() if k != "Efectivo")

            def _resumen_chip(texto, valor, bg, fg):
                w = QWidget()
                w.setStyleSheet(f"background:{bg}; border-radius:5px;")
                wl = QHBoxLayout(w)
                wl.setContentsMargins(8, 4, 8, 4)
                l1 = QLabel(texto)
                l1.setStyleSheet(
                    f"color:{fg}; font-size:10px; font-weight:bold; background:transparent;"
                )
                l2 = QLabel(cop(valor))
                l2.setStyleSheet(
                    f"color:{fg}; font-size:11px; font-weight:bold; background:transparent;"
                )
                l2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                wl.addWidget(l1); wl.addStretch(); wl.addWidget(l2)
                return w

            self._lay_metodos.addWidget(
                _resumen_chip("Efectivo", efectivo, "#DCFCE7", "#15803D")
            )
            self._lay_metodos.addWidget(
                _resumen_chip("Digital", digital, "#DBEAFE", "#1D4ED8")
            )
            self._lay_metodos.addStretch()

        # ── Filas de productos ────────────────────────────────────────────────
        while self._lay_productos.count():
            item = self._lay_productos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not productos:
            lbl = QLabel("Sin ventas registradas para esta fecha.")
            lbl.setStyleSheet(
                "color:#9CA3AF; font-size:12px; font-style:italic; padding:4px 0;"
            )
            self._lay_productos.addWidget(lbl)
            return

        for i, (nombre, cant, ingresos, ganancia) in enumerate(productos):
            fila = QHBoxLayout()
            fila.setContentsMargins(0, 2, 0, 2)

            lbl_nombre = QLabel(nombre)
            lbl_nombre.setStyleSheet("font-size:11px; color:#374151;")
            lbl_nombre.setWordWrap(True)

            lbl_cant = QLabel(str(cant))
            lbl_cant.setAlignment(Qt.AlignCenter)
            lbl_cant.setStyleSheet("font-size:11px; color:#6B7280;")

            lbl_ing = QLabel(cop(ingresos))
            lbl_ing.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl_ing.setStyleSheet("font-size:11px; color:#374151;")

            color_g = "#15803D" if ganancia >= 0 else "#DC2626"
            lbl_gan = QLabel(cop(ganancia))
            lbl_gan.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl_gan.setStyleSheet(f"font-size:11px; font-weight:bold; color:{color_g};")

            fila.addWidget(lbl_nombre, stretch=4)
            fila.addWidget(lbl_cant,   stretch=1)
            fila.addWidget(lbl_ing,    stretch=2)
            fila.addWidget(lbl_gan,    stretch=2)

            contenedor = QWidget()
            contenedor.setLayout(fila)
            fondo = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
            contenedor.setStyleSheet(f"background:{fondo}; border-radius:4px;")
            self._lay_productos.addWidget(contenedor)

        self._lay_productos.addStretch()

    def _actualizar_proyeccion(self, p: dict):
        self._card_proy_dia.set_valor(f"Día {p['dia']} de {p['dias_mes']}", "#374151")
        self._card_proy_meta.set_valor(cop(p["meta"]), "#374151")
        self._card_proy_util.set_valor(cop(p["utilidad_acumulada"]), "#374151")

        dif = p["diferencia"]
        if dif >= 0:
            texto = f"+{cop(dif)}"
            color = "#15803D"; bg = "#DCFCE7"; border = "#86EFAC"
        else:
            texto = cop(dif)
            color = "#DC2626"; bg = "#FEE2E2"; border = "#FECACA"

        self._card_proy_dif.set_valor(texto, color)
        # Resaltar la tarjeta de situación con color semántico
        self._card_proy_dif.setStyleSheet(
            f"_MiniCard {{ background:{bg}; border:1px solid {border}; border-radius:8px; }}"
        )
        # Borde sutil en el panel de proyección
        self._frame_proy.setStyleSheet(
            f"QFrame {{ background:#FFFFFF; border:1px solid {border}; border-radius:10px; }}"
        )

        # ── Comisiones por plataforma ─────────────────────────────────────────
        while self._lay_comisiones.count():
            item = self._lay_comisiones.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        comisiones = p.get("comisiones_plataforma", {})
        if not comisiones:
            self._frame_comisiones_panel.setVisible(False)
        else:
            self._frame_comisiones_panel.setVisible(True)
            total_com = sum(comisiones.values())
            for metodo, monto in sorted(comisiones.items(), key=lambda x: -x[1]):
                bg_c, fg_c = _COLORES_METODO.get(metodo, ("#F3F4F6", "#374151"))
                chip = QLabel(f"{metodo}: {cop(monto)}")
                chip.setStyleSheet(
                    f"background:{bg_c}; color:{fg_c}; border-radius:4px;"
                    "font-size:11px; font-weight:bold; padding:4px 10px;"
                )
                self._lay_comisiones.addWidget(chip)
            sep = QFrame(); sep.setFrameShape(QFrame.VLine)
            sep.setFixedHeight(24); sep.setStyleSheet("color:#CBD5E1;")
            lbl_tot = QLabel(f"Total cobrado: {cop(total_com)}")
            lbl_tot.setStyleSheet(
                "color:#DC2626; font-size:11px; font-weight:bold; padding:4px 0;"
            )
            self._lay_comisiones.addWidget(sep)
            self._lay_comisiones.addWidget(lbl_tot)
            self._lay_comisiones.addStretch()

    def _actualizar_alertas(self, alertas: dict):
        # Banner amarillo: alertas generales
        partes = []
        if alertas["prestamos"] > 0:
            n = alertas["prestamos"]
            texto = f"⚠  {n} préstamo(s) pendiente(s)"
            if alertas.get("prestamos_urgentes", 0) > 0:
                texto += f"  ({alertas['prestamos_urgentes']} urgentes)"
            partes.append(texto)
        fact_no_vencidas = alertas["facturas"] - alertas.get("facturas_vencidas", 0)
        if fact_no_vencidas > 0:
            partes.append(
                f"🧾  {fact_no_vencidas} factura(s) por pagar"
                f"  ({cop(alertas['total_facturas'] - alertas.get('total_vencidas', 0))})"
            )
        if partes:
            self._lbl_alertas.setText("   |   ".join(partes))
            self._banner.setVisible(True)
        else:
            self._banner.setVisible(False)

        # Banner rojo: facturas ya vencidas
        vencidas = alertas.get("facturas_vencidas", 0)
        if vencidas > 0:
            self._lbl_urgente.setText(
                f"🚨  {vencidas} factura{'s' if vencidas != 1 else ''} VENCIDA{'S' if vencidas != 1 else ''}"
                f"  —  {cop(alertas.get('total_vencidas', 0))} sin pagar"
            )
            self._banner_urgente_frame.setVisible(True)
        else:
            self._banner_urgente_frame.setVisible(False)
