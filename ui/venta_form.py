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
    QSizePolicy, QSpinBox, QCompleter,
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


class VentaForm(QWidget):
    """
    Panel de registro de venta.
    Emite venta_guardada(Venta) cuando se guarda exitosamente.
    """

    venta_guardada = Signal(object)   # Venta

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = VentaController()
        self._build_ui()
        self._connect_signals()
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

        # Formulario
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

        # Producto (con autocompletado desde inventario)
        self.campo_producto = QLineEdit()
        self.campo_producto.setPlaceholderText("Ej: Casco X-Sport, Aceite 10W-40…")
        self.campo_producto.setFixedHeight(34)
        form.addRow("Producto:", self.campo_producto)

        # Indicador de stock (visible solo cuando se selecciona un producto del inventario)
        self._lbl_stock = QLabel("")
        self._lbl_stock.setVisible(False)
        self._lbl_stock.setStyleSheet(
            "font-size:10px; padding:2px 6px; border-radius:3px;"
        )
        form.addRow("", self._lbl_stock)

        # Configurar QCompleter
        self._completer = QCompleter(self)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setMaxVisibleItems(12)
        self.campo_producto.setCompleter(self._completer)
        self._completer_model = QStringListModel(self)
        self._completer.setModel(self._completer_model)

        # Costo
        self.campo_costo = MoneyLineEdit()
        self.campo_costo.setPlaceholderText("0")
        self.campo_costo.setFixedHeight(34)
        form.addRow("Costo ($):", self.campo_costo)

        # Precio de venta
        self.campo_precio = MoneyLineEdit()
        self.campo_precio.setPlaceholderText("0")
        self.campo_precio.setFixedHeight(34)
        form.addRow("Precio venta ($):", self.campo_precio)

        # Cantidad
        self.campo_cantidad = QSpinBox()
        self.campo_cantidad.setMinimum(1)
        self.campo_cantidad.setMaximum(999)
        self.campo_cantidad.setValue(1)
        self.campo_cantidad.setFixedHeight(34)
        self.campo_cantidad.setPrefix("× ")
        form.addRow("Cantidad:", self.campo_cantidad)

        # Método de pago
        self.campo_metodo = QComboBox()
        self.campo_metodo.addItems(METODOS_PAGO)
        self.campo_metodo.setFixedHeight(34)
        form.addRow("Método de pago:", self.campo_metodo)

        # Sub-tipo de transferencia (oculto por defecto)
        self.lbl_sub_transferencia = QLabel("Tipo transferencia:")
        self.campo_sub_transferencia = QComboBox()
        self.campo_sub_transferencia.addItems(TRANSFERENCIA_SUBTIPOS)
        self.campo_sub_transferencia.setFixedHeight(34)
        form.addRow(self.lbl_sub_transferencia, self.campo_sub_transferencia)
        self.lbl_sub_transferencia.setVisible(False)
        self.campo_sub_transferencia.setVisible(False)

        # Notas
        self.campo_notas = QTextEdit()
        self.campo_notas.setPlaceholderText("Observaciones opcionales…")
        self.campo_notas.setFixedHeight(70)
        self.campo_notas.setTabChangesFocus(True)
        form.addRow("Notas:", self.campo_notas)

        layout.addLayout(form)
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
        self.campo_costo.textChanged.connect(self._actualizar_preview)
        self.campo_precio.textChanged.connect(self._actualizar_preview)
        self.campo_cantidad.valueChanged.connect(self._actualizar_preview)
        self.campo_metodo.currentTextChanged.connect(self._on_metodo_changed)
        self.campo_sub_transferencia.currentTextChanged.connect(self._actualizar_preview)
        self.btn_guardar.clicked.connect(self._on_guardar)

        # Inventario: buscar mientras se escribe y auto-rellenar al seleccionar
        self.campo_producto.textEdited.connect(self._on_producto_editado)
        self._completer.activated.connect(self._on_producto_seleccionado)

    # ------------------------------------------------------------------
    # Autocompletado con inventario
    # ------------------------------------------------------------------

    def _on_producto_editado(self, texto: str) -> None:
        """Actualiza el modelo del completer consultando el inventario."""
        if len(texto) < 2:
            self._completer_model.setStringList([])
            self._lbl_stock.setVisible(False)
            return
        try:
            from database.inventario_repo import buscar_productos_por_nombre
            productos = buscar_productos_por_nombre(texto)
            nombres = [p.producto for p in productos]
            self._completer_model.setStringList(nombres)

            # Si el texto coincide exacto con un producto, auto-rellenar costo
            exacto = next(
                (p for p in productos if p.producto.lower() == texto.lower()), None
            )
            if exacto:
                self._aplicar_producto_inventario(exacto)
        except Exception:
            pass  # Si el inventario no está disponible, seguir sin él

    def _on_producto_seleccionado(self, nombre: str) -> None:
        """Rellena costo y muestra stock cuando el usuario elige del desplegable."""
        try:
            from database.inventario_repo import obtener_producto_por_nombre_exacto
            p = obtener_producto_por_nombre_exacto(nombre)
            if p:
                self._aplicar_producto_inventario(p)
        except Exception:
            pass

    def _aplicar_producto_inventario(self, producto) -> None:
        """Rellena el campo costo y actualiza el indicador de stock."""
        self.campo_costo.set_valor(int(producto.costo_unitario))
        if producto.cantidad > 5:
            self._lbl_stock.setText(f"Stock disponible: {producto.cantidad} uds.")
            self._lbl_stock.setStyleSheet(
                "font-size:10px; padding:2px 6px; border-radius:3px;"
                "color:#15803D; background:#DCFCE7;"
            )
        elif producto.cantidad > 0:
            self._lbl_stock.setText(f"Stock bajo: {producto.cantidad} uds.")
            self._lbl_stock.setStyleSheet(
                "font-size:10px; padding:2px 6px; border-radius:3px;"
                "color:#92400E; background:#FEF3C7;"
            )
        else:
            self._lbl_stock.setText("Sin stock en inventario")
            self._lbl_stock.setStyleSheet(
                "font-size:10px; padding:2px 6px; border-radius:3px;"
                "color:#DC2626; background:#FEE2E2;"
            )
        self._lbl_stock.setVisible(True)

    def actualizar_inventario(self) -> None:
        """Llamar desde fuera cuando el inventario cambia para refrescar el completer."""
        texto = self.campo_producto.text()
        if len(texto) >= 2:
            self._on_producto_editado(texto)

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
        """Recalcula y refresca el panel de resumen en tiempo real."""
        costo = self._parse_int(self.campo_costo.text())
        precio = self._parse_int(self.campo_precio.text())
        metodo = self._metodo_completo()

        data = self._ctrl.calcular_preview(costo, precio, metodo, self.campo_cantidad.value())

        self.lbl_bruta.setText(cop(data["ganancia_bruta"]))
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
        """Valida los campos y guarda la venta."""
        try:
            fecha_q = self.campo_fecha.date()
            fecha = date(fecha_q.year(), fecha_q.month(), fecha_q.day())
            producto = self.campo_producto.text().strip()
            costo = float(self._parse_int(self.campo_costo.text()))
            precio = float(self._parse_int(self.campo_precio.text()))
            metodo = self._metodo_completo()
            notas = self.campo_notas.toPlainText().strip()

            venta = self._ctrl.guardar_nueva_venta(
                fecha=fecha,
                producto=producto,
                costo=costo,
                precio=precio,
                metodo_pago=metodo,
                notas=notas,
                cantidad=self.campo_cantidad.value(),
            )
            self._mostrar_exito(venta)
            self.venta_guardada.emit(venta)
            self._limpiar_form()

        except ValueError as exc:
            QMessageBox.warning(self, "Dato inválido", str(exc))

    def _mostrar_exito(self, venta: Venta) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("Venta registrada")
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            f"<b>{venta.producto}</b> registrada correctamente.<br>"
            f"Ganancia neta: <b>{cop(venta.ganancia_neta)}</b>"
        )
        msg.exec()

    def _limpiar_form(self) -> None:
        """Resetea el formulario para la próxima entrada."""
        self.campo_fecha.setDate(QDate.currentDate())
        self.campo_producto.clear()
        self.campo_costo.clear()
        self.campo_precio.clear()
        self.campo_cantidad.setValue(1)
        self.campo_metodo.setCurrentIndex(0)
        self.campo_sub_transferencia.setCurrentIndex(0)
        self.campo_notas.clear()
        self._lbl_stock.setVisible(False)
        self._actualizar_preview()
        self.campo_producto.setFocus()

    # ------------------------------------------------------------------
    # API pública — prellenar para edición
    # ------------------------------------------------------------------

    def cargar_venta(self, venta: Venta) -> None:
        """
        Precarga los campos con los datos de una venta existente.
        Usado desde la tabla de ventas para editar.
        """
        q = QDate(venta.fecha.year, venta.fecha.month, venta.fecha.day)
        self.campo_fecha.setDate(q)
        self.campo_producto.setText(venta.producto)
        self.campo_costo.set_valor(int(venta.costo))
        self.campo_precio.set_valor(int(venta.precio))
        self.campo_cantidad.setValue(venta.cantidad)

        metodo_base, sub = self._split_metodo(venta.metodo_pago)
        idx = self.campo_metodo.findText(metodo_base)
        if idx >= 0:
            self.campo_metodo.setCurrentIndex(idx)
        if sub:
            idx_sub = self.campo_sub_transferencia.findText(sub)
            if idx_sub >= 0:
                self.campo_sub_transferencia.setCurrentIndex(idx_sub)

        self.campo_notas.setPlainText(venta.notas)

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
