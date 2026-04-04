"""
ui/dashboard_panel.py
Dashboard diario: tarjetas métricas + indicador utilidad real.
La vista más importante del sistema — responde "¿cuánto REALMENTE gané hoy?"
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QDateEdit, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from controllers.dashboard_controller import DashboardController
from services.reportes import ResumenDiario
from utils.formatters import cop, porcentaje, fecha_corta
from ui.styles import aplicar_sombra


class MetricCard(QFrame):
    """
    Tarjeta de métrica reutilizable.
    Muestra: título (gris pequeño) + valor principal (grande) + subtítulo opcional.
    """

    def __init__(
        self,
        titulo: str,
        valor: str = "—",
        subtitulo: str = "",
        color_valor: str = "#111827",
        fondo: str = "#FFFFFF",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            MetricCard {{
                background-color: {fondo};
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)

        self._lbl_titulo = QLabel(titulo.upper())
        self._lbl_titulo.setStyleSheet("color: #6B7280; font-size: 10px; font-weight: bold; letter-spacing: 0.5px;")
        lay.addWidget(self._lbl_titulo)

        self._lbl_valor = QLabel(valor)
        font_v = QFont()
        font_v.setPointSize(20)
        font_v.setBold(True)
        self._lbl_valor.setFont(font_v)
        self._lbl_valor.setStyleSheet(f"color: {color_valor};")
        lay.addWidget(self._lbl_valor)

        self._lbl_sub = QLabel(subtitulo)
        self._lbl_sub.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        self._lbl_sub.setVisible(bool(subtitulo))
        lay.addWidget(self._lbl_sub)

    def actualizar(
        self,
        valor: str,
        subtitulo: str = "",
        color_valor: str = "#111827",
        fondo: str = "#FFFFFF",
    ) -> None:
        self._lbl_valor.setText(valor)
        self._lbl_valor.setStyleSheet(f"color: {color_valor};")
        self._lbl_sub.setText(subtitulo)
        self._lbl_sub.setVisible(bool(subtitulo))
        self.setStyleSheet(f"""
            MetricCard {{
                background-color: {fondo};
                border: 1px solid #E5E7EB;
                border-radius: 10px;
            }}
        """)


class UtilityCard(QFrame):
    """
    Tarjeta grande y prominente para la UTILIDAD REAL.
    Es EL número que define si el día fue bueno o malo.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(130)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(6)

        self._lbl_titulo = QLabel("UTILIDAD REAL DEL DÍA")
        self._lbl_titulo.setStyleSheet(
            "font-size: 11px; font-weight: bold; letter-spacing: 0.5px;"
        )
        lay.addWidget(self._lbl_titulo)

        self._lbl_valor = QLabel("$ 0")
        font = QFont(); font.setPointSize(32); font.setBold(True)
        self._lbl_valor.setFont(font)
        lay.addWidget(self._lbl_valor)

        self._lbl_formula = QLabel("Ganancia neta  −  Gasto operativo diario")
        self._lbl_formula.setStyleSheet("font-size: 11px;")
        lay.addWidget(self._lbl_formula)

        self._set_estado_neutro()

    def actualizar(self, utilidad: float, ganancia_neta: float, gasto_diario: float) -> None:
        self._lbl_valor.setText(cop(utilidad))
        formula = (
            f"{cop(ganancia_neta)}  −  {cop(gasto_diario)}"
            f"  =  {cop(utilidad)}"
        )
        self._lbl_formula.setText(formula)

        if utilidad > 0:
            self._set_positivo()
        elif utilidad < 0:
            self._set_negativo()
        else:
            self._set_estado_neutro()

    def _set_positivo(self) -> None:
        self._aplicar_estilo("#DCFCE7", "#15803D", "#166534")

    def _set_negativo(self) -> None:
        self._aplicar_estilo("#FEE2E2", "#DC2626", "#991B1B")

    def _set_estado_neutro(self) -> None:
        self._aplicar_estilo("#F8FAFC", "#374151", "#6B7280")

    def _aplicar_estilo(self, fondo: str, color_titulo: str, color_valor: str) -> None:
        self.setStyleSheet(f"""
            UtilityCard {{
                background-color: {fondo};
                border: 2px solid {color_valor}40;
                border-radius: 12px;
            }}
        """)
        self._lbl_titulo.setStyleSheet(
            f"font-size: 11px; font-weight: bold; letter-spacing: 0.5px; color: {color_titulo};"
        )
        self._lbl_valor.setStyleSheet(f"color: {color_valor};")
        self._lbl_formula.setStyleSheet(f"font-size: 11px; color: {color_titulo};")


class DashboardPanel(QWidget):
    """Vista de dashboard con tarjetas métricas del día."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = DashboardController()
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(16)

        root.addLayout(self._barra_superior())
        root.addLayout(self._fila_tarjetas_pequeñas())
        root.addLayout(self._fila_tarjetas_grandes())
        root.addWidget(self._barra_gasto())
        root.addStretch()

    def _barra_superior(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Dashboard Diario")
        font = QFont(); font.setPointSize(16); font.setBold(True)
        titulo.setFont(font)

        self.date_selector = QDateEdit()
        self.date_selector.setCalendarPopup(True)
        self.date_selector.setDate(QDate.currentDate())
        self.date_selector.setDisplayFormat("dd/MM/yyyy")
        self.date_selector.setFixedHeight(34)
        self.date_selector.setFixedWidth(130)
        self.date_selector.dateChanged.connect(lambda _: self.refresh())

        btn_hoy = QPushButton("Hoy")
        btn_hoy.setFixedHeight(34)
        btn_hoy.setFixedWidth(60)
        btn_hoy.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_hoy.clicked.connect(lambda: self.date_selector.setDate(QDate.currentDate()))

        self._lbl_estado = QLabel("")
        self._lbl_estado.setFixedHeight(28)
        self._lbl_estado.setStyleSheet(
            "font-weight: bold; font-size: 12px; border-radius: 5px; padding: 0 12px;"
        )

        lay.addWidget(titulo)
        lay.addSpacing(12)
        lay.addWidget(QLabel("Fecha:"))
        lay.addWidget(self.date_selector)
        lay.addWidget(btn_hoy)
        lay.addSpacing(16)
        lay.addWidget(self._lbl_estado)
        lay.addStretch()
        return lay

    def _fila_tarjetas_pequeñas(self) -> QHBoxLayout:
        """4 tarjetas de métricas secundarias."""
        lay = QHBoxLayout()
        lay.setSpacing(14)

        self.card_ventas     = MetricCard("Ventas registradas", "0",  color_valor="#1D4ED8")
        self.card_ingresos   = MetricCard("Ingresos totales",   "$ 0", color_valor="#374151")
        self.card_costos     = MetricCard("Costos totales",     "$ 0", color_valor="#374151")
        self.card_comisiones = MetricCard("Comisiones pagadas", "$ 0", color_valor="#92400E")

        for card in (self.card_ventas, self.card_ingresos,
                     self.card_costos, self.card_comisiones):
            aplicar_sombra(card)
            lay.addWidget(card)

        return lay

    def _fila_tarjetas_grandes(self) -> QHBoxLayout:
        """2 tarjetas grandes: Ganancia neta y Utilidad real."""
        lay = QHBoxLayout()
        lay.setSpacing(14)

        self.card_g_bruta = MetricCard("Ganancia bruta",
                                       "$ 0", subtitulo="Precio − Costo",
                                       color_valor="#374151")
        self.card_g_neta  = MetricCard("Ganancia neta de ventas",
                                       "$ 0", subtitulo="Bruta − Comisiones",
                                       color_valor="#374151")
        self.card_utilidad = UtilityCard()

        aplicar_sombra(self.card_g_bruta)
        aplicar_sombra(self.card_g_neta)
        aplicar_sombra(self.card_utilidad, radio=16, opacidad=22)

        lay.addWidget(self.card_g_bruta, stretch=1)
        lay.addWidget(self.card_g_neta,  stretch=1)
        lay.addWidget(self.card_utilidad, stretch=2)

        return lay

    def _barra_gasto(self) -> QFrame:
        """Barra informativa sobre los gastos operativos."""
        self._barra = QFrame()
        self._barra.setFrameShape(QFrame.StyledPanel)
        self._barra.setStyleSheet(
            "QFrame { background:#F1F5F9; border:1px solid #E2E8F0; border-radius:8px; }"
        )
        lay = QHBoxLayout(self._barra)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(24)

        self._lbl_gasto_dia  = self._info_chip("Gasto operativo diario", "$ 0")
        self._lbl_gasto_mes  = self._info_chip("Gastos fijos del mes",   "$ 0")
        self._lbl_margen     = self._info_chip("Margen sobre ingresos",  "0.0 %")

        lay.addWidget(self._lbl_gasto_dia)
        lay.addWidget(self._sep_v())
        lay.addWidget(self._lbl_gasto_mes)
        lay.addWidget(self._sep_v())
        lay.addWidget(self._lbl_margen)
        lay.addStretch()
        return self._barra

    def _info_chip(self, etiqueta: str, valor: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lbl_e = QLabel(etiqueta)
        lbl_e.setStyleSheet("color:#6B7280; font-size:10px; font-weight:bold;")
        lbl_v = QLabel(valor)
        lbl_v.setStyleSheet("color:#374151; font-size:14px; font-weight:bold;")
        lay.addWidget(lbl_e)
        lay.addWidget(lbl_v)

        # Guardamos referencia al label del valor para actualizar luego
        w._lbl_valor = lbl_v
        return w

    def _sep_v(self) -> QFrame:
        s = QFrame(); s.setFrameShape(QFrame.VLine)
        s.setFixedHeight(36)
        s.setStyleSheet("color:#CBD5E1;")
        return s

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Recarga los datos para la fecha seleccionada y actualiza las tarjetas."""
        qd = self.date_selector.date()
        fecha = date(qd.year(), qd.month(), qd.day())
        resumen = self._ctrl.get_resumen_dia(fecha)
        self._actualizar_cards(resumen)

    def _actualizar_cards(self, r: ResumenDiario) -> None:
        # Tarjetas pequeñas
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

        # Ganancia bruta y neta
        color_bruta = "#16A34A" if r.ganancia_bruta >= 0 else "#DC2626"
        self.card_g_bruta.actualizar(cop(r.ganancia_bruta), color_valor=color_bruta)

        color_neta = "#16A34A" if r.ganancia_neta >= 0 else "#DC2626"
        self.card_g_neta.actualizar(
            cop(r.ganancia_neta),
            subtitulo=f"Margen bruto: {porcentaje(r.margen_porcentual, 1)}",
            color_valor=color_neta,
        )

        # Utilidad real (la tarjeta más importante)
        self.card_utilidad.actualizar(r.utilidad_real, r.ganancia_neta, r.gasto_diario)

        # Barra inferior de gastos
        from database.config_repo import obtener_configuracion
        cfg = obtener_configuracion()
        self._lbl_gasto_dia._lbl_valor.setText(cop(r.gasto_diario))
        self._lbl_gasto_mes._lbl_valor.setText(cop(cfg.total_gastos_mes))
        self._lbl_margen._lbl_valor.setText(porcentaje(r.margen_porcentual, 1))

        # Indicador de estado en la barra superior
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
