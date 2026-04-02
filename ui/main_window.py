"""
Ventana principal de la aplicación YJBMOTOCOM.
Integra todas las secciones del sistema de control de rentabilidad.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QFrame, QStatusBar,
    QMessageBox, QDialog, QFormLayout, QDoubleSpinBox,
    QSpinBox, QPushButton, QGroupBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon

from config import (
    APP_NAME, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT,
    WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT, formatear_moneda
)
from database.db_manager import DatabaseManager
from logic.calculator import RentabilityCalculator
from .sales_panel import SalesPanel
from .monthly_view import MonthlyView
from .styles import STYLESHEET


class ConfigDialog(QDialog):
    """
    Diálogo para configurar los gastos fijos del negocio.
    """

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("Configuración de Gastos")
        self.setMinimumWidth(400)
        self._setup_ui()
        self._cargar_configuracion()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Título
        titulo = QLabel("Configuración de Gastos Fijos Mensuales")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(titulo)

        # Formulario
        form_group = QGroupBox("Gastos Mensuales (COP)")
        form_layout = QFormLayout(form_group)

        self.spin_arriendo = QDoubleSpinBox()
        self.spin_arriendo.setRange(0, 999999999)
        self.spin_arriendo.setDecimals(0)
        self.spin_arriendo.setSingleStep(100000)
        self.spin_arriendo.setPrefix("$ ")
        form_layout.addRow("Arriendo:", self.spin_arriendo)

        self.spin_sueldo = QDoubleSpinBox()
        self.spin_sueldo.setRange(0, 999999999)
        self.spin_sueldo.setDecimals(0)
        self.spin_sueldo.setSingleStep(100000)
        self.spin_sueldo.setPrefix("$ ")
        form_layout.addRow("Sueldo Empleada:", self.spin_sueldo)

        self.spin_servicios = QDoubleSpinBox()
        self.spin_servicios.setRange(0, 999999999)
        self.spin_servicios.setDecimals(0)
        self.spin_servicios.setSingleStep(50000)
        self.spin_servicios.setPrefix("$ ")
        form_layout.addRow("Servicios:", self.spin_servicios)

        layout.addWidget(form_group)

        # Comisión Bold
        bold_group = QGroupBox("Comisión Bold")
        bold_layout = QFormLayout(bold_group)

        self.spin_comision = QDoubleSpinBox()
        self.spin_comision.setRange(0, 100)
        self.spin_comision.setDecimals(2)
        self.spin_comision.setSingleStep(0.1)
        self.spin_comision.setSuffix(" %")
        bold_layout.addRow("Porcentaje:", self.spin_comision)

        layout.addWidget(bold_group)

        # Días del mes
        dias_group = QGroupBox("Cálculo Diario")
        dias_layout = QFormLayout(dias_group)

        self.spin_dias = QSpinBox()
        self.spin_dias.setRange(1, 31)
        dias_layout.addRow("Días del mes:", self.spin_dias)

        layout.addWidget(dias_group)

        # Resumen
        self.lbl_resumen = QLabel()
        self.lbl_resumen.setStyleSheet("""
            background-color: #ebf5fb;
            padding: 15px;
            border-radius: 8px;
            font-size: 13px;
        """)
        layout.addWidget(self.lbl_resumen)

        # Conectar señales para actualizar resumen
        self.spin_arriendo.valueChanged.connect(self._actualizar_resumen)
        self.spin_sueldo.valueChanged.connect(self._actualizar_resumen)
        self.spin_servicios.valueChanged.connect(self._actualizar_resumen)
        self.spin_dias.valueChanged.connect(self._actualizar_resumen)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)

        btn_guardar = QPushButton("Guardar")
        btn_guardar.setObjectName("btnRegistrar")
        btn_guardar.clicked.connect(self._guardar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def _cargar_configuracion(self):
        """Carga la configuración actual."""
        config = self.db.obtener_configuracion()
        self.spin_arriendo.setValue(config.arriendo)
        self.spin_sueldo.setValue(config.sueldo)
        self.spin_servicios.setValue(config.servicios)
        self.spin_comision.setValue(config.comision_bold)
        self.spin_dias.setValue(config.dias_mes)
        self._actualizar_resumen()

    def _actualizar_resumen(self):
        """Actualiza el resumen de gastos."""
        total = self.spin_arriendo.value() + self.spin_sueldo.value() + self.spin_servicios.value()
        dias = self.spin_dias.value()
        diario = total / dias if dias > 0 else 0

        self.lbl_resumen.setText(
            f"<b>Total Gastos Mensuales:</b> {formatear_moneda(total)}<br>"
            f"<b>Gasto Operativo Diario:</b> {formatear_moneda(diario)}"
        )

    def _guardar(self):
        """Guarda la configuración."""
        from database.models import Configuracion

        config = Configuracion(
            arriendo=self.spin_arriendo.value(),
            sueldo=self.spin_sueldo.value(),
            servicios=self.spin_servicios.value(),
            comision_bold=self.spin_comision.value(),
            dias_mes=self.spin_dias.value()
        )

        if self.db.guardar_configuracion(config):
            QMessageBox.information(self, "Éxito", "Configuración guardada correctamente.")
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "No se pudo guardar la configuración.")


class MainWindow(QMainWindow):
    """
    Ventana principal de la aplicación.
    """

    def __init__(self):
        super().__init__()

        # Inicializar componentes
        self.db = DatabaseManager()
        self.calculator = RentabilityCalculator(self.db)

        self._setup_ui()
        self._setup_connections()
        self._setup_statusbar()

    def _setup_ui(self):
        """Configura la interfaz de usuario."""
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        # Aplicar estilos
        self.setStyleSheet(STYLESHEET)

        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Encabezado
        header = self._crear_header()
        layout.addWidget(header)

        # Contenedor de pestañas
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Sección 1: Ventas del Día
        self.sales_panel = SalesPanel(self.calculator)
        self.tabs.addTab(self.sales_panel, "  Ventas del Día  ")

        # Sección 2: Historial Mensual
        self.monthly_view = MonthlyView(self.calculator)
        self.tabs.addTab(self.monthly_view, "  Historial Mensual  ")

        layout.addWidget(self.tabs)

    def _crear_header(self) -> QFrame:
        """Crea el encabezado de la aplicación."""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                padding: 15px;
            }
        """)
        header.setFixedHeight(70)

        layout = QHBoxLayout(header)

        # Logo/Título
        titulo = QLabel(APP_NAME)
        titulo.setStyleSheet("""
            color: white;
            font-size: 20px;
            font-weight: bold;
        """)
        layout.addWidget(titulo)

        # Subtítulo
        subtitulo = QLabel("Sistema de Control de Rentabilidad")
        subtitulo.setStyleSheet("""
            color: #bdc3c7;
            font-size: 12px;
        """)
        layout.addWidget(subtitulo)

        layout.addStretch()

        # Indicador de gasto diario
        config = self.calculator.config
        gasto_label = QLabel(f"Gasto Diario: {formatear_moneda(config.gasto_diario)}")
        gasto_label.setStyleSheet("""
            color: #f39c12;
            font-size: 14px;
            font-weight: bold;
            padding: 5px 15px;
            background-color: rgba(243, 156, 18, 0.2);
            border-radius: 5px;
        """)
        self.gasto_label = gasto_label
        layout.addWidget(gasto_label)

        # Botón de configuración
        btn_config = QPushButton("Configuración")
        btn_config.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #4a6278;
            }
        """)
        btn_config.clicked.connect(self._abrir_configuracion)
        layout.addWidget(btn_config)

        return header

    def _setup_connections(self):
        """Configura las conexiones de señales."""
        # Cuando se registra una venta, actualizar vista mensual
        self.sales_panel.venta_registrada.connect(self._on_venta_registrada)

        # Cuando cambia de pestaña, refrescar datos
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _setup_statusbar(self):
        """Configura la barra de estado."""
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Listo")

        # Timer para actualizar hora
        self.timer = QTimer()
        self.timer.timeout.connect(self._actualizar_hora)
        self.timer.start(1000)

        # Label de hora
        self.hora_label = QLabel()
        self.statusBar.addPermanentWidget(self.hora_label)
        self._actualizar_hora()

    def _actualizar_hora(self):
        """Actualiza la hora en la barra de estado."""
        from datetime import datetime
        ahora = datetime.now()
        self.hora_label.setText(ahora.strftime("%d/%m/%Y  %H:%M:%S"))

    def _on_venta_registrada(self):
        """Maneja el evento de venta registrada."""
        self.statusBar.showMessage("Venta registrada correctamente", 3000)

    def _on_tab_changed(self, index: int):
        """Maneja el cambio de pestaña."""
        if index == 1:  # Pestaña de historial mensual
            self.monthly_view.refrescar()

    def _abrir_configuracion(self):
        """Abre el diálogo de configuración."""
        dialog = ConfigDialog(self.db, self)
        if dialog.exec() == QDialog.Accepted:
            # Refrescar calculador y vistas
            self.calculator.refrescar_configuracion()
            self.sales_panel.refrescar()

            # Actualizar label de gasto diario
            config = self.calculator.config
            self.gasto_label.setText(f"Gasto Diario: {formatear_moneda(config.gasto_diario)}")

            if self.tabs.currentIndex() == 1:
                self.monthly_view.refrescar()

    def closeEvent(self, event):
        """Maneja el cierre de la aplicación."""
        # Confirmar cierre
        respuesta = QMessageBox.question(
            self, "Confirmar salida",
            "¿Está seguro de que desea cerrar la aplicación?",
            QMessageBox.Yes | QMessageBox.No
        )

        if respuesta == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
