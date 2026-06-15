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
    QSpinBox, QCompleter, QScrollArea, QCheckBox,
)
from PySide6.QtCore import Qt, QDate, QTimer, Signal, QStringListModel
from PySide6.QtGui import QFont

import re as _re_vf

from models.venta import Venta


class _NoScrollSpinBox(QSpinBox):
    """QSpinBox que ignora el scroll del mouse para no cambiar el valor
    accidentalmente al hacer scroll en la ventana."""
    def wheelEvent(self, event):
        event.ignore()
from controllers.venta_controller import VentaController
from utils.formatters import cop, porcentaje

def _get_combo_style(radius: int = 5, padding: str = "0 10px",
                     font_size: int = 12, dropdown_width: int = 20) -> str:
    """Retorna hoja de estilo completa para QComboBox según el tema activo."""
    from ui.styles import es_modo_oscuro
    if es_modo_oscuro():
        bg, fg, bdr          = "#1E293B", "#F1F5F9", "#475569"
        popup_bdr, sel_bg, sel_fg = "#334155", "#1E3A5F", "#93C5FD"
    else:
        bg, fg, bdr          = "#FFFFFF", "#111827", "#D1D5DB"
        popup_bdr, sel_bg, sel_fg = "#E5E7EB", "#EFF6FF", "#1D4ED8"
    return (
        f"QComboBox {{ border-radius:{radius}px; padding:{padding}; "
        f"font-size:{font_size}px; background:{bg}; color:{fg}; "
        f"border:1px solid {bdr}; }}"
        "QComboBox:focus { border:2px solid #3B82F6; }"
        f"QComboBox::drop-down {{ border:none; width:{dropdown_width}px; }}"
        f"QComboBox QAbstractItemView {{ background:{bg}; color:{fg}; "
        f"border:1px solid {popup_bdr}; border-radius:6px; padding:2px; "
        f"selection-background-color:{sel_bg}; selection-color:{sel_fg}; "
        f"outline:none; }}"
        f"QComboBox QAbstractItemView::item {{ padding:6px 10px; border-radius:4px; color:{fg}; }}"
    )


def _aplicar_estilo_combo(combo: "QComboBox", placeholder: bool = False) -> None:
    """Aplica stylesheet al combo y fuerza colores del popup via QPalette.

    El popup de QComboBox es una ventana top-level, por lo que los selectores
    descendientes del widget-stylesheet (QComboBox QAbstractItemView) no le
    aplican. La única forma fiable de controlar el color de los ítems es
    seteando directamente la QPalette del view.
    """
    from ui.styles import es_modo_oscuro
    from PySide6.QtGui import QPalette, QColor as _QColor
    combo.setStyleSheet(
        _get_combo_style() + ("QComboBox { color: #9CA3AF; }" if placeholder else "")
    )
    dark = es_modo_oscuro()
    fg   = "#F1F5F9" if dark else "#111827"
    bg   = "#1E293B" if dark else "#FFFFFF"
    sel  = "#1E3A5F" if dark else "#EFF6FF"
    sfg  = "#93C5FD" if dark else "#1D4ED8"
    view = combo.view()
    pal = view.palette()
    for grp in (QPalette.ColorGroup.All,):
        pal.setColor(grp, QPalette.ColorRole.Text,            _QColor(fg))
        pal.setColor(grp, QPalette.ColorRole.WindowText,      _QColor(fg))
        pal.setColor(grp, QPalette.ColorRole.Base,            _QColor(bg))
        pal.setColor(grp, QPalette.ColorRole.Window,          _QColor(bg))
        pal.setColor(grp, QPalette.ColorRole.Highlight,       _QColor(sel))
        pal.setColor(grp, QPalette.ColorRole.HighlightedText, _QColor(sfg))
    view.setPalette(pal)

# Métodos de pago disponibles (orden de ComboBox)
METODOS_PAGO = ["Efectivo", "Addi", "Transferencia", "Otro"]

# Texto del placeholder del combo de método de pago (no es un método real)
_PLACEHOLDER_METODO = "— Selecciona método —"

_TALLAS = ["XS", "S", "M", "L", "XL", "2XL"]
_PAT_TALLA_FORM = _re_vf.compile(r"-T:(\w+)$")

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

        # Layout principal: 2 filas dentro del widget
        root = QVBoxLayout(self.widget)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(4)

        # ── Fila 1: nombre (ancho completo) + talla + botón X ────────────
        fila1 = QHBoxLayout()
        fila1.setSpacing(6)

        self.campo_producto = QLineEdit()
        self.campo_producto.setPlaceholderText("Buscar producto en inventario...")
        self.campo_producto.setFixedHeight(32)
        self.campo_producto.setStyleSheet(
            "QLineEdit { border-radius:5px; font-size:12px; padding:0 10px; }"
            "QLineEdit:focus { border:2px solid #3B82F6; }"
        )

        self._combo_talla = QComboBox()
        self._combo_talla.addItems(["—"] + _TALLAS)
        self._combo_talla.setFixedHeight(32)
        self._combo_talla.setFixedWidth(68)
        self._combo_talla.setVisible(False)
        self._combo_talla.setToolTip("Talla del producto")
        self._combo_talla.setStyleSheet(
            _get_combo_style(radius=5, padding="0 4px", font_size=11, dropdown_width=16)
        )

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(28, 28)
        btn_del.setToolTip("Quitar este producto del carrito")
        btn_del.setStyleSheet(
            "QPushButton { background:#FEE2E2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#FECACA; }"
            "QPushButton:disabled { background:#F3F4F6; color:#D1D5DB; border-color:#E5E7EB; }"
        )
        btn_del.clicked.connect(on_remove)
        self._btn_del = btn_del

        fila1.addWidget(self.campo_producto, stretch=1)
        fila1.addWidget(self._combo_talla)
        fila1.addWidget(btn_del)

        # ── Fila 2: costo + precio + cantidad + badge stock ──────────────
        fila2 = QHBoxLayout()
        fila2.setSpacing(6)

        _campo_style = (
            "QLineEdit { border-radius:5px; font-size:11px; padding:0 6px; }"
            "QLineEdit:focus { border:2px solid #3B82F6; }"
        )

        self.campo_costo = MoneyLineEdit()
        self.campo_costo.setPlaceholderText("Costo")
        self.campo_costo.setFixedHeight(28)
        self.campo_costo.setFixedWidth(115)
        self.campo_costo.setStyleSheet(_campo_style)

        self.campo_precio = MoneyLineEdit()
        self.campo_precio.setPlaceholderText("Precio venta")
        self.campo_precio.setFixedHeight(28)
        self.campo_precio.setFixedWidth(130)
        self.campo_precio.setStyleSheet(_campo_style)

        self.campo_cantidad = _NoScrollSpinBox()
        self.campo_cantidad.setMinimum(1)
        self.campo_cantidad.setMaximum(999)
        self.campo_cantidad.setValue(1)
        self.campo_cantidad.setFixedHeight(28)
        self.campo_cantidad.setFixedWidth(66)
        self.campo_cantidad.setPrefix("x")

        self._lbl_stock = QLabel("")
        self._lbl_stock.setVisible(False)
        self._lbl_stock.setFixedWidth(90)
        self._lbl_stock.setAlignment(Qt.AlignCenter)
        self._lbl_stock.setStyleSheet("font-size:9px; padding:1px 5px; border-radius:3px;")

        # Checkbox ¿Dcto? — habilita campos de descuento por producto
        self._chk_dcto = QCheckBox("✂ ¿Dcto?")
        self._chk_dcto.setToolTip(
            "Activa si le dijiste al cliente un precio diferente al real.\n"
            "Ingresa el precio que le anunciaste y el sistema calcula el ahorro."
        )
        self._chk_dcto.setStyleSheet(
            "QCheckBox { font-size:10px; color:#9CA3AF; background:transparent; padding:0; }"
            "QCheckBox:checked { color:#D97706; font-weight:bold; }"
            "QCheckBox::indicator { width:13px; height:13px; }"
        )

        fila2.addWidget(self.campo_costo)
        fila2.addWidget(self.campo_precio)
        fila2.addWidget(self.campo_cantidad)
        fila2.addWidget(self._lbl_stock)
        fila2.addStretch()
        fila2.addWidget(self._chk_dcto)

        # ── Fila 3: campos de descuento (ocultos hasta marcar checkbox) ───
        self._fila_dcto_widget = QWidget()
        self._fila_dcto_widget.setVisible(False)
        self._fila_dcto_widget.setStyleSheet("background:transparent;")
        fila3 = QHBoxLayout(self._fila_dcto_widget)
        fila3.setContentsMargins(0, 2, 0, 0)
        fila3.setSpacing(6)

        lbl_ofertado = QLabel("Precio al cliente:")
        lbl_ofertado.setStyleSheet(
            "font-size:10px; color:#92400E; background:transparent; padding:0;"
        )

        self._campo_ofertado = MoneyLineEdit()
        self._campo_ofertado.setPlaceholderText("Precio que le dijiste")
        self._campo_ofertado.setFixedHeight(26)
        self._campo_ofertado.setFixedWidth(140)
        self._campo_ofertado.setStyleSheet(
            "QLineEdit { border-radius:4px; font-size:11px; padding:0 6px;"
            " border:1px solid #FDE68A; background:#FFFBEB; }"
            "QLineEdit:focus { border:2px solid #F59E0B; }"
        )

        self._lbl_ahorro = QLabel("—")
        self._lbl_ahorro.setStyleSheet(
            "font-size:10px; font-weight:bold; color:#D97706; background:transparent;"
        )
        self._lbl_ahorro.setMinimumWidth(110)

        fila3.addSpacing(4)
        fila3.addWidget(lbl_ofertado)
        fila3.addWidget(self._campo_ofertado)
        fila3.addWidget(self._lbl_ahorro)
        fila3.addStretch()

        root.addLayout(fila1)
        root.addLayout(fila2)
        root.addWidget(self._fila_dcto_widget)

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

        self._sku = ""

        # Callbacks
        self._on_change = on_change
        self.campo_producto.textEdited.connect(self._on_texto_editado)
        self._completer.activated.connect(self._on_seleccionado)
        self.campo_producto.editingFinished.connect(self._on_confirmado)
        self.campo_costo.textChanged.connect(on_change)
        self.campo_precio.textChanged.connect(on_change)
        self.campo_precio.textChanged.connect(self._recalcular_ahorro)
        self.campo_cantidad.valueChanged.connect(on_change)
        self._combo_talla.currentTextChanged.connect(self._on_talla_cambiada)
        self._chk_dcto.toggled.connect(self._on_toggle_dcto)
        self._campo_ofertado.textChanged.connect(self._recalcular_ahorro)
        self._campo_ofertado.textChanged.connect(on_change)

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

    def _on_talla_cambiada(self, nueva_talla: str) -> None:
        if nueva_talla == "—":
            return
        nombre = self.campo_producto.text()
        # Reemplazar -T:XX con la nueva talla, o agregar si no existe
        if _PAT_TALLA_FORM.search(nombre):
            nuevo_nombre = _PAT_TALLA_FORM.sub(f"-T:{nueva_talla}", nombre)
        else:
            return  # sin patrón -T:, no modificar
        if nuevo_nombre == nombre:
            return
        self.campo_producto.blockSignals(True)
        self.campo_producto.setText(nuevo_nombre)
        self.campo_producto.blockSignals(False)
        # Buscar el producto con el nuevo nombre y actualizar costo/stock
        try:
            from database.inventario_repo import obtener_producto_por_nombre_exacto
            p = obtener_producto_por_nombre_exacto(nuevo_nombre)
            if p:
                self.campo_costo.set_valor(int(p.costo_unitario))
                # Actualizar stock sin llamar a _aplicar_producto completo
                if p.cantidad > 5:
                    self._lbl_stock.setText(f"Stock: {p.cantidad}")
                    self._lbl_stock.setStyleSheet(
                        "font-size:9px; padding:1px 5px; border-radius:3px;"
                        "color:#15803D; background:#DCFCE7;"
                    )
                elif p.cantidad > 0:
                    self._lbl_stock.setText(f"Bajo: {p.cantidad}")
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
        except Exception:
            pass
        self._on_change()

    def _aplicar_producto(self, producto) -> None:
        # Mostrar/preseleccionar talla si el nombre tiene -T:XX
        m = _PAT_TALLA_FORM.search(producto.producto or "")
        if m:
            talla = m.group(1).upper()
            self._combo_talla.blockSignals(True)
            idx = self._combo_talla.findText(talla)
            self._combo_talla.setCurrentIndex(idx if idx >= 0 else 0)
            self._combo_talla.blockSignals(False)
            self._combo_talla.setVisible(True)
        else:
            self._combo_talla.setVisible(False)
        self._sku = (
            getattr(producto, "codigo_barras", "") or
            getattr(producto, "serial", "") or ""
        ).strip()
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

    def _on_toggle_dcto(self, activo: bool) -> None:
        self._fila_dcto_widget.setVisible(activo)
        if not activo:
            self._campo_ofertado.clear()
            self._lbl_ahorro.setText("—")
            self._lbl_ahorro.setStyleSheet(
                "font-size:10px; font-weight:bold; color:#D97706; background:transparent;"
            )
        self._on_change()

    def _recalcular_ahorro(self) -> None:
        if not self._chk_dcto.isChecked():
            return
        from utils.formatters import cop as _cop
        ofertado = self._campo_ofertado.valor_int()
        real     = self.campo_precio.valor_int()
        if ofertado > 0 and real > 0 and ofertado > real:
            ahorro = ofertado - real
            self._lbl_ahorro.setText(f"Ahorro: {_cop(ahorro)}")
            self._lbl_ahorro.setStyleSheet(
                "font-size:10px; font-weight:bold; color:#16A34A; background:transparent;"
            )
        elif ofertado > 0 and real > 0 and ofertado <= real:
            self._lbl_ahorro.setText("⚠ Debe ser > precio real")
            self._lbl_ahorro.setStyleSheet(
                "font-size:10px; color:#DC2626; background:transparent;"
            )
        else:
            self._lbl_ahorro.setText("—")
            self._lbl_ahorro.setStyleSheet(
                "font-size:10px; font-weight:bold; color:#D97706; background:transparent;"
            )

    def datos(self) -> dict:
        """Retorna los datos de esta linea como dict."""
        ofertado = 0.0
        if self._chk_dcto.isChecked():
            v = self._campo_ofertado.valor_int()
            if v > self.campo_precio.valor_int() > 0:
                ofertado = float(v)
        return {
            "producto":        self.campo_producto.text().strip(),
            "costo":           float(self.campo_costo.valor_int()),
            "precio":          float(self.campo_precio.valor_int()),
            "cantidad":        self.campo_cantidad.value(),
            "sku":             self._sku,
            "precio_ofertado": ofertado,
        }

    def limpiar(self) -> None:
        self.campo_producto.clear()
        self.campo_costo.clear()
        self.campo_precio.clear()
        self.campo_cantidad.setValue(1)
        self._lbl_stock.setVisible(False)
        self._combo_talla.setCurrentIndex(0)
        self._combo_talla.setVisible(False)
        self._sku = ""
        self._chk_dcto.setChecked(False)
        self._campo_ofertado.clear()
        self._fila_dcto_widget.setVisible(False)
        self._lbl_ahorro.setText("—")


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
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Panel izquierdo (formulario) dentro de un scroll para manejar muchos productos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setWidget(self._panel_formulario())

        # Panel derecho (preview) con márgenes propios
        preview_wrapper = QWidget()
        preview_wrapper.setStyleSheet("background: transparent;")
        pw_lay = QVBoxLayout(preview_wrapper)
        pw_lay.setContentsMargins(12, 24, 28, 24)
        pw_lay.addWidget(self._panel_preview())

        root.addWidget(scroll, stretch=3)
        root.addWidget(self._separador_vertical())
        root.addWidget(preview_wrapper, stretch=2)

    def _panel_formulario(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 16, 24)
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

        # Vendedor (obligatorio)
        _PLACEHOLDER_VENDEDOR = "— Selecciona vendedor —"
        self._placeholder_vendedor = _PLACEHOLDER_VENDEDOR
        self.campo_vendedor = QComboBox()
        self.campo_vendedor.setFixedHeight(34)
        self._poblar_vendedores()
        _aplicar_estilo_combo(self.campo_vendedor, placeholder=True)
        form.addRow("Vendedor*:", self.campo_vendedor)

        layout.addLayout(form)

        # --- Cabecera de la sección de productos ---
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 4, 0, 2)
        lbl_prods = QLabel("Productos")
        f_hdr = QFont(); f_hdr.setPointSize(11); f_hdr.setBold(True)
        lbl_prods.setFont(f_hdr)

        # Encabezado de columnas
        lbl_cols = QLabel("Nombre del producto / Talla                    Costo          Precio venta   Cant.")
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

        # --- Barra de escaneo de código de barras ---
        scan_frame = QFrame()
        scan_frame.setStyleSheet(
            "QFrame { background:#F0F9FF; border:1px solid #BAE6FD; border-radius:6px; }"
        )
        scan_lay = QHBoxLayout(scan_frame)
        scan_lay.setContentsMargins(10, 6, 10, 6)
        scan_lay.setSpacing(8)

        lbl_scan = QLabel("📷")
        lbl_scan.setStyleSheet("font-size:18px; background:transparent;")
        scan_lay.addWidget(lbl_scan)

        self._campo_scan = QLineEdit()
        self._campo_scan.setPlaceholderText("Escanea un código de barras o escríbelo y presiona Enter...")
        self._campo_scan.setFixedHeight(30)
        self._campo_scan.setStyleSheet(
            "QLineEdit { border:1px solid #7DD3FC; border-radius:5px; padding:0 8px; font-size:11px; }"
            "QLineEdit:focus { border:2px solid #0284C7; }"
        )
        self._campo_scan.returnPressed.connect(self._on_scan_codigo)
        scan_lay.addWidget(self._campo_scan, stretch=1)

        self._lbl_scan_status = QLabel("")
        self._lbl_scan_status.setFixedWidth(200)
        self._lbl_scan_status.setStyleSheet("font-size:10px; color:#0369A1; background:transparent;")
        scan_lay.addWidget(self._lbl_scan_status)

        layout.addWidget(scan_frame)

        # Contenedor de líneas de productos (sin scroll propio — el panel completo scrollea)
        self._lineas_container = QWidget()
        self._lineas_container.setStyleSheet("background:transparent;")
        self._lineas_layout = QVBoxLayout(self._lineas_container)
        self._lineas_layout.setContentsMargins(0, 0, 0, 0)
        self._lineas_layout.setSpacing(4)
        layout.addWidget(self._lineas_container)

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
        self.campo_metodo.addItem(_PLACEHOLDER_METODO)
        self.campo_metodo.addItems(METODOS_PAGO)
        self.campo_metodo.setCurrentIndex(0)
        self.campo_metodo.setFixedHeight(34)
        _aplicar_estilo_combo(self.campo_metodo, placeholder=True)
        self._btn_combinado = QPushButton("Combinado")
        self._btn_combinado.setCheckable(True)
        self._btn_combinado.setFixedHeight(34)
        self._btn_combinado.setToolTip(
            "Activar cuando el cliente paga con más de un método"
        )
        self._btn_combinado.setStyleSheet(
            "QPushButton { border-radius:5px; padding:0 10px; font-size:12px; }"
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
        self.campo_sub_transferencia.setStyleSheet(_get_combo_style())
        form2.addRow(self.lbl_sub_transferencia, self.campo_sub_transferencia)
        self.lbl_sub_transferencia.setVisible(False)
        self.campo_sub_transferencia.setVisible(False)

        # Panel de pagos combinados (oculto hasta activar el toggle)
        self._filas_pago: list[tuple] = []  # (QComboBox_metodo, MoneyLineEdit, QWidget_row, QComboBox_sub)
        self._panel_combinado = self._build_panel_combinado()
        form2.addRow("", self._panel_combinado)
        self._panel_combinado.setVisible(False)

        # Observaciones
        self.campo_notas = QTextEdit()
        self.campo_notas.setPlaceholderText("Observaciones opcionales (aparecen en el comprobante)…")
        self.campo_notas.setFixedHeight(55)
        self.campo_notas.setTabChangesFocus(True)
        form2.addRow("Observaciones:", self.campo_notas)

        layout.addLayout(form2)
        layout.addSpacing(4)

        # ── Sección descuento (oculta — reemplazada por ¿Dcto? por producto) ──
        _sec_dcto = self._build_descuento_section()
        _sec_dcto.setVisible(False)
        layout.addWidget(_sec_dcto)

        # ── Sección datos del cliente ─────────────────────────────────────
        layout.addWidget(self._build_cliente_section())

        layout.addSpacing(8)

        # Fila de botones: Limpiar + Registrar Venta
        _fila_btns = QHBoxLayout()
        _fila_btns.setSpacing(10)

        self.btn_limpiar = QPushButton("Limpiar")
        self.btn_limpiar.setFixedHeight(42)
        self.btn_limpiar.setFixedWidth(110)
        self.btn_limpiar.setCursor(Qt.PointingHandCursor)
        font_btn2 = QFont()
        font_btn2.setPointSize(11)
        font_btn2.setBold(True)
        self.btn_limpiar.setFont(font_btn2)
        self.btn_limpiar.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #374151;"
            "border: 1px solid #CBD5E1; border-radius: 6px; }"
            "QPushButton:hover { background-color: #E2E8F0; }"
            "QPushButton:pressed { background-color: #CBD5E1; }"
        )
        _fila_btns.addWidget(self.btn_limpiar)

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
        _fila_btns.addWidget(self.btn_guardar, stretch=1)

        layout.addLayout(_fila_btns)
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

    def _build_descuento_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background:#FFFBEB; border:1px solid #FDE68A; border-radius:6px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        self._chk_descuento = QCheckBox("¿Hay descuento en esta venta?")
        self._chk_descuento.setStyleSheet(
            "QCheckBox { font-size:12px; font-weight:bold; background:transparent; border:none; }"
        )
        lay.addWidget(self._chk_descuento)

        self._frame_desc_campos = QWidget()
        self._frame_desc_campos.setStyleSheet("background:transparent;")
        self._frame_desc_campos.setVisible(False)
        fc_lay = QHBoxLayout(self._frame_desc_campos)
        fc_lay.setContentsMargins(0, 0, 0, 0)
        fc_lay.setSpacing(8)

        lbl = QLabel("Descuento (COP):")
        lbl.setStyleSheet("font-size:11px; background:transparent;")

        self._campo_descuento = MoneyLineEdit()
        self._campo_descuento.setPlaceholderText("0")
        self._campo_descuento.setFixedHeight(30)
        self._campo_descuento.setFixedWidth(140)
        self._campo_descuento.setStyleSheet(
            "QLineEdit { border-radius:5px; font-size:11px; padding:0 6px; }"
            "QLineEdit:focus { border:2px solid #3B82F6; }"
        )

        self._lbl_desc_pct = QLabel("")
        self._lbl_desc_pct.setStyleSheet(
            "font-size:12px; font-weight:bold; color:#B45309; background:transparent;"
        )

        fc_lay.addWidget(lbl)
        fc_lay.addWidget(self._campo_descuento)
        fc_lay.addWidget(self._lbl_desc_pct)
        fc_lay.addStretch()
        lay.addWidget(self._frame_desc_campos)
        return frame

    def _build_cliente_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background:#F0F9FF; border:1px solid #BAE6FD; border-radius:6px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)

        self._chk_cliente = QCheckBox("¿El cliente va a dejar sus datos?")
        self._chk_cliente.setStyleSheet(
            "QCheckBox { font-size:12px; font-weight:bold; background:transparent; border:none; }"
        )
        lay.addWidget(self._chk_cliente)

        self._frame_cliente_campos = QWidget()
        self._frame_cliente_campos.setStyleSheet("background:transparent;")
        self._frame_cliente_campos.setVisible(False)

        fc_form = QFormLayout(self._frame_cliente_campos)
        fc_form.setSpacing(6)
        fc_form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        fc_form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        _ls = (
            "QLineEdit { border-radius:5px; font-size:11px; padding:0 8px; }"
            "QLineEdit:focus { border:2px solid #3B82F6; }"
        )

        self._campo_cli_nombre = QLineEdit()
        self._campo_cli_nombre.setPlaceholderText("Nombre completo")
        self._campo_cli_nombre.setFixedHeight(30)
        self._campo_cli_nombre.setStyleSheet(_ls)

        self._campo_cli_cedula = QLineEdit()
        self._campo_cli_cedula.setPlaceholderText("Número de cédula")
        self._campo_cli_cedula.setFixedHeight(30)
        self._campo_cli_cedula.setStyleSheet(_ls)

        self._campo_cli_tel = QLineEdit()
        self._campo_cli_tel.setPlaceholderText("Teléfono / Celular")
        self._campo_cli_tel.setFixedHeight(30)
        self._campo_cli_tel.setStyleSheet(_ls)

        fc_form.addRow("Nombre:", self._campo_cli_nombre)
        fc_form.addRow("Cédula:", self._campo_cli_cedula)
        fc_form.addRow("Teléfono:", self._campo_cli_tel)

        lay.addWidget(self._frame_cliente_campos)
        return frame

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

        # Total de venta
        self._lbl_total_titulo = QLabel("Total de venta")
        self._lbl_total_titulo.setStyleSheet("color: #6B7280; font-size: 11px;")
        self._lbl_total_venta = QLabel("$ 0")
        self._lbl_total_venta.setFont(self._font_valor())
        self._lbl_total_venta.setStyleSheet("color: #1E293B;")
        layout.addWidget(self._lbl_total_titulo)
        layout.addWidget(self._lbl_total_venta)

        # Ahorro del cliente (visible solo cuando hay descuentos por producto)
        self._lbl_ahorro_titulo = QLabel("Ahorro del cliente")
        self._lbl_ahorro_titulo.setStyleSheet("color:#D97706; font-size:10px;")
        self._lbl_ahorro_titulo.setVisible(False)
        self._lbl_ahorro_total = QLabel("")
        self._lbl_ahorro_total.setStyleSheet(
            "color:#D97706; font-size:13px; font-weight:bold;"
        )
        self._lbl_ahorro_total.setVisible(False)
        layout.addWidget(self._lbl_ahorro_titulo)
        layout.addWidget(self._lbl_ahorro_total)

        layout.addWidget(self._separador_horizontal())

        # Medios de pago
        self._lbl_medios_titulo = QLabel("Medio de pago")
        self._lbl_medios_titulo.setStyleSheet("color: #6B7280; font-size: 11px;")
        layout.addWidget(self._lbl_medios_titulo)
        self._frame_medios = QWidget()
        self._frame_medios.setStyleSheet("background:transparent;")
        self._lay_medios = QVBoxLayout(self._frame_medios)
        self._lay_medios.setContentsMargins(0, 0, 0, 0)
        self._lay_medios.setSpacing(2)
        layout.addWidget(self._frame_medios)

        layout.addWidget(self._separador_horizontal())

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
        self.btn_limpiar.clicked.connect(self._limpiar_form)
        self._btn_combinado.toggled.connect(self._on_toggle_combinado)
        self.campo_vendedor.currentIndexChanged.connect(self._on_vendedor_changed)
        self._chk_descuento.toggled.connect(self._on_toggle_descuento)
        self._campo_descuento.textChanged.connect(self._actualizar_preview)
        self._campo_descuento.textChanged.connect(self._actualizar_status_combinado)
        self._chk_cliente.toggled.connect(
            lambda activo: self._frame_cliente_campos.setVisible(activo)
        )

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
                self._agregar_fila_pago("Transferencia", 0)
        else:
            # Limpiar filas al desactivar
            self._limpiar_filas_pago()

        self._actualizar_preview()

    def _on_vendedor_changed(self, idx: int) -> None:
        _aplicar_estilo_combo(self.campo_vendedor, placeholder=(idx == 0))

    def _on_toggle_descuento(self, activo: bool) -> None:
        self._frame_desc_campos.setVisible(activo)
        if not activo:
            self._campo_descuento.setText("")
        self._actualizar_preview()

    def _agregar_fila_pago(self, metodo: str = "Efectivo", monto: int = 0) -> None:
        """Agrega una fila de pago al panel combinado."""
        _combo_style = _get_combo_style(radius=4, padding="0 8px", font_size=12, dropdown_width=18)

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
            "QLineEdit { border-radius:4px; padding:0 6px; }"
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

    def _poblar_vendedores(self) -> None:
        """Llena el combo de vendedores desde la BD."""
        seleccionado = self.campo_vendedor.currentText()
        self.campo_vendedor.blockSignals(True)
        self.campo_vendedor.clear()
        self.campo_vendedor.addItem(self._placeholder_vendedor)
        try:
            from database.usuarios_repo import obtener_todos_usuarios
            for u in obtener_todos_usuarios():
                self.campo_vendedor.addItem(u.nombre)
        except Exception:
            pass
        idx = self.campo_vendedor.findText(seleccionado)
        self.campo_vendedor.setCurrentIndex(max(0, idx))
        self.campo_vendedor.blockSignals(False)

    def recargar_vendedores(self) -> None:
        """Slot público: recarga el combo cuando cambia la lista de usuarios."""
        self._poblar_vendedores()
        es_ph = self.campo_vendedor.currentIndex() == 0
        _aplicar_estilo_combo(self.campo_vendedor, placeholder=es_ph)

    def actualizar_inventario(self) -> None:
        """Llamar desde fuera cuando el inventario cambia para refrescar los completers."""
        for ln in self._lineas:
            texto = ln.campo_producto.text()
            if len(texto) >= 2:
                ln._on_texto_editado(texto)

    # ------------------------------------------------------------------

    def _on_metodo_changed(self, metodo: str) -> None:
        """Muestra u oculta el sub-combo de transferencia según el método elegido."""
        es_placeholder = (metodo == _PLACEHOLDER_METODO)
        es_transferencia = (metodo == "Transferencia")
        self.lbl_sub_transferencia.setVisible(es_transferencia)
        self.campo_sub_transferencia.setVisible(es_transferencia)
        _aplicar_estilo_combo(self.campo_metodo, placeholder=es_placeholder)
        self._actualizar_preview()

    def _metodo_completo(self) -> str:
        """Construye el string completo del método, incluyendo sub-tipo si aplica."""
        metodo = self.campo_metodo.currentText()
        if metodo == _PLACEHOLDER_METODO:
            return ""
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
        # Descuento per-producto: precio ya es el valor real cobrado
        descuento = sum(
            max(0, ln._campo_ofertado.valor_int() - ln.campo_precio.valor_int())
            * ln.campo_cantidad.value()
            for ln in self._lineas
            if hasattr(ln, "_chk_dcto") and ln._chk_dcto.isChecked()
        )
        total_final = total_precio  # precio = precio real cobrado

        metodo = self._metodo_completo()
        pagos = self._get_pagos_combinados()

        data = self._ctrl.calcular_preview(
            total_costo, total_final, metodo, 1, pagos
        )

        if hasattr(self, "_lbl_desc_pct"):
            self._lbl_desc_pct.setText("")

        # Ahorro del cliente en panel derecho
        if descuento > 0:
            anunciado_total = total_precio + descuento
            pct = descuento / anunciado_total * 100 if anunciado_total > 0 else 0
            self._lbl_ahorro_titulo.setText(f"Ahorro del cliente ({pct:.1f}%)")
            self._lbl_ahorro_total.setText(f"- {cop(descuento)}")
            self._lbl_ahorro_titulo.setVisible(True)
            self._lbl_ahorro_total.setVisible(True)
        else:
            self._lbl_ahorro_titulo.setVisible(False)
            self._lbl_ahorro_total.setVisible(False)

        self._lbl_total_titulo.setText("Total de venta")
        self._lbl_total_venta.setText(cop(total_final))

        # Medios de pago — limpiar y repoblar
        while self._lay_medios.count():
            item = self._lay_medios.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self._btn_combinado.isChecked() and self._filas_pago:
            self._lbl_medios_titulo.setText("Medios de pago")
            for combo, monto_edit, _, combo_sub in self._filas_pago:
                m = combo.currentText()
                if m == "Transferencia" and combo_sub is not None:
                    m = f"Transferencia {combo_sub.currentText()}"
                monto = monto_edit.valor_int()
                lbl = QLabel(f"{m}:  {cop(monto)}")
                lbl.setStyleSheet(
                    "font-size:12px; font-weight:bold; color:#1E293B; background:transparent;"
                )
                self._lay_medios.addWidget(lbl)
        else:
            self._lbl_medios_titulo.setText("Medio de pago")
            if metodo:
                lbl = QLabel(f"{metodo}:  {cop(total_final)}")
                lbl.setStyleSheet(
                    "font-size:12px; font-weight:bold; color:#1E293B; background:transparent;"
                )
            else:
                lbl = QLabel("Selecciona un método de pago")
                lbl.setStyleSheet(
                    "font-size:12px; color:#9CA3AF; background:transparent;"
                )
            self._lay_medios.addWidget(lbl)

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

            # Vendedor obligatorio
            vendedor = self.campo_vendedor.currentText()
            if vendedor == self._placeholder_vendedor:
                raise ValueError("Selecciona el vendedor antes de registrar la venta.")

            # Recoger lineas del carrito (solo las que tienen producto)
            lineas = [ln.datos() for ln in self._lineas if ln.datos()["producto"]]
            if not lineas:
                raise ValueError("Agrega al menos un producto.")

            # Datos del cliente
            if self._chk_cliente.isChecked():
                cliente_nombre = self._campo_cli_nombre.text().strip()
                cliente_cedula = self._campo_cli_cedula.text().strip()
                cliente_tel    = self._campo_cli_tel.text().strip()
            else:
                cliente_nombre = cliente_cedula = cliente_tel = ""

            # Método de pago obligatorio (solo en modo simple)
            if not self._btn_combinado.isChecked() and not metodo:
                raise ValueError("Selecciona un método de pago antes de registrar la venta.")

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
            # precio ya es el valor real cobrado (descuento por producto aplicado en campo)
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
                    vendedor=vendedor,
                    cliente_nombre=cliente_nombre,
                    cliente_cedula=cliente_cedula,
                    cliente_tel=cliente_tel,
                )
            self._mostrar_exito(ventas)
            for v in ventas:
                self.venta_guardada.emit(v)
            try:
                import utils.auditoria as auditoria
                nombres = ", ".join(v.producto for v in ventas[:3])
                auditoria.registrar("Venta registrada", nombres)
            except Exception:
                pass
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
                from utils.pdf_utils import imprimir_recibo
                imprimir_recibo(ventas)
            except Exception as exc:
                QMessageBox.warning(self, "Error al imprimir recibo",
                                    f"No se pudo imprimir:\n{exc}")

    def _limpiar_form(self) -> None:
        """Resetea el formulario para la próxima entrada."""
        self.campo_fecha.setDate(QDate.currentDate())
        self.campo_metodo.setCurrentIndex(0)
        _aplicar_estilo_combo(self.campo_metodo, placeholder=True)
        self.campo_metodo.setEnabled(True)
        self.lbl_sub_transferencia.setVisible(False)
        self.campo_sub_transferencia.setCurrentIndex(0)
        self.campo_sub_transferencia.setVisible(False)
        self.campo_notas.clear()
        # Resetear barra de escaneo
        self._campo_scan.clear()
        self._lbl_scan_status.setText("")
        # Resetear modo combinado
        self._btn_combinado.setChecked(False)
        self._limpiar_filas_pago()
        self._panel_combinado.setVisible(False)
        # Resetear vendedor
        self.campo_vendedor.setCurrentIndex(0)
        _aplicar_estilo_combo(self.campo_vendedor, placeholder=True)
        # Resetear descuento
        self._chk_descuento.setChecked(False)
        self._campo_descuento.setText("")
        # Resetear cliente
        self._chk_cliente.setChecked(False)
        self._campo_cli_nombre.clear()
        self._campo_cli_cedula.clear()
        self._campo_cli_tel.clear()
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

    def _on_scan_codigo(self) -> None:
        """Busca el producto por código de barras y lo agrega al carrito al presionar Enter."""
        codigo = self._campo_scan.text().strip()
        if not codigo:
            return
        try:
            from database.inventario_repo import (
                obtener_producto_por_codigo_barras,
                obtener_producto_por_nombre_exacto,
            )
            prod = obtener_producto_por_codigo_barras(codigo) or obtener_producto_por_nombre_exacto(codigo)
            if prod is None:
                self._lbl_scan_status.setText(f"No encontrado: {codigo}")
                self._lbl_scan_status.setStyleSheet(
                    "font-size:10px; color:#DC2626; background:transparent;"
                )
            else:
                # Agregar a la primera línea vacía o crear una nueva
                linea_vacia = next(
                    (ln for ln in self._lineas if not ln.campo_producto.text().strip()), None
                )
                if linea_vacia is None:
                    self._agregar_linea()
                    linea_vacia = self._lineas[-1]
                linea_vacia.campo_producto.setText(prod.producto)
                linea_vacia._aplicar_producto(prod)
                self._lbl_scan_status.setText(f"✔ {prod.producto}")
                self._lbl_scan_status.setStyleSheet(
                    "font-size:10px; color:#15803D; background:transparent;"
                )
        except Exception:
            self._lbl_scan_status.setText("Error al buscar código.")
            self._lbl_scan_status.setStyleSheet(
                "font-size:10px; color:#DC2626; background:transparent;"
            )
        finally:
            self._campo_scan.clear()

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
