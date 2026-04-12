"""
ui/dashboard_panel.py
Dashboard diario: métricas, desglose por método de pago, productos del día,
proyección mensual y alertas de facturas/préstamos pendientes.
"""

from datetime import date, timedelta

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
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


class MetricCard(QFrame):
    """Tarjeta de métrica reutilizable: título + valor grande + subtítulo."""

    def __init__(self, titulo, valor="—", subtitulo="",
                 color_valor="#111827", fondo="#FFFFFF", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._fondo_base = fondo
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


class DashboardPanel(QWidget):
    """Vista de dashboard con métricas del día, desglose y proyección mensual."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ctrl = DashboardController()
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(14)

        root.addLayout(self._barra_superior())
        root.addWidget(self._banner_alertas())
        root.addLayout(self._fila_tarjetas_pequeñas())
        root.addLayout(self._fila_tarjetas_grandes())
        root.addLayout(self._seccion_desglose())   # métodos | gastos+proyección
        root.addWidget(self._panel_productos())    # productos vendidos hoy (ancho completo)
        root.addStretch()

    # ── Barra superior con navegación ─────────────────────────────────

    def _barra_superior(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Dashboard Diario")
        ft = QFont(); ft.setPointSize(16); ft.setBold(True)
        titulo.setFont(ft)

        # Navegación ← / →
        btn_ant = QPushButton("← Anterior")
        btn_sig = QPushButton("Siguiente →")
        for b in (btn_ant, btn_sig):
            b.setFixedHeight(34)
            b.setStyleSheet(
                "QPushButton { border:1px solid #D1D5DB; border-radius:5px;"
                "padding:0 12px; font-size:12px; }"
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
        self.date_selector.dateChanged.connect(lambda _: self.refresh())

        btn_hoy = QPushButton("Hoy")
        btn_hoy.setFixedHeight(34)
        btn_hoy.setFixedWidth(55)
        btn_hoy.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px; }"
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

    # ── Banner de alertas ──────────────────────────────────────────────

    def _banner_alertas(self) -> QFrame:
        self._banner = QFrame()
        self._banner.setVisible(False)
        self._banner.setStyleSheet(
            "QFrame { background:#FFFBEB; border:1px solid #FDE68A;"
            "border-radius:7px; }"
        )
        lay = QHBoxLayout(self._banner)
        lay.setContentsMargins(14, 8, 14, 8)
        self._lbl_alertas = QLabel("")
        self._lbl_alertas.setStyleSheet("color:#92400E; font-size:12px;")
        lay.addWidget(self._lbl_alertas)
        lay.addStretch()
        return self._banner

    # ── Tarjetas métricas ──────────────────────────────────────────────

    def _fila_tarjetas_pequeñas(self) -> QHBoxLayout:
        lay = QHBoxLayout(); lay.setSpacing(14)
        self.card_ventas     = MetricCard("Ventas registradas", "0",  color_valor="#1D4ED8")
        self.card_ingresos   = MetricCard("Ingresos totales",   "$ 0")
        self.card_costos     = MetricCard("Costos totales",     "$ 0")
        self.card_comisiones = MetricCard("Comisiones pagadas", "$ 0", color_valor="#92400E")
        for c in (self.card_ventas, self.card_ingresos, self.card_costos, self.card_comisiones):
            aplicar_sombra(c); lay.addWidget(c)
        return lay

    def _fila_tarjetas_grandes(self) -> QHBoxLayout:
        lay = QHBoxLayout(); lay.setSpacing(14)
        self.card_g_bruta  = MetricCard("Ganancia bruta",            "$ 0", subtitulo="Precio − Costo")
        self.card_g_neta   = MetricCard("Ganancia neta de ventas",   "$ 0", subtitulo="Bruta − Comisiones")
        self.card_utilidad = UtilityCard()
        aplicar_sombra(self.card_g_bruta)
        aplicar_sombra(self.card_g_neta)
        aplicar_sombra(self.card_utilidad, radio=16, opacidad=22)
        lay.addWidget(self.card_g_bruta,  stretch=1)
        lay.addWidget(self.card_g_neta,   stretch=1)
        lay.addWidget(self.card_utilidad, stretch=2)
        return lay

    # ── Sección de desglose: métodos | gastos + proyección ────────────

    def _seccion_desglose(self) -> QHBoxLayout:
        lay = QHBoxLayout(); lay.setSpacing(14)
        lay.addWidget(self._panel_metodos(),       stretch=1)
        lay.addWidget(self._panel_gastos_proy(),   stretch=2)
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
        lbl.setStyleSheet("color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;")
        lay.addWidget(lbl)

        self._lay_metodos = QVBoxLayout()
        self._lay_metodos.setSpacing(6)
        lay.addLayout(self._lay_metodos)

        self._lbl_sin_ventas_met = QLabel("Sin ventas hoy")
        self._lbl_sin_ventas_met.setStyleSheet("color:#9CA3AF; font-size:12px; font-style:italic;")
        self._lay_metodos.addWidget(self._lbl_sin_ventas_met)

        lay.addStretch()
        return self._frame_metodos

    def _panel_gastos_proy(self) -> QFrame:
        """Panel derecho: gastos del día (arriba) + proyección mensual (abajo)."""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        aplicar_sombra(frame)
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        # ── Gastos del día ──────────────────────────────────────────
        lbl_g = QLabel("GASTOS DEL DÍA")
        lbl_g.setStyleSheet("color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;")
        lay.addWidget(lbl_g)

        fila_gastos = QHBoxLayout(); fila_gastos.setSpacing(20)
        self._lbl_gasto_dia   = self._info_chip("Gasto fijo diario",     "$ 0")
        self._lbl_gasto_extra = self._info_chip("Gastos extra día",      "$ 0")
        self._lbl_gasto_mes   = self._info_chip("Gastos fijos del mes",  "$ 0")
        self._lbl_margen      = self._info_chip("Margen sobre ingresos", "0.0 %")
        fila_gastos.addWidget(self._lbl_gasto_dia)
        fila_gastos.addWidget(self._sep_v())
        fila_gastos.addWidget(self._lbl_gasto_extra)
        fila_gastos.addWidget(self._sep_v())
        fila_gastos.addWidget(self._lbl_gasto_mes)
        fila_gastos.addWidget(self._sep_v())
        fila_gastos.addWidget(self._lbl_margen)
        fila_gastos.addStretch()
        lay.addLayout(fila_gastos)

        # Separador
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#E5E7EB;")
        lay.addWidget(sep)

        # ── Proyección mensual ──────────────────────────────────────
        lbl_p = QLabel("PROYECCIÓN DEL MES")
        lbl_p.setStyleSheet("color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;")
        lay.addWidget(lbl_p)

        self._proy_frame_inner = QFrame()
        self._proy_frame_inner.setStyleSheet(
            "QFrame { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:7px; }"
        )
        fila_proy = QHBoxLayout(self._proy_frame_inner)
        fila_proy.setContentsMargins(12, 8, 12, 8)
        fila_proy.setSpacing(18)

        self._proy_dia      = self._info_chip("Día del mes",             "—")
        self._proy_meta     = self._info_chip("Meta acumulada",          "$ 0")
        self._proy_util     = self._info_chip("Utilidad acumulada",      "$ 0")
        self._proy_dif_chip = self._proy_diferencia_chip()

        fila_proy.addWidget(self._proy_dia)
        fila_proy.addWidget(self._sep_v())
        fila_proy.addWidget(self._proy_meta)
        fila_proy.addWidget(self._sep_v())
        fila_proy.addWidget(self._proy_util)
        fila_proy.addWidget(self._sep_v())
        fila_proy.addWidget(self._proy_dif_chip)
        fila_proy.addStretch()
        lay.addWidget(self._proy_frame_inner)

        lay.addStretch()
        return frame

    # ── Panel productos vendidos (ancho completo, abajo) ──────────────

    def _panel_productos(self) -> QFrame:
        """Productos vendidos en el día — panel ancho completo."""
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
        lbl.setStyleSheet("color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;")
        lay.addWidget(lbl)

        # Encabezado de columnas
        hdr = QHBoxLayout()
        for texto, stretch, alin in [
            ("Producto", 5, Qt.AlignLeft),
            ("Cant.", 1, Qt.AlignCenter),
            ("Ingresos", 2, Qt.AlignRight),
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

        # Área scrollable para las filas
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

        self._lbl_sin_ventas_prod = QLabel("Sin ventas registradas para esta fecha.")
        self._lbl_sin_ventas_prod.setStyleSheet(
            "color:#9CA3AF; font-size:12px; font-style:italic; padding:4px 0;"
        )
        self._lay_productos.addWidget(self._lbl_sin_ventas_prod)

        scroll.setWidget(self._contenedor_prods)
        lay.addWidget(scroll)

        return self._frame_productos

    def _proy_diferencia_chip(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(2)
        lbl_e = QLabel("SITUACIÓN")
        lbl_e.setStyleSheet("color:#6B7280; font-size:10px; font-weight:bold;")
        self._proy_dif_label = QLabel("—")
        self._proy_dif_label.setStyleSheet("font-size:14px; font-weight:bold; color:#374151;")
        lay.addWidget(lbl_e); lay.addWidget(self._proy_dif_label)
        w._lbl_valor = self._proy_dif_label
        return w

    def _info_chip(self, etiqueta: str, valor: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(2)
        lbl_e = QLabel(etiqueta)
        lbl_e.setStyleSheet("color:#6B7280; font-size:10px; font-weight:bold;")
        lbl_v = QLabel(valor)
        lbl_v.setStyleSheet("color:#374151; font-size:14px; font-weight:bold;")
        lay.addWidget(lbl_e); lay.addWidget(lbl_v)
        w._lbl_valor = lbl_v
        return w

    def _sep_v(self) -> QFrame:
        s = QFrame(); s.setFrameShape(QFrame.VLine)
        s.setFixedHeight(36); s.setStyleSheet("color:#CBD5E1;")
        return s

    # ------------------------------------------------------------------
    # Navegación entre días
    # ------------------------------------------------------------------

    def _dia_anterior(self):
        self.date_selector.setDate(self.date_selector.date().addDays(-1))

    def _dia_siguiente(self):
        self.date_selector.setDate(self.date_selector.date().addDays(1))

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

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
            subtitulo=f"Margen bruto: {porcentaje(r.margen_porcentual, 1)}",
            color_valor=color_neta,
        )

        self.card_utilidad.actualizar(r.utilidad_real, r.ganancia_neta,
                                      r.gasto_diario, r.gastos_operativos)

        from database.config_repo import obtener_configuracion
        cfg = obtener_configuracion()
        self._lbl_gasto_dia._lbl_valor.setText(cop(r.gasto_diario))
        self._lbl_gasto_extra._lbl_valor.setText(cop(r.gastos_operativos))
        self._lbl_gasto_mes._lbl_valor.setText(cop(cfg.total_gastos_mes))
        self._lbl_margen._lbl_valor.setText(porcentaje(r.margen_porcentual, 1))

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
        # ── Chips de métodos ──────────────────────────────────────────
        while self._lay_metodos.count():
            item = self._lay_metodos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not por_metodo:
            self._lay_metodos.addWidget(self._lbl_sin_ventas_met)
        else:
            for metodo, total in sorted(por_metodo.items()):
                bg, fg = _COLORES_METODO.get(metodo, ("#F3F4F6", "#374151"))
                lbl = QLabel(f"  {metodo}  {cop(total)}  ")
                lbl.setStyleSheet(
                    f"background:{bg}; color:{fg}; border-radius:5px;"
                    f"font-size:12px; font-weight:bold; padding:4px 10px;"
                )
                self._lay_metodos.addWidget(lbl)
            self._lay_metodos.addStretch()

        # ── Filas de productos ────────────────────────────────────────
        while self._lay_productos.count():
            item = self._lay_productos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not productos:
            self._lay_productos.addWidget(self._lbl_sin_ventas_prod)
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

            color_g = "#15803D" if ganancia >= 0 else "#DC2626"
            lbl_ing = QLabel(cop(ingresos))
            lbl_ing.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl_ing.setStyleSheet("font-size:11px; color:#374151;")

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
            contenedor.setStyleSheet(
                f"background:{fondo}; border-radius:4px;"
            )
            self._lay_productos.addWidget(contenedor)

        self._lay_productos.addStretch()

    def _actualizar_proyeccion(self, p: dict):
        self._proy_dia._lbl_valor.setText(f"Día {p['dia']} de {p['dias_mes']}")
        self._proy_meta._lbl_valor.setText(cop(p["meta"]))
        self._proy_util._lbl_valor.setText(cop(p["utilidad_acumulada"]))

        dif = p["diferencia"]
        if dif >= 0:
            texto = f"+{cop(dif)}  SUPERÁVIT"
            color = "#15803D"; bg = "#DCFCE7"
        else:
            texto = f"{cop(dif)}  DÉFICIT"
            color = "#DC2626"; bg = "#FEE2E2"

        self._proy_dif_label.setText(texto)
        self._proy_dif_label.setStyleSheet(
            f"font-size:13px; font-weight:bold; color:{color};"
        )
        self._proy_frame_inner.setStyleSheet(
            f"QFrame {{ background:{bg}; border:1px solid {color}40; border-radius:7px; }}"
        )

    def _actualizar_alertas(self, alertas: dict):
        partes = []
        if alertas["prestamos"] > 0:
            partes.append(f"⚠  {alertas['prestamos']} préstamo(s) pendiente(s)")
        if alertas["facturas"] > 0:
            partes.append(
                f"🧾  {alertas['facturas']} factura(s) por pagar"
                f"  ({cop(alertas['total_facturas'])})"
            )
        if partes:
            self._lbl_alertas.setText("   |   ".join(partes))
            self._banner.setVisible(True)
        else:
            self._banner.setVisible(False)
