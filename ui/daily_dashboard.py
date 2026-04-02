"""
Dashboard diario con métricas y gráficas.
Este módulo proporciona una vista completa del rendimiento diario.
"""

from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QDateEdit, QPushButton,
    QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPen

from config import formatear_moneda
from logic.calculator import RentabilityCalculator
from .styles import get_card_style, COLORS


class MetricCard(QFrame):
    """
    Widget de tarjeta para mostrar una métrica.
    """

    def __init__(self, titulo: str, color: str = "#3498db", parent=None):
        super().__init__(parent)
        self.color = color
        self._setup_ui(titulo)

    def _setup_ui(self, titulo: str):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: none;
                border-left: 5px solid {self.color};
                border-radius: 8px;
            }}
        """)
        self.setMinimumHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)

        # Título
        self.lbl_titulo = QLabel(titulo)
        self.lbl_titulo.setStyleSheet("color: #7f8c8d; font-size: 12px; border: none;")
        layout.addWidget(self.lbl_titulo)

        # Valor
        self.lbl_valor = QLabel("$0")
        self.lbl_valor.setStyleSheet(f"color: {self.color}; font-size: 22px; font-weight: bold; border: none;")
        layout.addWidget(self.lbl_valor)

        layout.addStretch()

    def set_valor(self, valor: float, formato_moneda: bool = True):
        """Actualiza el valor de la métrica."""
        if formato_moneda:
            self.lbl_valor.setText(formatear_moneda(valor))
        else:
            self.lbl_valor.setText(str(valor))

    def set_color_valor(self, color: str):
        """Cambia el color del valor."""
        self.lbl_valor.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold; border: none;")


class SimpleBarChart(QWidget):
    """
    Widget simple para mostrar gráfica de barras de utilidad.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.datos = []
        self.setMinimumHeight(200)

    def set_datos(self, fechas: list, valores: list):
        """Actualiza los datos de la gráfica."""
        self.datos = list(zip(fechas, valores))
        self.update()

    def paintEvent(self, event):
        """Dibuja la gráfica de barras."""
        if not self.datos:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Dimensiones
        width = self.width()
        height = self.height()
        margin = 40
        chart_width = width - 2 * margin
        chart_height = height - 2 * margin

        if len(self.datos) == 0:
            return

        # Encontrar valores máximo y mínimo
        valores = [v for _, v in self.datos]
        max_val = max(max(valores), 0)
        min_val = min(min(valores), 0)
        rango = max_val - min_val if max_val != min_val else 1

        # Calcular posición del eje cero
        zero_y = margin + chart_height * (max_val / rango)

        # Dibujar eje horizontal (línea del cero)
        painter.setPen(QPen(QColor("#dcdde1"), 2))
        painter.drawLine(margin, int(zero_y), width - margin, int(zero_y))

        # Ancho de cada barra
        bar_width = chart_width / len(self.datos) * 0.8
        spacing = chart_width / len(self.datos)

        # Dibujar barras
        for i, (fecha, valor) in enumerate(self.datos):
            x = margin + i * spacing + (spacing - bar_width) / 2

            # Altura de la barra proporcional al valor
            bar_height = abs(valor) / rango * chart_height

            if valor >= 0:
                y = zero_y - bar_height
                color = QColor(COLORS["success"])
            else:
                y = zero_y
                color = QColor(COLORS["danger"])

            # Dibujar barra
            painter.fillRect(int(x), int(y), int(bar_width), int(bar_height), color)

            # Etiqueta de fecha
            painter.setPen(QColor("#7f8c8d"))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(int(x), height - 5, fecha)

        painter.end()


class DailyDashboard(QWidget):
    """
    Dashboard completo para visualización diaria.
    """

    fecha_cambiada = Signal(date)

    def __init__(self, calculator: RentabilityCalculator, parent=None):
        super().__init__(parent)
        self.calculator = calculator
        self._setup_ui()
        self._actualizar()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Encabezado con selector de fecha
        header = QHBoxLayout()

        titulo = QLabel("Dashboard Diario")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header.addWidget(titulo)

        header.addStretch()

        header.addWidget(QLabel("Fecha:"))
        self.fecha_edit = QDateEdit()
        self.fecha_edit.setDate(QDate.currentDate())
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDisplayFormat("dd/MM/yyyy")
        self.fecha_edit.dateChanged.connect(self._on_fecha_changed)
        header.addWidget(self.fecha_edit)

        layout.addLayout(header)

        # Grid de métricas
        metricas_grid = QGridLayout()
        metricas_grid.setSpacing(15)

        self.card_ventas = MetricCard("Total Ventas", "#3498db")
        metricas_grid.addWidget(self.card_ventas, 0, 0)

        self.card_costos = MetricCard("Total Costos", "#e67e22")
        metricas_grid.addWidget(self.card_costos, 0, 1)

        self.card_ganancia = MetricCard("Ganancia Bruta", "#9b59b6")
        metricas_grid.addWidget(self.card_ganancia, 0, 2)

        self.card_comisiones = MetricCard("Comisiones Bold", "#e74c3c")
        metricas_grid.addWidget(self.card_comisiones, 1, 0)

        self.card_gasto = MetricCard("Gasto Operativo", "#34495e")
        metricas_grid.addWidget(self.card_gasto, 1, 1)

        self.card_utilidad = MetricCard("UTILIDAD REAL", "#27ae60")
        metricas_grid.addWidget(self.card_utilidad, 1, 2)

        layout.addLayout(metricas_grid)

        # Indicador de estado
        self.estado_frame = QFrame()
        self.estado_frame.setMinimumHeight(100)
        estado_layout = QVBoxLayout(self.estado_frame)

        self.lbl_estado_titulo = QLabel("Estado del Día")
        self.lbl_estado_titulo.setAlignment(Qt.AlignCenter)
        self.lbl_estado_titulo.setStyleSheet("font-size: 18px; font-weight: bold; border: none;")
        estado_layout.addWidget(self.lbl_estado_titulo)

        self.lbl_estado_detalle = QLabel("")
        self.lbl_estado_detalle.setAlignment(Qt.AlignCenter)
        self.lbl_estado_detalle.setStyleSheet("font-size: 14px; border: none;")
        estado_layout.addWidget(self.lbl_estado_detalle)

        layout.addWidget(self.estado_frame)

        # Desglose por método de pago
        desglose_frame = QFrame()
        desglose_frame.setStyleSheet(get_card_style("normal"))
        desglose_layout = QVBoxLayout(desglose_frame)

        desglose_titulo = QLabel("Desglose por Método de Pago")
        desglose_titulo.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        desglose_layout.addWidget(desglose_titulo)

        self.desglose_grid = QGridLayout()
        self.desglose_grid.setSpacing(10)

        self.lbl_efectivo = QLabel("Efectivo: $0")
        self.desglose_grid.addWidget(self.lbl_efectivo, 0, 0)

        self.lbl_bold = QLabel("Bold: $0")
        self.desglose_grid.addWidget(self.lbl_bold, 0, 1)

        self.lbl_transferencia = QLabel("Transferencia: $0")
        self.desglose_grid.addWidget(self.lbl_transferencia, 0, 2)

        desglose_layout.addLayout(self.desglose_grid)
        layout.addWidget(desglose_frame)

        layout.addStretch()

    def _on_fecha_changed(self, qdate):
        """Maneja el cambio de fecha."""
        self._actualizar()
        self.fecha_cambiada.emit(qdate.toPython())

    def _actualizar(self):
        """Actualiza todas las métricas del dashboard."""
        fecha = self.fecha_edit.date().toPython()
        resumen = self.calculator.obtener_resumen_fecha(fecha)

        # Actualizar cards
        self.card_ventas.set_valor(resumen.total_ventas)
        self.card_costos.set_valor(resumen.total_costos)
        self.card_ganancia.set_valor(resumen.ganancia_bruta)
        self.card_comisiones.set_valor(resumen.total_comisiones)
        self.card_gasto.set_valor(resumen.gasto_operativo)
        self.card_utilidad.set_valor(resumen.utilidad_real)

        # Color de utilidad
        if resumen.utilidad_real >= 0:
            self.card_utilidad.set_color_valor(COLORS["success"])
        else:
            self.card_utilidad.set_color_valor(COLORS["danger"])

        # Estado
        if resumen.utilidad_real >= 0:
            self.estado_frame.setStyleSheet(get_card_style("positivo"))
            self.lbl_estado_titulo.setText("EN ZONA DE GANANCIA")
            self.lbl_estado_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #27ae60; border: none;")
            self.lbl_estado_detalle.setText(f"Utilidad del día: {formatear_moneda(resumen.utilidad_real)}")
            self.lbl_estado_detalle.setStyleSheet("font-size: 14px; color: #27ae60; border: none;")
        else:
            self.estado_frame.setStyleSheet(get_card_style("negativo"))
            self.lbl_estado_titulo.setText("META NO ALCANZADA")
            self.lbl_estado_titulo.setStyleSheet("font-size: 18px; font-weight: bold; color: #e74c3c; border: none;")
            self.lbl_estado_detalle.setText(f"Faltan {formatear_moneda(abs(resumen.utilidad_real))} para cubrir gastos operativos")
            self.lbl_estado_detalle.setStyleSheet("font-size: 14px; color: #e74c3c; border: none;")

        # Desglose
        self.lbl_efectivo.setText(f"Efectivo: {formatear_moneda(resumen.ventas_efectivo)}")
        self.lbl_bold.setText(f"Bold: {formatear_moneda(resumen.ventas_bold)}")
        self.lbl_transferencia.setText(f"Transferencia: {formatear_moneda(resumen.ventas_transferencia)}")

    def refrescar(self):
        """Refresca los datos del dashboard."""
        self._actualizar()
