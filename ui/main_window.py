"""
ui/main_window.py
Ventana principal de YJBMOTOCOM.
Estructura: Sidebar de navegación (izquierda) + QStackedWidget (contenido).
Sin lógica de negocio.
"""

from datetime import date as _date

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStatusBar, QPushButton, QStackedWidget, QFrame,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from ui.venta_form import VentaForm
from ui.ventas_dia_panel import VentasDiaPanel
from ui.dashboard_panel import DashboardPanel
from ui.historial_panel import HistorialPanel
from ui.config_panel import ConfigPanel


# Índices de página en el QStackedWidget
PAGE_REGISTRAR = 0
PAGE_VENTAS_DIA = 1
PAGE_DASHBOARD = 2
PAGE_HISTORIAL = 3
PAGE_CONFIG = 4


class MainWindow(QMainWindow):
    """Shell principal con sidebar + stacked content."""

    APP_TITLE = "YJBMOTOCOM — Control de Rentabilidad"
    MIN_SIZE = QSize(1100, 700)

    def __init__(self) -> None:
        super().__init__()
        self._setup_window()
        self._build_ui()
        self._nav_buttons[PAGE_REGISTRAR].setChecked(True)

    # ------------------------------------------------------------------
    # Configuración de ventana
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowTitle(self.APP_TITLE)
        self.setMinimumSize(self.MIN_SIZE)
        self.resize(1280, 800)
        self._status = QStatusBar()
        self._status.showMessage("YJBMOTOCOM v2.0  •  Sistema listo")
        self.setStatusBar(self._status)

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content())

        self.setCentralWidget(central)

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet("background-color: #1E293B;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(2)

        # Logo / nombre
        logo = QLabel("YJBMOTOCOM")
        logo.setAlignment(Qt.AlignCenter)
        logo.setContentsMargins(0, 24, 0, 8)
        font_logo = QFont()
        font_logo.setPointSize(13)
        font_logo.setBold(True)
        logo.setFont(font_logo)
        logo.setStyleSheet("color: #F8FAFC; letter-spacing: 1px;")
        layout.addWidget(logo)

        sub = QLabel("Control de Rentabilidad")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #94A3B8; font-size: 10px;")
        layout.addWidget(sub)

        # Fecha actual
        hoy = _date.today()
        DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        MESES_ES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
                    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        fecha_str = f"{DIAS_ES[hoy.weekday()]}  {hoy.day} {MESES_ES[hoy.month]} {hoy.year}"
        lbl_fecha = QLabel(fecha_str)
        lbl_fecha.setAlignment(Qt.AlignCenter)
        lbl_fecha.setStyleSheet(
            "color: #64748B; font-size: 11px; margin-top: 6px;"
        )
        layout.addWidget(lbl_fecha)

        layout.addSpacing(20)
        layout.addWidget(self._separador_sidebar())
        layout.addSpacing(8)

        # Botones de navegación
        nav_items = [
            (PAGE_REGISTRAR, "＋  Registrar Venta"),
            (PAGE_VENTAS_DIA, "📋  Ventas del Día"),
            (PAGE_DASHBOARD, "📊  Dashboard"),
            (PAGE_HISTORIAL, "📅  Historial Mensual"),
            (PAGE_CONFIG, "⚙  Configuración"),
        ]

        self._nav_buttons: dict[int, QPushButton] = {}
        for page_idx, label in nav_items:
            btn = self._crear_nav_btn(label, page_idx)
            self._nav_buttons[page_idx] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Versión al pie
        version = QLabel("v2.0")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #475569; font-size: 10px;")
        layout.addWidget(version)

        return sidebar

    def _crear_nav_btn(self, label: str, page_idx: int) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setFixedHeight(42)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CBD5E1;
                border: none;
                text-align: left;
                padding-left: 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
            QPushButton:checked {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
            }
        """)
        btn.clicked.connect(lambda checked, idx=page_idx: self._navegar(idx))
        return btn

    def _separador_sidebar(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #334155;")
        return sep

    # ------------------------------------------------------------------
    # Área de contenido (stacked)
    # ------------------------------------------------------------------

    def _build_content(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setStyleSheet("background-color: #F8FAFC;")
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()

        # Página 0 — Registrar Venta (FASE 4)
        self._form_venta = VentaForm()
        self._stack.addWidget(self._form_venta)

        # Página 1 — Ventas del Día (FASE 5)
        self._ventas_dia = VentasDiaPanel()
        self._stack.addWidget(self._ventas_dia)

        # Página 2 — Dashboard Diario (FASE 6)
        self._dashboard = DashboardPanel()
        self._stack.addWidget(self._dashboard)

        # Página 3 — Historial Mensual (FASE 7)
        self._historial = HistorialPanel()
        self._stack.addWidget(self._historial)

        # Página 4 — Configuración (FASE 8)
        self._config = ConfigPanel()
        self._stack.addWidget(self._config)

        # Señales
        self._form_venta.venta_guardada.connect(self._on_venta_guardada)
        self._config.configuracion_guardada.connect(self._on_config_guardada)

        layout.addWidget(self._stack)
        return wrapper

    def _placeholder(self, titulo: str, fase: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignCenter)
        lbl = QLabel(f"{titulo}\n({fase} — próximamente)")
        lbl.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(14)
        lbl.setFont(f)
        lbl.setStyleSheet("color: #94A3B8;")
        v.addWidget(lbl)
        return w

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------

    def _navegar(self, page_idx: int) -> None:
        """Cambia la página visible y marca el botón activo."""
        self._stack.setCurrentIndex(page_idx)
        for idx, btn in self._nav_buttons.items():
            btn.setChecked(idx == page_idx)

    def set_page(self, page_idx: int) -> None:
        """API pública para cambiar de página desde controllers."""
        self._navegar(page_idx)

    # ------------------------------------------------------------------
    # Acceso a sub-vistas (para inyección en fases posteriores)
    # ------------------------------------------------------------------

    def replace_page(self, page_idx: int, widget: QWidget) -> None:
        """
        Reemplaza un placeholder por la vista real.
        Llamado por las fases 5–8 al completarse.
        """
        old = self._stack.widget(page_idx)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(page_idx, widget)

    def set_status(self, mensaje: str) -> None:
        self._status.showMessage(mensaje)

    def _on_venta_guardada(self, venta) -> None:
        """Refresca todas las vistas al registrar una venta."""
        self._ventas_dia.refresh()
        self._dashboard.refresh()
        self._historial.refresh()
        self._status.showMessage(
            f"Venta registrada: {venta.producto}  •  Ganancia neta: {venta.ganancia_neta:,.0f}"
        )

    def _on_config_guardada(self) -> None:
        """Al guardar config, recalcula dashboards e historial con los nuevos gastos."""
        self._dashboard.refresh()
        self._historial.refresh()
        self._status.showMessage(
            "Configuración guardada  •  Cálculos actualizados automáticamente"
        )
