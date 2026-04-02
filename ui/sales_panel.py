"""
Panel de registro de ventas diarias.
Contiene el formulario de entrada y la tabla de ventas del día.
"""

from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QDoubleSpinBox, QDateEdit,
    QComboBox, QTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QMessageBox,
    QGroupBox, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont

from config import formatear_moneda, METODOS_PAGO
from logic.calculator import RentabilityCalculator
from logic.reports import ReportGenerator
from .styles import get_card_style, get_value_label_style, COLORS


class SalesPanel(QWidget):
    """
    Panel principal para el registro de ventas diarias.
    """

    # Señal emitida cuando se registra una venta
    venta_registrada = Signal()

    def __init__(self, calculator: RentabilityCalculator):
        super().__init__()
        self.calculator = calculator
        self.report_generator = ReportGenerator()
        self._setup_ui()
        self._cargar_ventas_hoy()
        self._actualizar_dashboard()

    def _setup_ui(self):
        """Configura la interfaz del panel."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título de la sección
        titulo = QLabel("Registro de Ventas del Día")
        titulo.setObjectName("lblTitulo")
        layout.addWidget(titulo)

        # Contenedor principal con formulario y dashboard
        contenedor_principal = QHBoxLayout()
        contenedor_principal.setSpacing(20)

        # Panel izquierdo: Formulario y tabla
        panel_izquierdo = QVBoxLayout()
        panel_izquierdo.setSpacing(15)

        # Formulario de registro
        panel_izquierdo.addWidget(self._crear_formulario())

        # Tabla de ventas del día
        panel_izquierdo.addWidget(self._crear_tabla_ventas())

        contenedor_principal.addLayout(panel_izquierdo, stretch=3)

        # Panel derecho: Dashboard
        panel_derecho = self._crear_dashboard()
        contenedor_principal.addWidget(panel_derecho, stretch=1)

        layout.addLayout(contenedor_principal)

    def _crear_formulario(self) -> QGroupBox:
        """Crea el formulario de registro de ventas."""
        grupo = QGroupBox("Nueva Venta")
        layout = QGridLayout(grupo)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 25, 20, 20)

        # Fila 1: Fecha y Producto
        layout.addWidget(QLabel("Fecha:"), 0, 0)
        self.fecha_edit = QDateEdit()
        self.fecha_edit.setDate(QDate.currentDate())
        self.fecha_edit.setCalendarPopup(True)
        self.fecha_edit.setDisplayFormat("dd/MM/yyyy")
        layout.addWidget(self.fecha_edit, 0, 1)

        layout.addWidget(QLabel("Producto:"), 0, 2)
        self.producto_edit = QLineEdit()
        self.producto_edit.setPlaceholderText("Nombre del producto...")
        layout.addWidget(self.producto_edit, 0, 3)

        # Fila 2: Costo y Precio de Venta
        layout.addWidget(QLabel("Costo ($):"), 1, 0)
        self.costo_spin = QDoubleSpinBox()
        self.costo_spin.setRange(0, 999999999)
        self.costo_spin.setDecimals(0)
        self.costo_spin.setSingleStep(1000)
        self.costo_spin.setPrefix("$ ")
        self.costo_spin.setGroupSeparatorShown(True)
        layout.addWidget(self.costo_spin, 1, 1)

        layout.addWidget(QLabel("Precio Venta ($):"), 1, 2)
        self.precio_spin = QDoubleSpinBox()
        self.precio_spin.setRange(0, 999999999)
        self.precio_spin.setDecimals(0)
        self.precio_spin.setSingleStep(1000)
        self.precio_spin.setPrefix("$ ")
        self.precio_spin.setGroupSeparatorShown(True)
        layout.addWidget(self.precio_spin, 1, 3)

        # Fila 3: Método de pago y Notas
        layout.addWidget(QLabel("Método de Pago:"), 2, 0)
        self.metodo_combo = QComboBox()
        self.metodo_combo.addItems(METODOS_PAGO)
        layout.addWidget(self.metodo_combo, 2, 1)

        layout.addWidget(QLabel("Notas:"), 2, 2)
        self.notas_edit = QLineEdit()
        self.notas_edit.setPlaceholderText("Notas opcionales...")
        layout.addWidget(self.notas_edit, 2, 3)

        # Fila 4: Preview de ganancia y botón
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet(get_card_style("info"))
        preview_layout = QHBoxLayout(self.preview_frame)

        self.lbl_preview = QLabel("Ganancia estimada: $0")
        self.lbl_preview.setStyleSheet("font-weight: bold; color: #2c3e50;")
        preview_layout.addWidget(self.lbl_preview)

        self.lbl_comision = QLabel("Comisión: $0")
        self.lbl_comision.setStyleSheet("color: #7f8c8d;")
        preview_layout.addWidget(self.lbl_comision)

        preview_layout.addStretch()

        layout.addWidget(self.preview_frame, 3, 0, 1, 3)

        # Botón de registro
        self.btn_registrar = QPushButton("REGISTRAR VENTA")
        self.btn_registrar.setObjectName("btnRegistrar")
        self.btn_registrar.setMinimumHeight(45)
        self.btn_registrar.clicked.connect(self._registrar_venta)
        layout.addWidget(self.btn_registrar, 3, 3)

        # Conectar señales para preview en tiempo real
        self.costo_spin.valueChanged.connect(self._actualizar_preview)
        self.precio_spin.valueChanged.connect(self._actualizar_preview)
        self.metodo_combo.currentTextChanged.connect(self._actualizar_preview)

        return grupo

    def _crear_tabla_ventas(self) -> QGroupBox:
        """Crea la tabla de ventas del día."""
        grupo = QGroupBox("Ventas de Hoy")
        layout = QVBoxLayout(grupo)
        layout.setContentsMargins(10, 20, 10, 10)

        # Barra de acciones
        barra_acciones = QHBoxLayout()

        self.lbl_total_ventas = QLabel("Total: 0 ventas")
        self.lbl_total_ventas.setStyleSheet("font-weight: bold;")
        barra_acciones.addWidget(self.lbl_total_ventas)

        barra_acciones.addStretch()

        self.btn_exportar_dia = QPushButton("Exportar a Excel")
        self.btn_exportar_dia.setObjectName("btnExportar")
        self.btn_exportar_dia.clicked.connect(self._exportar_dia)
        barra_acciones.addWidget(self.btn_exportar_dia)

        layout.addLayout(barra_acciones)

        # Tabla
        self.tabla_ventas = QTableWidget()
        self.tabla_ventas.setColumnCount(8)
        self.tabla_ventas.setHorizontalHeaderLabels([
            "Producto", "Costo", "Venta", "Método", "Comisión", "Gan. Neta", "Notas", "Acciones"
        ])

        # Configurar columnas
        header = self.tabla_ventas.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Producto
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        self.tabla_ventas.setAlternatingRowColors(True)
        self.tabla_ventas.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_ventas.verticalHeader().setVisible(False)

        layout.addWidget(self.tabla_ventas)

        return grupo

    def _crear_dashboard(self) -> QFrame:
        """Crea el panel de dashboard con métricas del día."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #dcdde1;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Título
        titulo = QLabel("Dashboard del Día")
        titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; border: none;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)

        # Métricas
        self.cards = {}

        metricas = [
            ("total_ventas", "Total Ventas", "#3498db"),
            ("total_costos", "Total Costos", "#e67e22"),
            ("ganancia_bruta", "Ganancia Bruta", "#9b59b6"),
            ("comisiones", "Comisiones Bold", "#e74c3c"),
            ("gasto_diario", "Gasto Operativo", "#34495e"),
            ("utilidad_real", "UTILIDAD REAL", "#27ae60"),
        ]

        for key, label, color in metricas:
            card = self._crear_metrica_card(label, color)
            self.cards[key] = card
            layout.addWidget(card)

        # Indicador de estado
        self.estado_frame = QFrame()
        self.estado_frame.setMinimumHeight(80)
        self.estado_layout = QVBoxLayout(self.estado_frame)
        self.estado_layout.setContentsMargins(10, 10, 10, 10)

        self.lbl_estado = QLabel("Estado del día")
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        self.lbl_estado.setWordWrap(True)
        self.lbl_estado.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        self.estado_layout.addWidget(self.lbl_estado)

        layout.addWidget(self.estado_frame)
        layout.addStretch()

        return frame

    def _crear_metrica_card(self, titulo: str, color: str) -> QFrame:
        """Crea una tarjeta de métrica."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #f8f9fa;
                border: none;
                border-left: 4px solid {color};
                border-radius: 5px;
                padding: 5px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet("font-size: 11px; color: #7f8c8d; border: none;")
        layout.addWidget(lbl_titulo)

        lbl_valor = QLabel("$0")
        lbl_valor.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {color}; border: none;")
        lbl_valor.setObjectName("valor")
        layout.addWidget(lbl_valor)

        return frame

    def _actualizar_preview(self):
        """Actualiza el preview de ganancia en tiempo real."""
        costo = self.costo_spin.value()
        precio = self.precio_spin.value()
        metodo = self.metodo_combo.currentText()

        ganancia_bruta = precio - costo
        comision = self.calculator.calcular_comision(precio, metodo)
        ganancia_neta = ganancia_bruta - comision

        # Actualizar etiquetas
        self.lbl_preview.setText(f"Ganancia estimada: {formatear_moneda(ganancia_neta)}")
        self.lbl_comision.setText(f"Comisión ({metodo}): {formatear_moneda(comision)}")

        # Cambiar color según resultado
        if ganancia_neta > 0:
            self.lbl_preview.setStyleSheet("font-weight: bold; color: #27ae60;")
        elif ganancia_neta < 0:
            self.lbl_preview.setStyleSheet("font-weight: bold; color: #e74c3c;")
        else:
            self.lbl_preview.setStyleSheet("font-weight: bold; color: #2c3e50;")

    def _registrar_venta(self):
        """Registra una nueva venta."""
        producto = self.producto_edit.text().strip()
        costo = self.costo_spin.value()
        precio = self.precio_spin.value()
        metodo = self.metodo_combo.currentText()
        notas = self.notas_edit.text().strip()
        fecha = self.fecha_edit.date().toPython()

        # Validaciones
        if not producto:
            QMessageBox.warning(self, "Error", "Debe ingresar el nombre del producto.")
            self.producto_edit.setFocus()
            return

        if costo <= 0:
            QMessageBox.warning(self, "Error", "El costo debe ser mayor a cero.")
            self.costo_spin.setFocus()
            return

        if precio <= 0:
            QMessageBox.warning(self, "Error", "El precio de venta debe ser mayor a cero.")
            self.precio_spin.setFocus()
            return

        if precio < costo:
            respuesta = QMessageBox.question(
                self, "Advertencia",
                f"El precio de venta ({formatear_moneda(precio)}) es menor al costo ({formatear_moneda(costo)}).\n"
                "¿Desea registrar esta venta con pérdida?",
                QMessageBox.Yes | QMessageBox.No
            )
            if respuesta == QMessageBox.No:
                return

        # Registrar venta
        try:
            venta = self.calculator.registrar_venta(
                producto=producto,
                costo=costo,
                precio_venta=precio,
                metodo_pago=metodo,
                notas=notas,
                fecha=fecha
            )

            # Limpiar formulario
            self._limpiar_formulario()

            # Actualizar tabla y dashboard
            self._cargar_ventas_hoy()
            self._actualizar_dashboard()

            # Emitir señal
            self.venta_registrada.emit()

            # Mostrar confirmación breve
            self.btn_registrar.setText("¡VENTA REGISTRADA!")
            self.btn_registrar.setStyleSheet("background-color: #27ae60;")

            # Restaurar botón después de 1.5 segundos
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, self._restaurar_boton)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al registrar la venta: {str(e)}")

    def _limpiar_formulario(self):
        """Limpia los campos del formulario."""
        self.producto_edit.clear()
        self.costo_spin.setValue(0)
        self.precio_spin.setValue(0)
        self.notas_edit.clear()
        self.metodo_combo.setCurrentIndex(0)
        self.producto_edit.setFocus()
        self._actualizar_preview()

    def _restaurar_boton(self):
        """Restaura el texto y estilo del botón de registro."""
        self.btn_registrar.setText("REGISTRAR VENTA")
        self.btn_registrar.setStyleSheet("")

    def _cargar_ventas_hoy(self):
        """Carga las ventas del día en la tabla."""
        fecha = self.fecha_edit.date().toPython()
        ventas = self.calculator.obtener_ventas_fecha(fecha)

        self.tabla_ventas.setRowCount(len(ventas))
        self.lbl_total_ventas.setText(f"Total: {len(ventas)} ventas")

        for row, venta in enumerate(ventas):
            # Producto
            self.tabla_ventas.setItem(row, 0, QTableWidgetItem(venta.producto))

            # Costo
            item_costo = QTableWidgetItem(formatear_moneda(venta.costo))
            item_costo.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tabla_ventas.setItem(row, 1, item_costo)

            # Venta
            item_venta = QTableWidgetItem(formatear_moneda(venta.precio_venta))
            item_venta.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tabla_ventas.setItem(row, 2, item_venta)

            # Método
            self.tabla_ventas.setItem(row, 3, QTableWidgetItem(venta.metodo_pago))

            # Comisión
            item_comision = QTableWidgetItem(formatear_moneda(venta.comision))
            item_comision.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if venta.comision > 0:
                item_comision.setForeground(Qt.red)
            self.tabla_ventas.setItem(row, 4, item_comision)

            # Ganancia Neta
            item_neta = QTableWidgetItem(formatear_moneda(venta.ganancia_neta))
            item_neta.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if venta.ganancia_neta > 0:
                item_neta.setForeground(Qt.darkGreen)
            elif venta.ganancia_neta < 0:
                item_neta.setForeground(Qt.red)
            self.tabla_ventas.setItem(row, 5, item_neta)

            # Notas
            self.tabla_ventas.setItem(row, 6, QTableWidgetItem(venta.notas or ""))

            # Botón eliminar
            btn_eliminar = QPushButton("Eliminar")
            btn_eliminar.setObjectName("btnEliminar")
            btn_eliminar.clicked.connect(lambda checked, vid=venta.id: self._eliminar_venta(vid))
            self.tabla_ventas.setCellWidget(row, 7, btn_eliminar)

    def _actualizar_dashboard(self):
        """Actualiza las métricas del dashboard."""
        fecha = self.fecha_edit.date().toPython()
        resumen = self.calculator.obtener_resumen_fecha(fecha)

        # Actualizar valores
        self._actualizar_card("total_ventas", resumen.total_ventas)
        self._actualizar_card("total_costos", resumen.total_costos)
        self._actualizar_card("ganancia_bruta", resumen.ganancia_bruta)
        self._actualizar_card("comisiones", resumen.total_comisiones)
        self._actualizar_card("gasto_diario", resumen.gasto_operativo)
        self._actualizar_card("utilidad_real", resumen.utilidad_real, es_utilidad=True)

        # Actualizar estado
        if resumen.utilidad_real >= 0:
            self.estado_frame.setStyleSheet(get_card_style("positivo"))
            self.lbl_estado.setText(f"EN ZONA DE GANANCIA\n+{formatear_moneda(resumen.utilidad_real)}")
            self.lbl_estado.setStyleSheet("font-weight: bold; font-size: 14px; color: #27ae60; border: none;")
        else:
            self.estado_frame.setStyleSheet(get_card_style("negativo"))
            self.lbl_estado.setText(f"Faltan {formatear_moneda(abs(resumen.utilidad_real))}\npara cubrir gastos")
            self.lbl_estado.setStyleSheet("font-weight: bold; font-size: 14px; color: #e74c3c; border: none;")

    def _actualizar_card(self, key: str, valor: float, es_utilidad: bool = False):
        """Actualiza el valor de una tarjeta de métrica."""
        card = self.cards.get(key)
        if card:
            lbl_valor = card.findChild(QLabel, "valor")
            if lbl_valor:
                lbl_valor.setText(formatear_moneda(valor))

                # Cambiar color si es utilidad
                if es_utilidad:
                    if valor >= 0:
                        lbl_valor.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60; border: none;")
                    else:
                        lbl_valor.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c; border: none;")

    def _eliminar_venta(self, venta_id: int):
        """Elimina una venta previa confirmación."""
        respuesta = QMessageBox.question(
            self, "Confirmar eliminación",
            "¿Está seguro de eliminar esta venta?",
            QMessageBox.Yes | QMessageBox.No
        )

        if respuesta == QMessageBox.Yes:
            if self.calculator.eliminar_venta(venta_id):
                self._cargar_ventas_hoy()
                self._actualizar_dashboard()
                self.venta_registrada.emit()
            else:
                QMessageBox.warning(self, "Error", "No se pudo eliminar la venta.")

    def _exportar_dia(self):
        """Exporta las ventas del día a Excel."""
        fecha = self.fecha_edit.date().toPython()

        try:
            ruta = self.report_generator.exportar_ventas_dia(fecha)
            QMessageBox.information(
                self, "Exportación exitosa",
                f"El reporte se guardó en:\n{ruta}"
            )
            # Abrir carpeta de reportes
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
        """Refresca los datos del panel."""
        self._cargar_ventas_hoy()
        self._actualizar_dashboard()
