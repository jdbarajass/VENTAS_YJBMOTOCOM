"""
Vista mensual de ventas y rentabilidad.
Sección 2: Historial de ventas separado por mes.
"""

from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QSizePolicy, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from config import formatear_moneda
from logic.calculator import RentabilityCalculator
from logic.reports import ReportGenerator
from .styles import get_card_style, COLORS


class BarChartWidget(QWidget):
    """
    Widget para gráfica de barras de utilidad diaria.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.datos = []
        self.setMinimumHeight(250)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_datos(self, fechas: list, valores: list):
        """Actualiza los datos de la gráfica."""
        self.datos = list(zip(fechas, valores))
        self.update()

    def paintEvent(self, event):
        """Dibuja la gráfica de barras."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fondo
        painter.fillRect(self.rect(), QColor("#ffffff"))

        if not self.datos:
            painter.setPen(QColor("#7f8c8d"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Sin datos para mostrar")
            painter.end()
            return

        # Dimensiones
        width = self.width()
        height = self.height()
        margin_left = 80
        margin_right = 20
        margin_top = 30
        margin_bottom = 50
        chart_width = width - margin_left - margin_right
        chart_height = height - margin_top - margin_bottom

        # Encontrar valores máximo y mínimo
        valores = [v for _, v in self.datos]
        max_val = max(max(valores), 0) * 1.1  # 10% extra
        min_val = min(min(valores), 0) * 1.1

        if max_val == min_val:
            max_val = max_val + 1 if max_val >= 0 else 1
            min_val = min_val - 1 if min_val < 0 else -1

        rango = max_val - min_val

        # Calcular posición del eje cero
        zero_y = margin_top + chart_height * (max_val / rango)

        # Título
        painter.setPen(QColor("#2c3e50"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(11)
        painter.setFont(font)
        painter.drawText(margin_left, 20, "Utilidad Diaria del Mes")

        # Dibujar líneas de referencia horizontales
        painter.setPen(QPen(QColor("#ecf0f1"), 1, Qt.DashLine))
        font.setBold(False)
        font.setPointSize(9)
        painter.setFont(font)

        # Líneas de referencia
        num_lineas = 5
        for i in range(num_lineas + 1):
            y = margin_top + (chart_height / num_lineas) * i
            valor = max_val - (rango / num_lineas) * i
            painter.drawLine(margin_left, int(y), width - margin_right, int(y))

            # Etiqueta de valor
            painter.setPen(QColor("#7f8c8d"))
            texto = formatear_moneda(valor)
            painter.drawText(5, int(y) + 4, texto)
            painter.setPen(QPen(QColor("#ecf0f1"), 1, Qt.DashLine))

        # Dibujar eje horizontal (línea del cero) más gruesa
        painter.setPen(QPen(QColor("#2c3e50"), 2))
        painter.drawLine(margin_left, int(zero_y), width - margin_right, int(zero_y))

        # Ancho de cada barra
        num_barras = len(self.datos)
        spacing = chart_width / num_barras
        bar_width = spacing * 0.7

        # Dibujar barras
        for i, (fecha, valor) in enumerate(self.datos):
            x = margin_left + i * spacing + (spacing - bar_width) / 2

            # Altura de la barra proporcional al valor
            bar_height = abs(valor) / rango * chart_height

            if valor >= 0:
                y = zero_y - bar_height
                color = QColor(COLORS["success"])
                color_borde = QColor("#1e8449")
            else:
                y = zero_y
                color = QColor(COLORS["danger"])
                color_borde = QColor("#a93226")

            # Dibujar barra con borde
            painter.fillRect(int(x), int(y), int(bar_width), int(bar_height), color)
            painter.setPen(QPen(color_borde, 1))
            painter.drawRect(int(x), int(y), int(bar_width), int(bar_height))

            # Etiqueta de fecha
            painter.setPen(QColor("#2c3e50"))
            font.setPointSize(8)
            painter.setFont(font)
            text_x = int(x + bar_width / 2 - 8)
            painter.drawText(text_x, height - 10, fecha)

        painter.end()


class MonthlyView(QWidget):
    """
    Vista completa del historial mensual.
    Sección 2 del sistema: Ventas diarias separadas mes a mes.
    """

    def __init__(self, calculator: RentabilityCalculator, parent=None):
        super().__init__(parent)
        self.calculator = calculator
        self.report_generator = ReportGenerator()
        self._setup_ui()
        self._cargar_meses()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Encabezado
        header = QHBoxLayout()

        titulo = QLabel("Historial Mensual")
        titulo.setObjectName("lblTitulo")
        header.addWidget(titulo)

        header.addStretch()

        # Selector de mes
        header.addWidget(QLabel("Seleccionar Mes:"))
        self.combo_mes = QComboBox()
        self.combo_mes.setMinimumWidth(200)
        self.combo_mes.currentIndexChanged.connect(self._on_mes_changed)
        header.addWidget(self.combo_mes)

        self.btn_exportar = QPushButton("Exportar Mes a Excel")
        self.btn_exportar.setObjectName("btnExportar")
        self.btn_exportar.clicked.connect(self._exportar_mes)
        header.addWidget(self.btn_exportar)

        layout.addLayout(header)

        # Splitter para dividir resumen y detalle
        splitter = QSplitter(Qt.Vertical)

        # Panel superior: Resumen del mes y gráfica
        panel_superior = QWidget()
        layout_superior = QVBoxLayout(panel_superior)
        layout_superior.setContentsMargins(0, 0, 0, 0)
        layout_superior.setSpacing(15)

        # Resumen del mes
        layout_superior.addWidget(self._crear_resumen_mensual())

        # Gráfica
        grafica_frame = QFrame()
        grafica_frame.setStyleSheet(get_card_style("normal"))
        grafica_layout = QVBoxLayout(grafica_frame)

        self.grafica = BarChartWidget()
        grafica_layout.addWidget(self.grafica)

        layout_superior.addWidget(grafica_frame)

        splitter.addWidget(panel_superior)

        # Panel inferior: Tabla de detalle diario
        panel_inferior = QWidget()
        layout_inferior = QVBoxLayout(panel_inferior)
        layout_inferior.setContentsMargins(0, 0, 0, 0)

        layout_inferior.addWidget(self._crear_tabla_diaria())

        splitter.addWidget(panel_inferior)

        # Proporciones del splitter
        splitter.setSizes([400, 300])

        layout.addWidget(splitter)

    def _crear_resumen_mensual(self) -> QFrame:
        """Crea el panel de resumen mensual."""
        frame = QFrame()
        frame.setStyleSheet(get_card_style("normal"))

        layout = QVBoxLayout(frame)
        layout.setSpacing(15)

        # Título del período
        self.lbl_periodo = QLabel("Seleccione un mes")
        self.lbl_periodo.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(self.lbl_periodo)

        # Grid de métricas
        grid = QGridLayout()
        grid.setSpacing(20)

        # Fila 1
        self.cards = {}

        metricas = [
            ("total_ventas", "Total Ventas", 0, 0),
            ("total_costos", "Total Costos", 0, 1),
            ("ganancia_bruta", "Ganancia Bruta", 0, 2),
            ("comisiones", "Total Comisiones", 0, 3),
            ("gastos_op", "Gastos Operativos", 1, 0),
            ("utilidad", "UTILIDAD REAL", 1, 1),
            ("dias_positivos", "Días Positivos", 1, 2),
            ("dias_negativos", "Días Negativos", 1, 3),
        ]

        for key, titulo, row, col in metricas:
            card = self._crear_mini_card(titulo)
            self.cards[key] = card
            grid.addWidget(card, row, col)

        layout.addLayout(grid)

        return frame

    def _crear_mini_card(self, titulo: str) -> QFrame:
        """Crea una mini tarjeta de métrica."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #ecf0f1;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet("color: #7f8c8d; font-size: 11px; border: none;")
        layout.addWidget(lbl_titulo)

        lbl_valor = QLabel("$0")
        lbl_valor.setStyleSheet("color: #2c3e50; font-size: 16px; font-weight: bold; border: none;")
        lbl_valor.setObjectName("valor")
        layout.addWidget(lbl_valor)

        return frame

    def _crear_tabla_diaria(self) -> QGroupBox:
        """Crea la tabla de detalle diario."""
        grupo = QGroupBox("Detalle por Día")

        layout = QVBoxLayout(grupo)
        layout.setContentsMargins(10, 20, 10, 10)

        self.tabla_dias = QTableWidget()
        self.tabla_dias.setColumnCount(8)
        self.tabla_dias.setHorizontalHeaderLabels([
            "Fecha", "# Ventas", "Ventas", "Costos",
            "Gan. Bruta", "Comisiones", "Gasto Op.", "Utilidad"
        ])

        # Configurar columnas
        header = self.tabla_dias.horizontalHeader()
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        self.tabla_dias.setAlternatingRowColors(True)
        self.tabla_dias.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_dias.verticalHeader().setVisible(False)
        self.tabla_dias.setSortingEnabled(True)

        layout.addWidget(self.tabla_dias)

        return grupo

    def _cargar_meses(self):
        """Carga los meses disponibles en el combo."""
        self.combo_mes.clear()

        meses = self.calculator.obtener_meses_disponibles()

        if not meses:
            # Agregar mes actual si no hay datos
            hoy = date.today()
            self.combo_mes.addItem(
                f"{self._nombre_mes(hoy.month)} {hoy.year}",
                (hoy.year, hoy.month)
            )
        else:
            for anio, mes, nombre in meses:
                self.combo_mes.addItem(nombre, (anio, mes))

        # Seleccionar el primer mes
        if self.combo_mes.count() > 0:
            self._on_mes_changed(0)

    def _nombre_mes(self, mes: int) -> str:
        """Retorna el nombre del mes."""
        nombres = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        return nombres[mes - 1]

    def _on_mes_changed(self, index: int):
        """Maneja el cambio de mes seleccionado."""
        if index < 0:
            return

        data = self.combo_mes.currentData()
        if data:
            anio, mes = data
            self._cargar_datos_mes(anio, mes)

    def _cargar_datos_mes(self, anio: int, mes: int):
        """Carga los datos del mes seleccionado."""
        # Obtener resumen mensual
        resumen = self.calculator.obtener_resumen_mes(anio, mes)

        # Actualizar título
        self.lbl_periodo.setText(f"Resumen de {resumen.periodo}")

        # Actualizar cards
        self._actualizar_card("total_ventas", resumen.total_ventas)
        self._actualizar_card("total_costos", resumen.total_costos)
        self._actualizar_card("ganancia_bruta", resumen.ganancia_bruta)
        self._actualizar_card("comisiones", resumen.total_comisiones)
        self._actualizar_card("gastos_op", resumen.total_gastos_operativos)
        self._actualizar_card("utilidad", resumen.utilidad_real, es_utilidad=True)
        self._actualizar_card("dias_positivos", resumen.dias_positivos, es_moneda=False, color="#27ae60")
        self._actualizar_card("dias_negativos", resumen.dias_negativos, es_moneda=False, color="#e74c3c")

        # Cargar detalle diario
        self._cargar_tabla_diaria(anio, mes)

        # Cargar gráfica
        self._cargar_grafica(anio, mes)

    def _actualizar_card(self, key: str, valor, es_moneda: bool = True,
                         es_utilidad: bool = False, color: str = None):
        """Actualiza el valor de una card."""
        card = self.cards.get(key)
        if card:
            lbl_valor = card.findChild(QLabel, "valor")
            if lbl_valor:
                if es_moneda:
                    lbl_valor.setText(formatear_moneda(valor))
                else:
                    lbl_valor.setText(str(valor))

                if es_utilidad:
                    if valor >= 0:
                        lbl_valor.setStyleSheet("color: #27ae60; font-size: 16px; font-weight: bold; border: none;")
                    else:
                        lbl_valor.setStyleSheet("color: #e74c3c; font-size: 16px; font-weight: bold; border: none;")
                elif color:
                    lbl_valor.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold; border: none;")

    def _cargar_tabla_diaria(self, anio: int, mes: int):
        """Carga la tabla de detalle diario."""
        resumenes = self.calculator.obtener_detalle_diario_mes(anio, mes)

        self.tabla_dias.setRowCount(len(resumenes))

        for row, resumen in enumerate(resumenes):
            # Fecha
            item_fecha = QTableWidgetItem(resumen.fecha.strftime("%d/%m/%Y"))
            item_fecha.setData(Qt.UserRole, resumen.fecha)
            self.tabla_dias.setItem(row, 0, item_fecha)

            # Número de ventas
            item_num = QTableWidgetItem(str(resumen.num_ventas))
            item_num.setTextAlignment(Qt.AlignCenter)
            self.tabla_dias.setItem(row, 1, item_num)

            # Ventas
            item_ventas = QTableWidgetItem(formatear_moneda(resumen.total_ventas))
            item_ventas.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_ventas.setData(Qt.UserRole, resumen.total_ventas)
            self.tabla_dias.setItem(row, 2, item_ventas)

            # Costos
            item_costos = QTableWidgetItem(formatear_moneda(resumen.total_costos))
            item_costos.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_costos.setData(Qt.UserRole, resumen.total_costos)
            self.tabla_dias.setItem(row, 3, item_costos)

            # Ganancia bruta
            item_gan = QTableWidgetItem(formatear_moneda(resumen.ganancia_bruta))
            item_gan.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_gan.setData(Qt.UserRole, resumen.ganancia_bruta)
            self.tabla_dias.setItem(row, 4, item_gan)

            # Comisiones
            item_com = QTableWidgetItem(formatear_moneda(resumen.total_comisiones))
            item_com.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_com.setData(Qt.UserRole, resumen.total_comisiones)
            self.tabla_dias.setItem(row, 5, item_com)

            # Gasto operativo
            item_gasto = QTableWidgetItem(formatear_moneda(resumen.gasto_operativo))
            item_gasto.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_gasto.setData(Qt.UserRole, resumen.gasto_operativo)
            self.tabla_dias.setItem(row, 6, item_gasto)

            # Utilidad
            item_util = QTableWidgetItem(formatear_moneda(resumen.utilidad_real))
            item_util.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_util.setData(Qt.UserRole, resumen.utilidad_real)

            if resumen.utilidad_real >= 0:
                item_util.setForeground(QColor(COLORS["success"]))
            else:
                item_util.setForeground(QColor(COLORS["danger"]))

            self.tabla_dias.setItem(row, 7, item_util)

    def _cargar_grafica(self, anio: int, mes: int):
        """Carga la gráfica de utilidad diaria."""
        datos = self.calculator.obtener_datos_grafica_mes(anio, mes)
        self.grafica.set_datos(datos["fechas"], datos["utilidades"])

    def _exportar_mes(self):
        """Exporta los datos del mes a Excel."""
        data = self.combo_mes.currentData()
        if not data:
            return

        anio, mes = data

        try:
            ruta = self.report_generator.exportar_ventas_mes(anio, mes)
            QMessageBox.information(
                self, "Exportación exitosa",
                f"El reporte se guardó en:\n{ruta}"
            )
            self.report_generator.abrir_carpeta_reportes()
        except ImportError:
            QMessageBox.warning(
                self, "Error",
                "Se requiere instalar pandas y openpyxl para exportar a Excel.\n"
                "Ejecute: pip install pandas openpyxl"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al exportar: {str(e)}")

    def refrescar(self):
        """Refresca los datos de la vista."""
        # Recargar meses disponibles
        mes_actual = self.combo_mes.currentData()
        self._cargar_meses()

        # Intentar seleccionar el mes que estaba seleccionado
        if mes_actual:
            for i in range(self.combo_mes.count()):
                if self.combo_mes.itemData(i) == mes_actual:
                    self.combo_mes.setCurrentIndex(i)
                    break
