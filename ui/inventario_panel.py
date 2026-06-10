"""
ui/inventario_panel.py
Panel de gestión de inventario: tabla, formulario, importación desde Excel.
"""

import re as _re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMessageBox, QInputDialog,
    QSpinBox, QSizePolicy, QCheckBox, QScrollArea, QTabWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from database.inventario_repo import (
    obtener_todos_productos, insertar_producto,
    actualizar_producto, eliminar_producto,
)
from models.producto import Producto
from ui.venta_form import MoneyLineEdit
from utils.formatters import cop


class InventarioPanel(QWidget):
    """Vista de gestión de inventario."""

    inventario_actualizado = Signal()   # para notificar al form de venta

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._productos: list[Producto] = []
        self._editando_id: int | None = None  # id del producto en edición
        self._solo_con_stock: bool = True     # filtro por defecto
        self._edicion_desbloqueada: bool = False  # clave verificada esta sesión
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                padding: 8px 18px; font-size: 12px;
                background: #F1F5F9; border: 1px solid #E2E8F0;
                border-bottom: none; border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected {
                background: white; font-weight: bold; color: #2563EB;
                border-bottom: 2px solid #2563EB;
            }
            QTabBar::tab:hover:!selected { background: #E2E8F0; }
        """)

        # ── Tab 1: Detalle ────────────────────────────────────────────────
        tab_detalle = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenido = QWidget()
        root = QVBoxLayout(contenido)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        root.addLayout(self._barra_superior())
        root.addWidget(self._panel_form())
        root.addWidget(self._build_tabla(), stretch=1)
        root.addWidget(self._barra_resumen())

        scroll.setWidget(contenido)
        lay_detalle = QVBoxLayout(tab_detalle)
        lay_detalle.setContentsMargins(0, 0, 0, 0)
        lay_detalle.addWidget(scroll)

        # ── Tab 2: Inventario General ─────────────────────────────────────
        tab_general = self._build_tab_general()

        self._tabs.addTab(tab_detalle, "📦  Detalle")
        self._tabs.addTab(tab_general, "📊  Inventario General")
        outer.addWidget(self._tabs)

    def _barra_superior(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Inventario")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)

        self._campo_busqueda = QLineEdit()
        self._campo_busqueda.setPlaceholderText("Buscar producto…")
        self._campo_busqueda.setFixedHeight(34)
        self._campo_busqueda.setFixedWidth(240)
        self._campo_busqueda.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:5px; padding:0 10px; }"
            "QLineEdit:focus { border:2px solid #2563EB; }"
        )
        self._campo_busqueda.textChanged.connect(self._filtrar)

        self._chk_solo_stock = QCheckBox("Solo con stock")
        self._chk_solo_stock.setChecked(True)
        self._chk_solo_stock.setStyleSheet("font-size:12px; color:#374151;")
        self._chk_solo_stock.toggled.connect(self._on_toggle_stock)

        btn_nuevo = QPushButton("+ Nuevo Producto")
        btn_nuevo.setFixedHeight(34)
        btn_nuevo.setStyleSheet(
            "QPushButton { border:1px solid #2563EB; border-radius:5px; padding:0 14px;"
            "color:#2563EB; font-weight:bold; }"
            "QPushButton:hover { background:#EFF6FF; }"
        )
        btn_nuevo.clicked.connect(self._on_nuevo)

        lay.addWidget(titulo)
        lay.addSpacing(16)
        lay.addWidget(self._campo_busqueda)
        lay.addSpacing(12)
        lay.addWidget(self._chk_solo_stock)
        lay.addStretch()
        lay.addWidget(btn_nuevo)
        return lay

    def _panel_form(self) -> QFrame:
        """Formulario colapsable para agregar / editar un producto."""
        self._frame_form = QFrame()
        self._frame_form.setObjectName("formFrame")
        # El color del frame se define en GLOBAL_STYLESHEET / DARK_STYLESHEET via QFrame#formFrame
        self._frame_form.setVisible(False)

        lay = QVBoxLayout(self._frame_form)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(8)

        self._lbl_form_titulo = QLabel("Nuevo Producto")
        f = QFont(); f.setBold(True); f.setPointSize(11)
        self._lbl_form_titulo.setFont(f)
        self._lbl_form_titulo.setStyleSheet(
            "color:#0369A1; background:transparent; border:none;"
        )
        lay.addWidget(self._lbl_form_titulo)

        fila1 = QHBoxLayout(); fila1.setSpacing(10)
        fila2 = QHBoxLayout(); fila2.setSpacing(10)

        def _lbl(texto):
            l = QLabel(texto)
            l.setStyleSheet("color:#374151; font-size:11px; background:transparent; border:none;")
            return l

        def _field(placeholder, w=None):
            f = QLineEdit()
            f.setPlaceholderText(placeholder)
            f.setFixedHeight(30)
            if w:
                f.setFixedWidth(w)
            f.setStyleSheet(
                "QLineEdit { border-radius:4px; padding:0 8px; }"
                "QLineEdit:focus { border:2px solid #0EA5E9; }"
            )
            return f

        # Fila 1: serial | producto | costo
        self._f_serial  = _field("Nro. serial", 120)
        self._f_producto = _field("Nombre del producto")
        self._f_producto.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._f_costo   = MoneyLineEdit()
        self._f_costo.setPlaceholderText("Costo unitario")
        self._f_costo.setFixedHeight(30); self._f_costo.setFixedWidth(140)
        self._f_costo.setStyleSheet(
            "QLineEdit { border-radius:4px; padding:0 8px; }"
            "QLineEdit:focus { border:2px solid #0EA5E9; }"
        )

        for w, l in [
            (self._f_serial,  "Serial:"),
            (self._f_producto, "Producto:"),
            (self._f_costo,   "Costo ($):"),
        ]:
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(_lbl(l)); col.addWidget(w)
            fila1.addLayout(col)

        # Fila 2: cantidad | código de barras
        self._f_cantidad = QSpinBox()
        self._f_cantidad.setMinimum(0); self._f_cantidad.setMaximum(99999)
        self._f_cantidad.setFixedHeight(30); self._f_cantidad.setFixedWidth(100)
        self._f_cantidad.setStyleSheet(
            "QSpinBox { border-radius:4px; padding:0 6px; }"
        )

        self._f_barras = _field("Código de barras", 180)

        self._btn_guardar_form = QPushButton("Guardar")
        self._btn_guardar_form.setFixedHeight(30)
        self._btn_guardar_form.setStyleSheet(
            "QPushButton { background:#0EA5E9; color:white; border-radius:4px;"
            "padding:0 18px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#0284C7; }"
        )
        self._btn_guardar_form.clicked.connect(self._on_guardar_producto)

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(30)
        btn_cancelar.setStyleSheet(
            "QPushButton { border-radius:4px; padding:0 14px; }"
        )
        btn_cancelar.clicked.connect(self._on_cancelar_form)

        for w, l in [
            (self._f_cantidad, "Cantidad:"),
            (self._f_barras,   "Código de barras:"),
        ]:
            col = QVBoxLayout(); col.setSpacing(2)
            col.addWidget(_lbl(l)); col.addWidget(w)
            fila2.addLayout(col)

        fila2.addStretch()
        fila_btns = QVBoxLayout()
        fila_btns.addWidget(_lbl(""))
        fila_btns.addWidget(self._btn_guardar_form)
        fila2.addLayout(fila_btns)
        fila_btns2 = QVBoxLayout()
        fila_btns2.addWidget(_lbl(""))
        fila_btns2.addWidget(btn_cancelar)
        fila2.addLayout(fila_btns2)

        lay.addLayout(fila1)
        lay.addLayout(fila2)
        return self._frame_form

    def _build_tabla(self) -> QTableWidget:
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Serial", "Producto", "Talla",
            "Costo Unitario", "Cantidad", "Código de Barras", "Acciones"
        ])
        self.tabla.setColumnHidden(0, True)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setStyleSheet("""
            QTableWidget { border:none; font-size:12px; }
            QTableWidget::item { padding:4px 8px; }
            QHeaderView::section {
                background:#1E293B; color:white;
                font-weight:bold; font-size:11px;
                padding:6px; border:none;
            }
            QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }
            QToolTip {
                background:#1E293B; color:#FFFFFF;
                border:1px solid #475569; padding:5px 8px;
                font-size:12px; border-radius:4px;
            }
        """)

        hh = self.tabla.horizontalHeader()
        hh.setMinimumSectionSize(60)
        hh.setSectionResizeMode(1, QHeaderView.Fixed);        self.tabla.setColumnWidth(1, 90)
        hh.setSectionResizeMode(2, QHeaderView.Interactive);  self.tabla.setColumnWidth(2, 220)
        hh.setSectionResizeMode(3, QHeaderView.Fixed);        self.tabla.setColumnWidth(3, 58)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);        self.tabla.setColumnWidth(4, 130)
        hh.setSectionResizeMode(5, QHeaderView.Fixed);        self.tabla.setColumnWidth(5, 90)
        hh.setSectionResizeMode(6, QHeaderView.Interactive);  self.tabla.setColumnWidth(6, 140)
        hh.setSectionResizeMode(7, QHeaderView.Fixed);        self.tabla.setColumnWidth(7, 145)
        self.tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tabla.setMinimumHeight(180)

        return self.tabla

    def _barra_resumen(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; }"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 6, 14, 6)
        lay.setSpacing(20)

        self._lbl_total_prods = QLabel("0 productos")
        self._lbl_total_stock = QLabel("Stock total: 0 uds.")
        self._lbl_valor_inventario = QLabel("Valor inventario: $ 0")

        for lbl in (self._lbl_total_prods, self._lbl_total_stock, self._lbl_valor_inventario):
            lbl.setStyleSheet(
                "font-size:12px; font-weight:bold; color:#374151;"
                "background:transparent; border:none;"
            )
            lay.addWidget(lbl)

        lay.addStretch()
        return frame

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Tab Inventario General
    # ------------------------------------------------------------------

    def _build_tab_general(self) -> QWidget:
        """Tab con inventario agrupado por categoría."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenido = QWidget()
        root = QVBoxLayout(contenido)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        # Título + búsqueda
        barra = QHBoxLayout()
        titulo = QLabel("Inventario General")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)

        self._busq_general = QLineEdit()
        self._busq_general.setPlaceholderText("Filtrar categoría…")
        self._busq_general.setFixedHeight(34)
        self._busq_general.setFixedWidth(200)
        self._busq_general.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:5px; padding:0 10px; }"
            "QLineEdit:focus { border:2px solid #2563EB; }"
        )
        self._busq_general.textChanged.connect(self._filtrar_general)

        barra.addWidget(titulo)
        barra.addSpacing(16)
        barra.addWidget(self._busq_general)
        barra.addStretch()
        root.addLayout(barra)

        # Nota informativa
        nota = QLabel(
            "Unidades actuales agrupadas por tipo de producto  "
            "(primera palabra del nombre)"
        )
        nota.setStyleSheet("font-size:11px; color:#6B7280;")
        root.addWidget(nota)

        # Tabla
        self._tabla_general = QTableWidget()
        self._tabla_general.setColumnCount(4)
        self._tabla_general.setHorizontalHeaderLabels([
            "Categoría", "Referencias", "Unidades en Stock", "Valor en Stock"
        ])
        self._tabla_general.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla_general.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_general.setAlternatingRowColors(True)
        self._tabla_general.verticalHeader().setVisible(False)
        self._tabla_general.setShowGrid(False)
        self._tabla_general.setMinimumHeight(200)
        self._tabla_general.setStyleSheet("""
            QTableWidget { border:none; font-size:12px; }
            QTableWidget::item { padding:5px 10px; }
            QHeaderView::section {
                background:#1E293B; color:white;
                font-weight:bold; font-size:11px;
                padding:7px; border:none;
            }
            QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }
        """)
        hh = self._tabla_general.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Fixed); self._tabla_general.setColumnWidth(1, 110)
        hh.setSectionResizeMode(2, QHeaderView.Fixed); self._tabla_general.setColumnWidth(2, 160)
        hh.setSectionResizeMode(3, QHeaderView.Fixed); self._tabla_general.setColumnWidth(3, 160)
        root.addWidget(self._tabla_general, stretch=1)

        # Barra resumen general
        self._frame_resumen_general = QFrame()
        self._frame_resumen_general.setStyleSheet(
            "QFrame { background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; }"
        )
        lay_res = QHBoxLayout(self._frame_resumen_general)
        lay_res.setContentsMargins(14, 6, 14, 6)
        lay_res.setSpacing(20)
        self._lbl_gen_cats   = QLabel("0 categorías")
        self._lbl_gen_uds    = QLabel("0 unidades")
        self._lbl_gen_valor  = QLabel("Valor: $ 0")
        for lbl in (self._lbl_gen_cats, self._lbl_gen_uds, self._lbl_gen_valor):
            lbl.setStyleSheet(
                "font-size:12px; font-weight:bold; color:#374151;"
                "background:transparent; border:none;"
            )
            lay_res.addWidget(lbl)
        lay_res.addStretch()
        root.addWidget(self._frame_resumen_general)

        scroll.setWidget(contenido)
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)
        return tab

    def _categoria_producto(self, nombre: str) -> str:
        limpio = _re.sub(r"\s*-T:\S*", "", nombre, flags=_re.IGNORECASE).strip()
        return limpio.split()[0].upper() if limpio else "OTRO"

    def _poblar_tabla_general(self, productos=None) -> None:
        from collections import defaultdict
        fuente = productos if productos is not None else self._productos
        texto = self._busq_general.text().lower().strip()

        grupos: dict[str, dict] = defaultdict(lambda: {"refs": 0, "uds": 0, "valor": 0.0})
        for p in fuente:
            cat = self._categoria_producto(p.producto)
            grupos[cat]["refs"] += 1
            grupos[cat]["uds"] += p.cantidad
            grupos[cat]["valor"] += p.costo_unitario * p.cantidad

        if texto:
            grupos = {k: v for k, v in grupos.items() if texto in k.lower()}

        ordenados = sorted(grupos.items(), key=lambda x: -x[1]["uds"])

        self._tabla_general.setRowCount(0)
        self._tabla_general.setRowCount(len(ordenados))

        for row, (cat, d) in enumerate(ordenados):
            self._tabla_general.setRowHeight(row, 36)

            item_cat = QTableWidgetItem(cat)
            item_cat.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            f2 = QFont(); f2.setBold(True)
            item_cat.setFont(f2)
            self._tabla_general.setItem(row, 0, item_cat)

            item_refs = QTableWidgetItem(str(d["refs"]))
            item_refs.setTextAlignment(Qt.AlignCenter)
            item_refs.setForeground(QColor("#374151"))
            self._tabla_general.setItem(row, 1, item_refs)

            item_uds = QTableWidgetItem(str(d["uds"]))
            item_uds.setTextAlignment(Qt.AlignCenter)
            color_uds = QColor("#15803D") if d["uds"] > 5 else (
                QColor("#D97706") if d["uds"] > 0 else QColor("#DC2626")
            )
            item_uds.setForeground(color_uds)
            f3 = QFont(); f3.setBold(True)
            item_uds.setFont(f3)
            self._tabla_general.setItem(row, 2, item_uds)

            item_val = QTableWidgetItem(cop(d["valor"]))
            item_val.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_val.setForeground(QColor("#1D4ED8"))
            self._tabla_general.setItem(row, 3, item_val)

        total_cats = len(ordenados)
        total_uds  = sum(d["uds"] for _, d in ordenados)
        total_val  = sum(d["valor"] for _, d in ordenados)
        self._lbl_gen_cats.setText(f"{total_cats} categoría{'s' if total_cats != 1 else ''}")
        self._lbl_gen_uds.setText(f"{total_uds} unidades en stock")
        self._lbl_gen_valor.setText(f"Valor: {cop(total_val)}")

    def _filtrar_general(self, _texto: str = "") -> None:
        self._poblar_tabla_general()

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        from utils.busy import ocupado
        with ocupado(mensaje="Cargando inventario..."):
            self._productos = obtener_todos_productos()
            self._campo_busqueda.clear()
            self._aplicar_filtros()
            self._poblar_tabla_general()

    def _on_toggle_stock(self, checked: bool) -> None:
        self._solo_con_stock = checked
        self._aplicar_filtros()

    def _filtrar(self, texto: str) -> None:
        self._aplicar_filtros(texto)

    def _aplicar_filtros(self, texto: str | None = None) -> None:
        if texto is None:
            texto = self._campo_busqueda.text()
        filtrados = self._productos
        if self._solo_con_stock:
            filtrados = [p for p in filtrados if p.cantidad > 0]
        if texto.strip():
            t = texto.lower()
            filtrados = [
                p for p in filtrados
                if t in p.producto.lower()
                or t in p.serial.lower()
                or t in p.codigo_barras.lower()
            ]
        self._poblar_tabla(filtrados)
        self._actualizar_resumen(filtrados)

    def _poblar_tabla(self, productos: list[Producto]) -> None:
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(productos))

        for row, p in enumerate(productos):
            self.tabla.setRowHeight(row, 34)
            self.tabla.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self._celda(row, 1, p.serial or "", Qt.AlignCenter)
            self._celda(row, 2, p.producto)

            # Talla (col 3)
            talla_item = QTableWidgetItem(p.talla)
            talla_item.setTextAlignment(Qt.AlignCenter)
            if p.talla != "N/A":
                talla_item.setForeground(QColor("#1D4ED8"))
            else:
                talla_item.setForeground(QColor("#9CA3AF"))
            self.tabla.setItem(row, 3, talla_item)

            self._celda(row, 4, cop(p.costo_unitario), Qt.AlignRight | Qt.AlignVCenter)

            # Cantidad con color (col 5)
            item_cant = QTableWidgetItem(str(p.cantidad))
            item_cant.setTextAlignment(Qt.AlignCenter)
            if p.cantidad == 0:
                item_cant.setForeground(QColor("#DC2626"))
            elif p.cantidad <= 3:
                item_cant.setForeground(QColor("#D97706"))
            else:
                item_cant.setForeground(QColor("#15803D"))
            self.tabla.setItem(row, 5, item_cant)

            self._celda(row, 6, p.codigo_barras or "", Qt.AlignCenter)

            # Acciones
            self.tabla.setCellWidget(row, 7, self._widget_acciones(p.id))

    def _celda(self, row, col, texto, alin=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alin)
        if texto:
            item.setToolTip(texto)
        self.tabla.setItem(row, col, item)

    def _actualizar_resumen(self, productos: list[Producto]) -> None:
        total_prods = len(productos)
        total_stock = sum(p.cantidad for p in productos)
        valor = sum(p.costo_unitario * p.cantidad for p in productos)
        self._lbl_total_prods.setText(f"{total_prods} producto{'s' if total_prods != 1 else ''}")
        self._lbl_total_stock.setText(f"Stock total: {total_stock} uds.")
        self._lbl_valor_inventario.setText(f"Valor inventario: {cop(valor)}")

    def _widget_acciones(self, producto_id: int) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)

        btn_editar = QPushButton("Editar")
        btn_editar.setFixedHeight(26)
        btn_editar.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 10px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn_editar.clicked.connect(lambda _, pid=producto_id: self._on_editar(pid))

        btn_eliminar = QPushButton("Borrar")
        btn_eliminar.setFixedHeight(26)
        btn_eliminar.setStyleSheet(
            "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 10px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn_eliminar.clicked.connect(lambda _, pid=producto_id: self._on_eliminar(pid))

        lay.addWidget(btn_editar)
        lay.addWidget(btn_eliminar)
        return w

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _verificar_edicion(self) -> bool:
        """Pide la clave una sola vez por sesión antes de permitir modificaciones."""
        if self._edicion_desbloqueada:
            return True
        from database.config_repo import obtener_configuracion
        clave_correcta = obtener_configuracion().clave_inventario
        clave, ok = QInputDialog.getText(
            self, "Modificar inventario",
            "Ingresa la contraseña para editar:",
            QLineEdit.Password,
        )
        if not ok or clave != clave_correcta:
            if ok:
                QMessageBox.warning(self, "Acceso denegado", "Contraseña incorrecta.")
            return False
        self._edicion_desbloqueada = True
        return True

    def _on_nuevo(self) -> None:
        if not self._verificar_edicion():
            return
        self._editando_id = None
        self._lbl_form_titulo.setText("Nuevo Producto")
        self._btn_guardar_form.setText("Guardar")
        self._limpiar_form()
        self._frame_form.setVisible(True)
        self._f_producto.setFocus()

    def _on_cancelar_form(self) -> None:
        self._frame_form.setVisible(False)
        self._editando_id = None

    def _on_editar(self, producto_id: int) -> None:
        if not self._verificar_edicion():
            return
        p = next((x for x in self._productos if x.id == producto_id), None)
        if not p:
            return
        self._editando_id = producto_id
        self._lbl_form_titulo.setText("Editar Producto")
        self._btn_guardar_form.setText("Actualizar")
        self._f_serial.setText(p.serial)
        self._f_producto.setText(p.producto)
        self._f_costo.set_valor(int(p.costo_unitario))
        self._f_cantidad.setValue(p.cantidad)
        self._f_barras.setText(p.codigo_barras)
        self._frame_form.setVisible(True)
        self._f_producto.setFocus()

    def _on_guardar_producto(self) -> None:
        producto_nombre = self._f_producto.text().strip()
        if not producto_nombre:
            QMessageBox.warning(self, "Campo requerido",
                                "Ingresa el nombre del producto.")
            self._f_producto.setFocus()
            return

        costo = float(self._f_costo.valor_int())

        try:
            p = Producto(
                serial=self._f_serial.text().strip(),
                producto=producto_nombre,
                costo_unitario=costo,
                cantidad=self._f_cantidad.value(),
                codigo_barras=self._f_barras.text().strip(),
                id=self._editando_id,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Dato inválido", str(exc))
            return

        if self._editando_id is None:
            insertar_producto(p)
        else:
            actualizar_producto(p)

        self._frame_form.setVisible(False)
        self._editando_id = None
        self.refresh()
        self.inventario_actualizado.emit()

    def _on_eliminar(self, producto_id: int) -> None:
        if not self._verificar_edicion():
            return
        p = next((x for x in self._productos if x.id == producto_id), None)
        nombre = p.producto if p else f"id {producto_id}"
        resp = QMessageBox.question(
            self, "Eliminar producto",
            f"¿Eliminar <b>{nombre}</b> del inventario?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            eliminar_producto(producto_id)
            self.refresh()
            self.inventario_actualizado.emit()

    def _limpiar_form(self) -> None:
        self._f_serial.clear()
        self._f_producto.clear()
        self._f_costo.clear()
        self._f_cantidad.setValue(0)
        self._f_barras.clear()
