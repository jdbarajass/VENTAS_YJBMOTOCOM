"""
ui/venta_form.py
Formulario de registro de venta con cálculo en tiempo real.
Solo UI — toda la lógica va por VentaController.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit,
    QPushButton, QDateEdit, QFrame, QMessageBox,
    QSpinBox, QCompleter,
)
from PySide6.QtCore import Qt, QDate, QTimer, Signal, QStringListModel
from PySide6.QtGui import QFont

from models.venta import Venta
from controllers.venta_controller import VentaController
from utils.formatters import cop, porcentaje

# Métodos de pago disponibles (orden de ComboBox)
METODOS_PAGO = ["Efectivo", "Bold", "Addi", "Transferencia", "Otro"]

# Sub-tipos de transferencia
TRANSFERENCIA_SUBTIPOS = ["NU", "QR", "NEQUI", "DAVIPLATA"]


def _fmt(valor: int) -> str:
    """Formato de miles colombiano para uso interno en el formulario."""
    return f"$ {valor:,}".replace(",", ".")


class MoneyLineEdit(QLineEdit):
    """
    Campo numérico con separador de miles automático (punto colombiano).
    Acepta solo dígitos; los formatea en tiempo real: "80.000", "1.200.000".
    Usar valor_int() para obtener el número limpio.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._actualizando = False
        self.textChanged.connect(self._formatear)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)

    def keyPressEvent(self, event) -> None:
        allowed = {
            Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Left, Qt.Key_Right,
            Qt.Key_Home, Qt.Key_End, Qt.Key_Tab, Qt.Key_Return, Qt.Key_Enter,
        }
        if event.key() in allowed or event.text().isdigit():
            super().keyPressEvent(event)

    def _formatear(self, texto: str) -> None:
        if self._actualizando:
            return
        digitos = "".join(c for c in texto if c.isdigit())
        if not digitos:
            if texto:
                self._actualizando = True
                self.setText("")
                self._actualizando = False
            return
        formateado = f"{int(digitos):,}".replace(",", ".")
        if formateado == texto:
            return
        # Reposicionar cursor correctamente tras insertar puntos
        pos = self.cursorPosition()
        digitos_antes = sum(1 for c in texto[:pos] if c.isdigit())
        nueva_pos = len(formateado)
        contados = 0
        for i, c in enumerate(formateado):
            if contados == digitos_antes:
                nueva_pos = i
                break
            if c.isdigit():
                contados += 1
        self._actualizando = True
        self.setText(formateado)
        self.setCursorPosition(nueva_pos)
        self._actualizando = False

    def valor_int(self) -> int:
        """Retorna el valor numérico sin puntos de separación."""
        return int("".join(c for c in self.text() if c.isdigit()) or "0")

    def set_valor(self, valor: int) -> None:
        """Establece el valor con formato de miles."""
        self.setText(f"{valor:,}".replace(",", ".") if valor else "")


class _LineaProducto:
    """
    Fila de producto en el carrito de venta.
    Encapsula: campo_producto (con autocompletado), campo_costo, campo_precio,
    campo_cantidad, indicador de stock y boton de quitar.
    """

    def __init__(self, on_change, on_remove) -> None:
        self.widget = QWidget()
        self.widget.setStyleSheet(
            "QWidget { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; }"
        )

        lay = QHBoxLayout(self.widget)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)

        self.campo_producto = QLineEdit()
        self.campo_producto.setPlaceholderText("Buscar producto en inventario...")
        self.campo_producto.setFixedHeight(30)
        self.campo_producto.setStyleSheet(
            "QLineEdit { background:white; border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 8px; } QLineEdit:focus { border:2px solid #3B82F6; }"
        )

        self.campo_costo = MoneyLineEdit()
        self.campo_costo.setPlaceholderText("Costo")
        self.campo_costo.setFixedHeight(30)
        self.campo_costo.setFixedWidth(105)
        self.campo_costo.setStyleSheet(
            "QLineEdit { background:white; border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 6px; } QLineEdit:focus { border:2px solid #3B82F6; }"
        )

        self.campo_precio = MoneyLineEdit()
        self.campo_precio.setPlaceholderText("Precio")
        self.campo_precio.setFixedHeight(30)
        self.campo_precio.setFixedWidth(115)
        self.campo_precio.setStyleSheet(
            "QLineEdit { background:white; border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 6px; } QLineEdit:focus { border:2px solid #3B82F6; }"
        )

        self.campo_cantidad = QSpinBox()
        self.campo_cantidad.setMinimum(1)
        self.campo_cantidad.setMaximum(999)
        self.campo_cantidad.setValue(1)
        self.campo_cantidad.setFixedHeight(30)
        self.campo_cantidad.setFixedWidth(62)
        self.campo_cantidad.setPrefix("x")

        self._lbl_stock = QLabel("")
        self._lbl_stock.setVisible(False)
        self._lbl_stock.setFixedWidth(86)
        self._lbl_stock.setAlignment(Qt.AlignCenter)
        self._lbl_stock.setStyleSheet("font-size:9px; padding:1px 5px; border-radius:3px;")

        btn_del = QPushButton("X")
        btn_del.setFixedSize(26, 26)
        btn_del.setToolTip("Quitar este producto del carrito")
        btn_del.setStyleSheet(
            "QPushButton { background:#FEE2E2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:12px; font-weight:bold; }"
            "QPushButton:hover { background:#FECACA; }"
            "QPushButton:disabled { background:#F3F4F6; color:#D1D5DB; border-color:#E5E7EB; }"
        )
        btn_del.clicked.connect(on_remove)
        self._btn_del = btn_del

        lay.addWidget(self.campo_producto, stretch=3)
        lay.addWidget(self.campo_costo)
        lay.addWidget(self.campo_precio)
        lay.addWidget(self.campo_cantidad)
        lay.addWidget(self._lbl_stock)
        lay.addWidget(btn_del)

        # Autocompletado
        self._completer = QCompleter()
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setMaxVisibleItems(30)
        self._completer_model = QStringListModel()
        self._completer.setModel(self._completer_model)
        self.campo_producto.setCompleter(self._completer)
        self._completer.popup().setStyleSheet(
            "QListView { background:#FFFFFF; color:#1E293B; border:1px solid #BFDBFE;"
            "border-radius:6px; font-size:12px; padding:2px; }"
            "QListView::item { padding:5px 10px; border-radius:4px; }"
            "QListView::item:hover { background:#EFF6FF; }"
            "QListView::item:selected { background:#DBEAFE; font-weight:bold; }"
        )

        # Callbacks
        self._on_change = on_change
        self.campo_producto.textEdited.connect(self._on_texto_editado)
        self._completer.activated.connect(self._on_seleccionado)
        self.campo_producto.editingFinished.connect(self._on_confirmado)
        self.campo_costo.textChanged.connect(on_change)
        self.campo_precio.textChanged.connect(on_change)
        self.campo_cantidad.valueChanged.connect(on_change)

    # -- Autocompletado --

    def _on_texto_editado(self, texto: str) -> None:
        if len(texto) < 2:
            self._completer_model.setStringList([])
            self._lbl_stock.setVisible(False)
            return
        try:
            from database.inventario_repo import (
                buscar_productos_por_nombre,
                obtener_producto_por_codigo_barras,
            )
            # Primero: coincidencia exacta por código de barras
            por_barras = obtener_producto_por_codigo_barras(texto)
            if por_barras:
                self._completer_model.setStringList([por_barras.producto])
                self.campo_producto.blockSignals(True)
                self.campo_producto.setText(por_barras.producto)
                self.campo_producto.blockSignals(False)
                self._aplicar_producto(por_barras)
                return
            # Búsqueda parcial por nombre o código de barras
            prods = buscar_productos_por_nombre(texto)
            self._completer_model.setStringList([p.producto for p in prods])
            exacto = next((p for p in prods if p.producto.lower() == texto.lower()), None)
            if exacto:
                self._aplicar_producto(exacto)
        except Exception:
            pass

    def _on_seleccionado(self, nombre: str) -> None:
        try:
            from database.inventario_repo import obtener_producto_por_nombre_exacto
            p = obtener_producto_por_nombre_exacto(nombre)
            if p:
                self._aplicar_producto(p)
        except Exception:
            pass

    def _on_confirmado(self) -> None:
        texto = self.campo_producto.text().strip()
        if not texto or self._lbl_stock.isVisible():
            return
        try:
            from database.inventario_repo import (
                obtener_producto_por_nombre_exacto,
                obtener_producto_por_codigo_barras,
            )
            p = obtener_producto_por_nombre_exacto(texto) or obtener_producto_por_codigo_barras(texto)
            if p:
                self.campo_producto.setText(p.producto)
                self._aplicar_producto(p)
        except Exception:
            pass

    def _aplicar_producto(self, producto) -> None:
        self.campo_costo.set_valor(int(producto.costo_unitario))
        if producto.cantidad > 5:
            self._lbl_stock.setText(f"Stock: {producto.cantidad}")
            self._lbl_stock.setStyleSheet(
                "font-size:9px; padding:1px 5px; border-radius:3px;"
                "color:#15803D; background:#DCFCE7;"
            )
        elif producto.cantidad > 0:
            self._lbl_stock.setText(f"Bajo: {producto.cantidad}")
            self._lbl_stock.setStyleSheet(
                "font-size:9px; padding:1px 5px; border-radius:3px;"
                "color:#92400E; background:#FEF3C7;"
            )
        else:
            self._lbl_stock.setText("Sin stock")
            self._lbl_stock.setStyleSheet(
                "font-size:9px; padding:1px 5px; border-radius:3px;"
                "color:#DC2626; background:#FEE2E2;"
            )
        self._lbl_stock.setVisible(True)
        self._on_change()

    def stock_actual(self) -> int | None:
        """Retorna el stock actual del producto si está en inventario, o None."""
        texto = self.campo_producto.text().strip()
        if not texto:
            return None
        try:
            from database.inventario_repo import (
                obtener_producto_por_nombre_exacto,
                obtener_producto_por_codigo_barras,
            )
            p = obtener_producto_por_nombre_exacto(texto) or obtener_producto_por_codigo_barras(texto)
            return p.cantidad if p else None
        except Exception:
            return None

    def datos(self) -> dict:
        """Retorna los datos de esta linea como dict."""
        return {
            "producto": self.campo_producto.text().strip(),
            "costo":    float(self.campo_costo.valor_int()),
            "precio":   float(self.campo_precio.valor_int()),
            "cantidad": self.campo_cantidad.value(),
        }

    def limpiar(self) -> None:
        self.campo_producto.clear()
        self.campo_costo.clear()
        self.campo_precio.clear()
        self.campo_cantidad.setValue(1)
        self._lbl_stock.setVisible(False)


class VentaForm(QWidget):
    """
    Panel de registro de venta.
    Emite venta_guardada(Venta) cuando se guarda exitosamente.
    """

    venta_guardada = Signal(object)   # Venta

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = VentaController()
        self._lineas: list[_LineaProducto] = []   # filas de producto del carrito
        self._build_ui()
        self._connect_signals()
        # Primera línea vacía — después de _build_ui para que lbl_bruta y campo_metodo existan
        self._agregar_linea()
        self._actualizar_preview()

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(24)

        root.addWidget(self._panel_formulario(), stretch=3)
        root.addWidget(self._separador_vertical())
        root.addWidget(self._panel_preview(), stretch=2)

    def _panel_formulario(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Título
        titulo = QLabel("Nueva Venta")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        titulo.setFont(font)
        layout.addWidget(titulo)

        # Formulario superior — solo fecha
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Fecha
        self.campo_fecha = QDateEdit()
        self.campo_fecha.setCalendarPopup(True)
        self.campo_fecha.setDate(QDate.currentDate())
        self.campo_fecha.setDisplayFormat("dd/MM/yyyy")
        self.campo_fecha.setFixedHeight(34)
        form.addRow("Fecha:", self.campo_fecha)
        layout.addLayout(form)

        # --- Cabecera de la sección de productos ---
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 4, 0, 2)
        lbl_prods = QLabel("Productos")
        f_hdr = QFont(); f_hdr.setPointSize(11); f_hdr.setBold(True)
        lbl_prods.setFont(f_hdr)

        # Encabezado de columnas
        lbl_cols = QLabel("Producto                                      Costo          Precio        Cant.")
        lbl_cols.setStyleSheet("color:#9CA3AF; font-size:10px;")

        btn_add_linea = QPushButton("+ Producto")
        btn_add_linea.setFixedHeight(28)
        btn_add_linea.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 10px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn_add_linea.clicked.connect(self._on_agregar_linea)
        hdr.addWidget(lbl_prods)
        hdr.addStretch()
        hdr.addWidget(btn_add_linea)
        layout.addLayout(hdr)
        layout.addWidget(lbl_cols)

        # Área scrollable de lineas de productos
        self._lineas_container = QWidget()
        self._lineas_container.setStyleSheet("background:transparent;")
        self._lineas_layout = QVBoxLayout(self._lineas_container)
        self._lineas_layout.setContentsMargins(0, 0, 0, 0)
        self._lineas_layout.setSpacing(4)

        from PySide6.QtWidgets import QScrollArea
        self._scroll_lineas = QScrollArea()
        self._scroll_lineas.setWidget(self._lineas_container)
        self._scroll_lineas.setWidgetResizable(True)
        self._scroll_lineas.setMaximumHeight(200)
        self._scroll_lineas.setFrameShape(QFrame.NoFrame)
        self._scroll_lineas.setStyleSheet("background:transparent;")
        layout.addWidget(self._scroll_lineas)

        # Formulario inferior — método de pago
        form2 = QFormLayout()
        form2.setSpacing(10)
        form2.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form2.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        # Método de pago (con toggle de pago combinado)
        fila_metodo = QHBoxLayout()
        fila_metodo.setSpacing(6)
        fila_metodo.setContentsMargins(0, 0, 0, 0)
        self.campo_metodo = QComboBox()
        self.campo_metodo.addItems(METODOS_PAGO)
        self.campo_metodo.setFixedHeight(34)
        self._btn_combinado = QPushButton("Combinado")
        self._btn_combinado.setCheckable(True)
        self._btn_combinado.setFixedHeight(34)
        self._btn_combinado.setToolTip(
            "Activar cuando el cliente paga con más de un método"
        )
        self._btn_combinado.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 10px; font-size:12px; background:white; color:#374151; }"
            "QPushButton:hover { background:#F3F4F6; }"
            "QPushButton:checked { background:#DBEAFE; color:#1D4ED8;"
            "border-color:#93C5FD; font-weight:bold; }"
        )
        fila_metodo.addWidget(self.campo_metodo)
        fila_metodo.addWidget(self._btn_combinado)
        metodo_widget = QWidget()
        metodo_widget.setLayout(fila_metodo)
        metodo_widget.setFixedHeight(34)
        form2.addRow("Método de pago:", metodo_widget)

        # Sub-tipo de transferencia (oculto por defecto)
        self.lbl_sub_transferencia = QLabel("Tipo transferencia:")
        self.campo_sub_transferencia = QComboBox()
        self.campo_sub_transferencia.addItems(TRANSFERENCIA_SUBTIPOS)
        self.campo_sub_transferencia.setFixedHeight(34)
        form2.addRow(self.lbl_sub_transferencia, self.campo_sub_transferencia)
        self.lbl_sub_transferencia.setVisible(False)
        self.campo_sub_transferencia.setVisible(False)

        # Panel de pagos combinados (oculto hasta activar el toggle)
        self._filas_pago: list[tuple] = []  # (QComboBox_metodo, MoneyLineEdit, QWidget_row, QComboBox_sub)
        self._panel_combinado = self._build_panel_combinado()
        form2.addRow("", self._panel_combinado)
        self._panel_combinado.setVisible(False)

        # Notas
        self.campo_notas = QTextEdit()
        self.campo_notas.setPlaceholderText("Observaciones opcionales…")
        self.campo_notas.setFixedHeight(60)
        self.campo_notas.setTabChangesFocus(True)
        form2.addRow("Notas:", self.campo_notas)

        layout.addLayout(form2)
        layout.addSpacing(8)

        # Botón guardar
        self.btn_guardar = QPushButton("Registrar Venta")
        self.btn_guardar.setFixedHeight(42)
        font_btn = QFont()
        font_btn.setPointSize(11)
        font_btn.setBold(True)
        self.btn_guardar.setFont(font_btn)
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: white; border-radius: 6px; }"
            "QPushButton:hover { background-color: #1D4ED8; }"
            "QPushButton:pressed { background-color: #1E40AF; }"
            "QPushButton:disabled { background-color: #93C5FD; }"
        )
        layout.addWidget(self.btn_guardar)
        layout.addStretch()

        return panel

    def _build_panel_combinado(self) -> QWidget:
        """Panel de pagos combinados con filas dinámicas."""
        w = QWidget()
        w.setStyleSheet(
            "QWidget#panelCombinado { background:#F0F9FF; border:1px solid #BAE6FD;"
            "border-radius:6px; }"
        )
        w.setObjectName("panelCombinado")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(5)

        # Contenedor dinámico de filas
        self._pagos_container = QWidget()
        self._pagos_container.setStyleSheet("background:transparent;")
        self._pagos_layout = QVBoxLayout(self._pagos_container)
        self._pagos_layout.setContentsMargins(0, 0, 0, 0)
        self._pagos_layout.setSpacing(4)
        outer.addWidget(self._pagos_container)

        # Botón agregar fila
        btn_add = QPushButton("+ Agregar método")
        btn_add.setFixedHeight(28)
        btn_add.setStyleSheet(
            "QPushButton { background:#E0F2FE; color:#0369A1; border:1px solid #7DD3FC;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 10px; }"
            "QPushButton:hover { background:#BAE6FD; }"
        )
        btn_add.clicked.connect(self._on_agregar_pago)
        outer.addWidget(btn_add)

        # Indicador de asignación
        self._lbl_pagos_status = QLabel("Asignado: $ 0  /  Total: $ 0")
        self._lbl_pagos_status.setStyleSheet(
            "font-size:11px; color:#374151; background:transparent;"
        )
        outer.addWidget(self._lbl_pagos_status)

        return w

    def _panel_preview(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 0, 0, 0)
        layout.setSpacing(12)

        titulo = QLabel("Resumen")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        titulo.setFont(font)
        layout.addWidget(titulo)

        layout.addSpacing(4)

        # Ganancia bruta
        self.lbl_bruta_titulo = QLabel("Ganancia Bruta")
        self.lbl_bruta_titulo.setStyleSheet("color: #6B7280; font-size: 11px;")
        self.lbl_bruta = QLabel("$ 0")
        self.lbl_bruta.setFont(self._font_valor())
        layout.addWidget(self.lbl_bruta_titulo)
        layout.addWidget(self.lbl_bruta)

        layout.addWidget(self._separador_horizontal())

        # Comisión
        self.lbl_comision_titulo = QLabel("Comisión (0.00 %)")
        self.lbl_comision_titulo.setStyleSheet("color: #6B7280; font-size: 11px;")
        self.lbl_comision = QLabel("$ 0")
        self.lbl_comision.setFont(self._font_valor())
        self.lbl_comision.setStyleSheet("color: #EF4444;")
        layout.addWidget(self.lbl_comision_titulo)
        layout.addWidget(self.lbl_comision)

        layout.addWidget(self._separador_horizontal())

        # Ganancia neta (el más importante)
        self.lbl_neta_titulo = QLabel("Ganancia Neta")
        self.lbl_neta_titulo.setStyleSheet("color: #6B7280; font-size: 11px;")
        self.lbl_neta = QLabel("$ 0")
        font_neta = QFont()
        font_neta.setPointSize(22)
        font_neta.setBold(True)
        self.lbl_neta.setFont(font_neta)
        layout.addWidget(self.lbl_neta_titulo)
        layout.addWidget(self.lbl_neta)

        layout.addSpacing(16)

        # Indicador visual
        self.lbl_indicador = QLabel("")
        self.lbl_indicador.setAlignment(Qt.AlignCenter)
        self.lbl_indicador.setFixedHeight(36)
        self.lbl_indicador.setStyleSheet(
            "border-radius: 8px; font-weight: bold; font-size: 13px;"
        )
        layout.addWidget(self.lbl_indicador)

        layout.addStretch()
        return panel

    # ------------------------------------------------------------------
    # Helpers de UI
    # ------------------------------------------------------------------

    def _separador_vertical(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #E5E7EB;")
        return sep

    def _separador_horizontal(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #E5E7EB;")
        return sep

    @staticmethod
    def _font_valor() -> QFont:
        f = QFont()
        f.setPointSize(15)
        f.setBold(True)
        return f

    # ------------------------------------------------------------------
    # Señales y lógica reactiva
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.campo_metodo.currentTextChanged.connect(self._on_metodo_changed)
        self.campo_sub_transferencia.currentTextChanged.connect(self._actualizar_preview)
        self.btn_guardar.clicked.connect(self._on_guardar)
        self._btn_combinado.toggled.connect(self._on_toggle_combinado)

    # ------------------------------------------------------------------
    # Gestión de lineas del carrito
    # ------------------------------------------------------------------

    def _agregar_linea(self) -> None:
        """Crea una nueva _LineaProducto y la agrega al carrito."""
        linea = _LineaProducto(
            on_change=self._actualizar_preview,
            on_remove=lambda: self._quitar_linea(linea),
        )
        self._lineas.append(linea)
        self._lineas_layout.addWidget(linea.widget)
        self._actualizar_btn_quitar()
        self._actualizar_preview()

    def _on_agregar_linea(self) -> None:
        self._agregar_linea()

    def _quitar_linea(self, linea: "_LineaProducto") -> None:
        """Elimina una linea del carrito (mínimo 1 linea siempre)."""
        if len(self._lineas) <= 1:
            return
        self._lineas.remove(linea)
        linea.widget.setParent(None)
        linea.widget.deleteLater()
        self._actualizar_btn_quitar()
        self._actualizar_preview()

    def _actualizar_btn_quitar(self) -> None:
        """El botón ✕ solo se habilita cuando hay más de una linea."""
        solo = len(self._lineas) <= 1
        for ln in self._lineas:
            ln._btn_del.setEnabled(not solo)

    # ------------------------------------------------------------------
    # Pagos combinados
    # ------------------------------------------------------------------

    def _on_toggle_combinado(self, activo: bool) -> None:
        """Activa/desactiva el modo pago combinado."""
        self.campo_metodo.setEnabled(not activo)
        self.lbl_sub_transferencia.setVisible(False)
        self.campo_sub_transferencia.setVisible(False)
        self._panel_combinado.setVisible(activo)

        if activo:
            # Inicializar con dos filas vacías si no hay ninguna
            if not self._filas_pago:
                self._agregar_fila_pago("Efectivo", 0)
                self._agregar_fila_pago("Bold", 0)
        else:
            # Limpiar filas al desactivar
            self._limpiar_filas_pago()

        self._actualizar_preview()

    def _agregar_fila_pago(self, metodo: str = "Efectivo", monto: int = 0) -> None:
        """Agrega una fila de pago al panel combinado."""
        _combo_style = """
            QComboBox {
                background: white; color: #1E293B;
                border: 1px solid #D1D5DB; border-radius: 4px; padding: 0 8px;
            }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox QAbstractItemView {
                background: white; color: #1E293B;
                selection-background-color: #DBEAFE; selection-color: #1E3A5F;
                border: 1px solid #BFDBFE;
            }
        """

        row_w = QWidget()
        row_w.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(row_w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        # Detectar si el metodo incluye un sub-tipo de transferencia
        metodo_base = metodo.split()[0] if metodo else "Efectivo"
        subtipo = metodo.split()[1] if metodo.startswith("Transferencia ") else TRANSFERENCIA_SUBTIPOS[0]

        combo = QComboBox()
        combo.addItems(METODOS_PAGO)
        combo.setCurrentText(metodo_base)
        combo.setFixedHeight(28)
        combo.setStyleSheet(_combo_style)

        # Sub-combo para tipo de transferencia (visible solo cuando metodo == Transferencia)
        combo_sub = QComboBox()
        combo_sub.addItems(TRANSFERENCIA_SUBTIPOS)
        combo_sub.setCurrentText(subtipo)
        combo_sub.setFixedHeight(28)
        combo_sub.setFixedWidth(80)
        combo_sub.setStyleSheet(_combo_style)
        combo_sub.setVisible(metodo_base == "Transferencia")

        monto_edit = MoneyLineEdit()
        monto_edit.setPlaceholderText("0")
        monto_edit.setFixedHeight(28)
        monto_edit.setStyleSheet(
            "QLineEdit { background:white; color:#1E293B; border:1px solid #D1D5DB;"
            "border-radius:4px; padding:0 6px; }"
            "QLineEdit:focus { border:2px solid #93C5FD; }"
        )
        if monto:
            monto_edit.set_valor(monto)

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(26, 26)
        btn_del.setStyleSheet(
            "QPushButton { background:#FEE2E2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:11px; }"
            "QPushButton:hover { background:#FECACA; }"
        )

        lay.addWidget(combo, stretch=2)
        lay.addWidget(combo_sub)
        lay.addWidget(monto_edit, stretch=2)
        lay.addWidget(btn_del)

        def _on_metodo_fila(texto: str) -> None:
            combo_sub.setVisible(texto == "Transferencia")
            self._actualizar_preview()

        combo.currentTextChanged.connect(_on_metodo_fila)
        combo_sub.currentTextChanged.connect(self._actualizar_preview)
        monto_edit.textChanged.connect(self._actualizar_status_combinado)
        monto_edit.textChanged.connect(self._actualizar_preview)
        btn_del.clicked.connect(lambda _=False, w=row_w: self._eliminar_fila_pago(w))

        self._pagos_layout.addWidget(row_w)
        self._filas_pago.append((combo, monto_edit, row_w, combo_sub))
        self._actualizar_status_combinado()

    def _eliminar_fila_pago(self, row_w: QWidget) -> None:
        """Elimina una fila de pago del panel combinado."""
        self._filas_pago = [t for t in self._filas_pago if t[2] is not row_w]
        row_w.setParent(None)
        row_w.deleteLater()
        self._actualizar_status_combinado()
        self._actualizar_preview()

    def _limpiar_filas_pago(self) -> None:
        """Elimina todas las filas de pago."""
        for t in self._filas_pago:
            t[2].setParent(None)
            t[2].deleteLater()
        self._filas_pago = []

    def _on_agregar_pago(self) -> None:
        self._agregar_fila_pago()

    def _actualizar_status_combinado(self) -> None:
        """Actualiza el indicador Asignado / Total (agrega todas las lineas del carrito)."""
        asignado = sum(t[1].valor_int() for t in self._filas_pago)
        total = sum(
            ln.campo_precio.valor_int() * ln.campo_cantidad.value()
            for ln in self._lineas
        )
        color = "#15803D" if asignado == total and total > 0 else (
            "#DC2626" if asignado > total else "#374151"
        )
        self._lbl_pagos_status.setText(
            f"Asignado: {_fmt(asignado)}  /  Total: {_fmt(total)}"
        )
        self._lbl_pagos_status.setStyleSheet(
            f"font-size:11px; color:{color}; background:transparent;"
        )

    def _get_pagos_combinados(self) -> list | None:
        """Devuelve la lista de pagos si el modo combinado está activo, si no None."""
        if not self._btn_combinado.isChecked():
            return None
        pagos = []
        for t in self._filas_pago:
            combo, monto_edit = t[0], t[1]
            combo_sub = t[3] if len(t) > 3 else None
            monto = monto_edit.valor_int()
            if monto > 0:
                metodo = combo.currentText()
                if metodo == "Transferencia" and combo_sub is not None:
                    metodo = f"Transferencia {combo_sub.currentText()}"
                pagos.append({"metodo": metodo, "monto": float(monto)})
        return pagos if pagos else None

    def actualizar_inventario(self) -> None:
        """Llamar desde fuera cuando el inventario cambia para refrescar los completers."""
        for ln in self._lineas:
            texto = ln.campo_producto.text()
            if len(texto) >= 2:
                ln._on_texto_editado(texto)

    # ------------------------------------------------------------------

    def _on_metodo_changed(self, metodo: str) -> None:
        """Muestra u oculta el sub-combo de transferencia según el método elegido."""
        es_transferencia = (metodo == "Transferencia")
        self.lbl_sub_transferencia.setVisible(es_transferencia)
        self.campo_sub_transferencia.setVisible(es_transferencia)
        self._actualizar_preview()

    def _metodo_completo(self) -> str:
        """Construye el string completo del método, incluyendo sub-tipo si aplica."""
        metodo = self.campo_metodo.currentText()
        if metodo == "Transferencia":
            return f"Transferencia {self.campo_sub_transferencia.currentText()}"
        return metodo

    def _actualizar_preview(self) -> None:
        """Recalcula y refresca el panel de resumen en tiempo real (suma todas las lineas)."""
        total_precio = sum(
            ln.campo_precio.valor_int() * ln.campo_cantidad.value()
            for ln in self._lineas
        )
        total_costo = sum(
            ln.campo_costo.valor_int() * ln.campo_cantidad.value()
            for ln in self._lineas
        )
        metodo = self._metodo_completo()
        pagos = self._get_pagos_combinados()

        data = self._ctrl.calcular_preview(
            total_costo, total_precio, metodo, 1, pagos
        )

        self.lbl_bruta.setText(cop(data["ganancia_bruta"]))
        if data.get("es_combinado"):
            self.lbl_comision_titulo.setText("Comisión (combinada)")
        else:
            self.lbl_comision_titulo.setText(
                f"Comisión ({porcentaje(data['porcentaje'], 2)})"
            )
        self.lbl_comision.setText(
            f"- {cop(data['comision'])}" if data["comision"] > 0 else cop(0)
        )

        neta = data["ganancia_neta"]
        self.lbl_neta.setText(cop(neta))

        if neta > 0:
            self.lbl_neta.setStyleSheet("color: #16A34A;")
            self.lbl_indicador.setText("GANANCIA")
            self.lbl_indicador.setStyleSheet(
                "border-radius: 8px; font-weight: bold; font-size: 13px;"
                "background-color: #DCFCE7; color: #15803D;"
            )
        elif neta < 0:
            self.lbl_neta.setStyleSheet("color: #DC2626;")
            self.lbl_indicador.setText("PÉRDIDA")
            self.lbl_indicador.setStyleSheet(
                "border-radius: 8px; font-weight: bold; font-size: 13px;"
                "background-color: #FEE2E2; color: #DC2626;"
            )
        else:
            self.lbl_neta.setStyleSheet("color: #374151;")
            self.lbl_indicador.setText("")
            self.lbl_indicador.setStyleSheet(
                "border-radius: 8px; font-weight: bold; font-size: 13px;"
            )

    def _on_guardar(self) -> None:
        """Valida el carrito y guarda todas las ventas."""
        try:
            fecha_q = self.campo_fecha.date()
            fecha = date(fecha_q.year(), fecha_q.month(), fecha_q.day())
            metodo = self._metodo_completo()
            notas = self.campo_notas.toPlainText().strip()
            pagos = self._get_pagos_combinados()

            # Recoger lineas del carrito (solo las que tienen producto)
            lineas = [ln.datos() for ln in self._lineas if ln.datos()["producto"]]
            if not lineas:
                raise ValueError("Agrega al menos un producto.")

            # Verificar stock para cada linea
            try:
                from database.inventario_repo import obtener_producto_por_nombre_exacto
                for d in lineas:
                    prod_inv = obtener_producto_por_nombre_exacto(d["producto"])
                    if prod_inv is not None and prod_inv.cantidad < d["cantidad"]:
                        resp = QMessageBox.warning(
                            self, "Stock insuficiente",
                            f"<b>{d['producto']}</b><br>"
                            f"Stock disponible: <b>{prod_inv.cantidad} uds.</b><br>"
                            f"Vas a registrar: <b>{d['cantidad']} uds.</b><br><br>"
                            "¿Continuar de todas formas?",
                            QMessageBox.Yes | QMessageBox.No,
                            QMessageBox.No,
                        )
                        if resp != QMessageBox.Yes:
                            return
            except Exception:
                pass

            # Validar suma de pagos combinados == total carrito
            if pagos is not None:
                total_esperado = sum(int(d["precio"]) * d["cantidad"] for d in lineas)
                total_asignado = sum(int(p["monto"]) for p in pagos)
                if total_asignado != total_esperado:
                    from utils.formatters import cop as _cop
                    raise ValueError(
                        f"La suma de los pagos ({_cop(total_asignado)}) debe ser igual "
                        f"al precio total ({_cop(total_esperado)})."
                    )

            from utils.busy import ocupado
            with ocupado(mensaje="Guardando venta..."):
                ventas = self._ctrl.guardar_carrito(
                    fecha=fecha,
                    lineas=lineas,
                    metodo_pago=metodo,
                    notas=notas,
                    pagos_combinados=pagos,
                )
            self._mostrar_exito(ventas)
            for v in ventas:
                self.venta_guardada.emit(v)
            self._limpiar_form()

        except ValueError as exc:
            QMessageBox.warning(self, "Dato inválido", str(exc))

    def _mostrar_exito(self, ventas: list) -> None:
        total_neta = sum(v.ganancia_neta for v in ventas)
        if len(ventas) == 1:
            texto = (
                f"<b>{ventas[0].producto}</b> registrado correctamente.<br>"
                f"Ganancia neta: <b>{cop(total_neta)}</b>"
            )
        else:
            prods = ", ".join(v.producto for v in ventas[:3])
            if len(ventas) > 3:
                prods += f" y {len(ventas) - 3} más"
            texto = (
                f"<b>{len(ventas)} productos</b> registrados: {prods}.<br>"
                f"Ganancia neta total: <b>{cop(total_neta)}</b>"
            )
        msg = QMessageBox(self)
        msg.setWindowTitle("Venta registrada")
        msg.setIcon(QMessageBox.Information)
        msg.setText(texto)
        btn_recibo = msg.addButton("Imprimir recibo", QMessageBox.AcceptRole)
        msg.addButton("Cerrar", QMessageBox.RejectRole)
        msg.exec()
        if msg.clickedButton() == btn_recibo:
            try:
                from services.recibo_generator import generar_recibo
                from utils.pdf_utils import abrir_pdf
                for v in ventas:
                    path = generar_recibo(v)
                    abrir_pdf(path)
            except Exception as exc:
                QMessageBox.warning(self, "Error al generar recibo",
                                    f"No se pudo generar el PDF:\n{exc}")

    def _limpiar_form(self) -> None:
        """Resetea el formulario para la próxima entrada."""
        self.campo_fecha.setDate(QDate.currentDate())
        self.campo_metodo.setCurrentIndex(0)
        self.campo_metodo.setEnabled(True)
        self.lbl_sub_transferencia.setVisible(False)
        self.campo_sub_transferencia.setCurrentIndex(0)
        self.campo_sub_transferencia.setVisible(False)
        self.campo_notas.clear()
        # Resetear modo combinado
        self._btn_combinado.setChecked(False)
        self._limpiar_filas_pago()
        self._panel_combinado.setVisible(False)
        # Reemplazar todas las lineas por una sola vacía
        for ln in self._lineas:
            ln.widget.setParent(None)
            ln.widget.deleteLater()
        self._lineas.clear()
        self._agregar_linea()
        self._actualizar_preview()
        if self._lineas:
            self._lineas[0].campo_producto.setFocus()

    # ------------------------------------------------------------------
    # API pública — prellenar para edición
    # ------------------------------------------------------------------

    # cargar_venta eliminado: la edición de ventas existentes se hace
    # exclusivamente desde EditVentaDialog (ventas_dia_panel.py).

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_int(texto: str) -> int:
        """Convierte texto con o sin separadores de miles a entero."""
        try:
            limpio = "".join(c for c in texto if c.isdigit())
            return int(limpio) if limpio else 0
        except ValueError:
            return 0

    @staticmethod
    def _split_metodo(metodo_pago: str):
        """
        Descompone "Transferencia NEQUI" en ("Transferencia", "NEQUI").
        Retorna (metodo_pago, "") para métodos sin sub-tipo.
        """
        if metodo_pago.startswith("Transferencia "):
            sub = metodo_pago[len("Transferencia "):]
            return "Transferencia", sub
        return metodo_pago, ""
