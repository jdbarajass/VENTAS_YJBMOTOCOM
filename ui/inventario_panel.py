"""
ui/inventario_panel.py
Panel de gestión de inventario con pestañas: Detalle, Inventario General,
Movimientos, Ingresar y Cambios.
"""

import re as _re

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMessageBox, QInputDialog,
    QSpinBox, QSizePolicy, QCheckBox, QScrollArea, QTabWidget,
    QComboBox, QCompleter, QListWidget, QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal, QStringListModel
from PySide6.QtGui import QFont, QColor

from database.inventario_repo import (
    obtener_todos_productos, insertar_producto,
    actualizar_producto, eliminar_producto,
    obtener_productos_bajo_stock,
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

        # ── Tab 3: Movimientos ────────────────────────────────────────────
        tab_mov = self._build_tab_movimientos()

        # ── Tab 4: Ingresar ───────────────────────────────────────────────
        tab_ingresar = self._build_tab_ingresar()

        # ── Tab 5: Cambios ────────────────────────────────────────────────
        tab_cambios = self._build_tab_cambios()

        self._tabs.addTab(tab_detalle,  "📦  Detalle")
        self._tabs.addTab(tab_general,  "📊  Inventario General")
        self._tabs.addTab(tab_mov,      "📋  Movimientos")
        self._tabs.addTab(tab_ingresar, "➕  Ingresar")
        self._tabs.addTab(tab_cambios,  "🔄  Cambios")
        self._tabs.currentChanged.connect(self._on_tab_changed)
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

        btn_pdf = QPushButton("📄 PDF")
        btn_pdf.setFixedHeight(34)
        btn_pdf.setStyleSheet(
            "QPushButton { border:1px solid #64748B; border-radius:5px; padding:0 12px;"
            "color:#374151; font-size:12px; }"
            "QPushButton:hover { background:#F1F5F9; }"
        )
        btn_pdf.clicked.connect(self._on_exportar_pdf)

        lay.addWidget(titulo)
        lay.addSpacing(16)
        lay.addWidget(self._campo_busqueda)
        lay.addSpacing(12)
        lay.addWidget(self._chk_solo_stock)
        lay.addStretch()
        lay.addWidget(btn_pdf)
        lay.addSpacing(8)
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

        # Fila 2: talla | cantidad | stock mínimo | código de barras
        self._f_talla = _field("Talla (XS/S/M/L/XL…)", 100)

        self._f_cantidad = QSpinBox()
        self._f_cantidad.setMinimum(0); self._f_cantidad.setMaximum(99999)
        self._f_cantidad.setFixedHeight(30); self._f_cantidad.setFixedWidth(100)
        self._f_cantidad.setStyleSheet(
            "QSpinBox { border-radius:4px; padding:0 6px; }"
        )

        self._f_stock_min = QSpinBox()
        self._f_stock_min.setMinimum(0); self._f_stock_min.setMaximum(9999)
        self._f_stock_min.setFixedHeight(30); self._f_stock_min.setFixedWidth(100)
        self._f_stock_min.setToolTip("Alerta en Dashboard cuando el stock baje de este valor. 0 = sin alerta.")
        self._f_stock_min.setStyleSheet(
            "QSpinBox { border-radius:4px; padding:0 6px; }"
        )

        self._f_barras    = _field("Código de barras", 180)
        self._f_categoria = _field("Categoría (ej: Cascos)", 160)

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
            (self._f_talla,     "Talla:"),
            (self._f_cantidad,  "Cantidad:"),
            (self._f_stock_min, "Stock mínimo:"),
            (self._f_barras,    "Código de barras:"),
            (self._f_categoria, "Categoría:"),
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
        self.tabla.setColumnCount(9)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Serial", "Producto", "Talla",
            "Costo Unitario", "Cantidad", "Código de Barras", "Categoría", "Acciones"
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
        hh.setSectionResizeMode(2, QHeaderView.Interactive);  self.tabla.setColumnWidth(2, 200)
        hh.setSectionResizeMode(3, QHeaderView.Fixed);        self.tabla.setColumnWidth(3, 58)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);        self.tabla.setColumnWidth(4, 120)
        hh.setSectionResizeMode(5, QHeaderView.Fixed);        self.tabla.setColumnWidth(5, 80)
        hh.setSectionResizeMode(6, QHeaderView.Interactive);  self.tabla.setColumnWidth(6, 130)
        hh.setSectionResizeMode(7, QHeaderView.Interactive);  self.tabla.setColumnWidth(7, 110)
        hh.setSectionResizeMode(8, QHeaderView.Fixed);        self.tabla.setColumnWidth(8, 145)
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

    def _categoria_producto(self, p) -> str:
        """Categoría explícita si existe, si no inferida de la primera palabra del nombre."""
        if hasattr(p, "categoria") and p.categoria:
            return p.categoria.strip().upper()
        nombre = p.producto if hasattr(p, "producto") else str(p)
        limpio = _re.sub(r"\s*-T:\S*", "", nombre, flags=_re.IGNORECASE).strip()
        return limpio.split()[0].upper() if limpio else "OTRO"

    def _poblar_tabla_general(self, productos=None) -> None:
        from collections import defaultdict
        fuente = productos if productos is not None else self._productos
        texto = self._busq_general.text().lower().strip()

        grupos: dict[str, dict] = defaultdict(lambda: {"refs": 0, "uds": 0, "valor": 0.0})
        for p in fuente:
            cat = self._categoria_producto(p)
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

    # ── Tab 3: Movimientos ────────────────────────────────────────────────

    def _build_tab_movimientos(self) -> QWidget:
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(10)

        # Barra superior
        barra = QHBoxLayout()
        titulo = QLabel("Historial de Movimientos")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        titulo.setFont(f)

        self._busq_mov = QLineEdit()
        self._busq_mov.setPlaceholderText("Filtrar por producto…")
        self._busq_mov.setFixedHeight(32)
        self._busq_mov.setFixedWidth(220)
        self._busq_mov.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:5px; padding:0 10px; }"
        )
        self._busq_mov.textChanged.connect(self._filtrar_movimientos)

        btn_refrescar = QPushButton("↻ Actualizar")
        btn_refrescar.setFixedHeight(32)
        btn_refrescar.setStyleSheet(
            "QPushButton { border-radius:5px; padding:0 12px; font-size:11px; }"
        )
        btn_refrescar.clicked.connect(self._cargar_movimientos)

        barra.addWidget(titulo)
        barra.addSpacing(16)
        barra.addWidget(self._busq_mov)
        barra.addStretch()
        barra.addWidget(btn_refrescar)
        root.addLayout(barra)

        # Tabla
        self._tabla_mov = QTableWidget()
        self._tabla_mov.setColumnCount(8)
        self._tabla_mov.setHorizontalHeaderLabels([
            "Fecha", "Hora", "Producto", "Tipo", "Anterior", "Nuevo", "Cambio", "Notas"
        ])
        self._tabla_mov.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla_mov.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_mov.verticalHeader().setVisible(False)
        self._tabla_mov.setShowGrid(False)
        self._tabla_mov.setAlternatingRowColors(True)
        self._tabla_mov.setStyleSheet("""
            QTableWidget { border:1px solid #E5E7EB; border-radius:8px; font-size:12px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:11px; padding:5px; border:none;
            }
            QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }
        """)
        hh = self._tabla_mov.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Interactive); self._tabla_mov.setColumnWidth(0, 90)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); self._tabla_mov.setColumnWidth(1, 75)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Interactive); self._tabla_mov.setColumnWidth(3, 80)
        hh.setSectionResizeMode(4, QHeaderView.Interactive); self._tabla_mov.setColumnWidth(4, 75)
        hh.setSectionResizeMode(5, QHeaderView.Interactive); self._tabla_mov.setColumnWidth(5, 75)
        hh.setSectionResizeMode(6, QHeaderView.Interactive); self._tabla_mov.setColumnWidth(6, 75)
        hh.setSectionResizeMode(7, QHeaderView.Interactive); self._tabla_mov.setColumnWidth(7, 160)

        root.addWidget(self._tabla_mov, stretch=1)
        self._movimientos_cache: list[dict] = []
        return tab

    def _on_tab_changed(self, idx: int) -> None:
        texto = self._tabs.tabText(idx)
        if texto.startswith("📋"):
            self._cargar_movimientos()
        elif texto.startswith("➕"):
            self._ingresar_refrescar_auto()

    def _cargar_movimientos(self) -> None:
        from database.inventario_mov_repo import obtener_movimientos_recientes
        self._movimientos_cache = obtener_movimientos_recientes(300)
        self._filtrar_movimientos(self._busq_mov.text())

    def _filtrar_movimientos(self, texto: str = "") -> None:
        texto = texto.strip().lower()
        datos = [
            m for m in self._movimientos_cache
            if not texto or texto in m["producto"].lower()
        ]
        self._tabla_mov.setRowCount(0)
        self._tabla_mov.setRowCount(len(datos))
        for row, m in enumerate(datos):
            self._tabla_mov.setRowHeight(row, 28)
            self._tabla_mov.setItem(row, 0, QTableWidgetItem(m["fecha"]))
            self._tabla_mov.setItem(row, 1, QTableWidgetItem(m["hora"]))

            item_prod = QTableWidgetItem(m["producto"])
            item_prod.setToolTip(m["producto"])
            self._tabla_mov.setItem(row, 2, item_prod)

            item_tipo = QTableWidgetItem(m["tipo"])
            item_tipo.setTextAlignment(Qt.AlignCenter)
            color_tipo = {
                "Venta": QColor("#DC2626"),
                "Ajuste": QColor("#2563EB"),
                "Entrada": QColor("#15803D"),
            }.get(m["tipo"], QColor("#374151"))
            item_tipo.setForeground(color_tipo)
            self._tabla_mov.setItem(row, 3, item_tipo)

            for col, val in [(4, m["cantidad_ant"]), (5, m["cantidad_nva"])]:
                it = QTableWidgetItem(str(val))
                it.setTextAlignment(Qt.AlignCenter)
                self._tabla_mov.setItem(row, col, it)

            dif = m["diferencia"]
            item_dif = QTableWidgetItem(f"{'+' if dif > 0 else ''}{dif}")
            item_dif.setTextAlignment(Qt.AlignCenter)
            item_dif.setForeground(QColor("#15803D") if dif > 0 else QColor("#DC2626"))
            self._tabla_mov.setItem(row, 6, item_dif)

            self._tabla_mov.setItem(row, 7, QTableWidgetItem(m.get("notas", "")))

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
        productos = sorted(productos, key=lambda p: p.producto.upper())
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

            # Cantidad con color (col 5) — rojo si bajo mínimo, naranja si stock ≤ 3 sin mínimo
            item_cant = QTableWidgetItem(str(p.cantidad))
            item_cant.setTextAlignment(Qt.AlignCenter)
            if p.cantidad == 0:
                item_cant.setForeground(QColor("#DC2626"))
            elif p.bajo_stock:
                item_cant.setForeground(QColor("#DC2626"))
                item_cant.setToolTip(f"⚠ Bajo mínimo: {p.cantidad}/{p.stock_minimo} ud.")
            elif p.cantidad <= 3:
                item_cant.setForeground(QColor("#D97706"))
            else:
                item_cant.setForeground(QColor("#15803D"))
            self.tabla.setItem(row, 5, item_cant)

            self._celda(row, 6, p.codigo_barras or "", Qt.AlignCenter)

            # Categoría (col 7)
            cat_item = QTableWidgetItem(p.categoria or "")
            cat_item.setTextAlignment(Qt.AlignCenter)
            if p.categoria:
                cat_item.setForeground(QColor("#7C3AED"))
            else:
                cat_item.setForeground(QColor("#9CA3AF"))
            self.tabla.setItem(row, 7, cat_item)

            # Acciones
            self.tabla.setCellWidget(row, 8, self._widget_acciones(p.id))

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
        # Mostrar nombre sin el sufijo -T:TALLA en el campo producto
        import re as _re2
        nombre_limpio = _re2.sub(r"\s*-T:\S+$", "", p.producto, flags=_re2.IGNORECASE).strip()
        self._f_producto.setText(nombre_limpio)
        self._f_talla.setText(p.talla)
        self._f_costo.set_valor(int(p.costo_unitario))
        self._f_cantidad.setValue(p.cantidad)
        self._f_stock_min.setValue(p.stock_minimo)
        self._f_barras.setText(p.codigo_barras)
        self._f_categoria.setText(p.categoria)
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

        # Incorporar la talla al nombre si fue indicada
        talla = self._f_talla.text().strip().upper()
        if talla:
            producto_nombre = f"{producto_nombre} -T:{talla}"

        try:
            p = Producto(
                serial=self._f_serial.text().strip(),
                producto=producto_nombre,
                costo_unitario=costo,
                cantidad=self._f_cantidad.value(),
                codigo_barras=self._f_barras.text().strip(),
                stock_minimo=self._f_stock_min.value(),
                categoria=self._f_categoria.text().strip(),
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

    def _on_exportar_pdf(self) -> None:
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog
        from services.pdf_reporte import generar_pdf_inventario

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF de inventario",
            str(Path.home() / "inventario.pdf"),
            "PDF (*.pdf)",
        )
        if not ruta:
            return
        try:
            generar_pdf_inventario(
                self._productos,
                Path(ruta),
                solo_con_stock=self._solo_con_stock,
            )
            import subprocess, sys
            if sys.platform == "win32":
                subprocess.Popen(["start", "", ruta], shell=True)
            QMessageBox.information(self, "PDF generado", f"Guardado en:\n{ruta}")
        except Exception as e:
            QMessageBox.critical(self, "Error al generar PDF", str(e))

    def _limpiar_form(self) -> None:
        self._f_serial.clear()
        self._f_producto.clear()
        self._f_talla.clear()
        self._f_costo.clear()
        self._f_cantidad.setValue(0)
        self._f_stock_min.setValue(0)
        self._f_barras.clear()
        self._f_categoria.clear()

    # ──────────────────────────────────────────────────────────────────────
    # Tab 4: Ingresar producto nuevo
    # ──────────────────────────────────────────────────────────────────────

    def _build_tab_ingresar(self) -> QWidget:
        """Construye la pestaña de ingreso rápido de nuevos productos al inventario."""
        tab = QWidget()
        root = QHBoxLayout(tab)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # ── Panel izquierdo: formulario ───────────────────────────────────
        izq = QFrame()
        izq.setObjectName("ingresarForm")
        izq.setStyleSheet(
            "QFrame#ingresarForm { background:#F0FDF4; border:1px solid #BBF7D0;"
            "border-radius:10px; }"
        )
        lay_izq = QVBoxLayout(izq)
        lay_izq.setContentsMargins(20, 18, 20, 18)
        lay_izq.setSpacing(12)

        titulo_ing = QLabel("Ingresar nuevo producto")
        f_t = QFont(); f_t.setPointSize(14); f_t.setBold(True)
        titulo_ing.setFont(f_t)
        titulo_ing.setStyleSheet("color:#15803D; background:transparent; border:none;")
        lay_izq.addWidget(titulo_ing)

        def _lbl(texto):
            l = QLabel(texto)
            l.setStyleSheet("color:#374151; font-size:11px; background:transparent; border:none;")
            return l

        def _field(placeholder, w=None):
            f = QLineEdit()
            f.setPlaceholderText(placeholder)
            f.setFixedHeight(32)
            if w:
                f.setFixedWidth(w)
            f.setStyleSheet(
                "QLineEdit { border:1px solid #D1D5DB; border-radius:5px; padding:0 8px; }"
                "QLineEdit:focus { border:2px solid #16A34A; }"
            )
            return f

        # Nombre del producto con autocompletado
        lay_izq.addWidget(_lbl("Nombre del producto:"))
        self._ing_nombre = _field("Ej: Casco Integral HJC Rojo")
        self._ing_nombre.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._ing_completer = QCompleter([], self._ing_nombre)
        self._ing_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._ing_completer.setFilterMode(Qt.MatchContains)
        self._ing_nombre.setCompleter(self._ing_completer)
        self._ing_nombre.textChanged.connect(self._ingresar_on_nombre_cambiado)
        lay_izq.addWidget(self._ing_nombre)

        # Talla
        lay_izq.addWidget(_lbl("Talla:"))
        self._ing_talla = QComboBox()
        self._ing_talla.addItems(["XS", "S", "M", "L", "XL", "2XL", "3XL", "N/A"])
        self._ing_talla.setCurrentText("N/A")
        self._ing_talla.setFixedHeight(32)
        self._ing_talla.setStyleSheet(
            "QComboBox { border:1px solid #D1D5DB; border-radius:5px; padding:0 8px;"
            "font-size:12px; }"
            "QComboBox:focus { border:2px solid #16A34A; }"
        )
        self._ing_talla.currentTextChanged.connect(self._ingresar_actualizar_codigo)
        lay_izq.addWidget(self._ing_talla)

        # Costo unitario y cantidad en la misma fila
        fila_nums = QHBoxLayout(); fila_nums.setSpacing(12)

        col_costo = QVBoxLayout(); col_costo.setSpacing(3)
        col_costo.addWidget(_lbl("Costo unitario ($):"))
        self._ing_costo = MoneyLineEdit()
        self._ing_costo.setPlaceholderText("0")
        self._ing_costo.setFixedHeight(32)
        self._ing_costo.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:5px; padding:0 8px; }"
            "QLineEdit:focus { border:2px solid #16A34A; }"
        )
        col_costo.addWidget(self._ing_costo)
        fila_nums.addLayout(col_costo)

        col_cant = QVBoxLayout(); col_cant.setSpacing(3)
        col_cant.addWidget(_lbl("Cantidad a ingresar:"))
        self._ing_cantidad = QSpinBox()
        self._ing_cantidad.setMinimum(1); self._ing_cantidad.setMaximum(99999)
        self._ing_cantidad.setValue(1)
        self._ing_cantidad.setFixedHeight(32)
        self._ing_cantidad.setStyleSheet(
            "QSpinBox { border:1px solid #D1D5DB; border-radius:5px; padding:0 6px; }"
        )
        col_cant.addWidget(self._ing_cantidad)
        fila_nums.addLayout(col_cant)

        lay_izq.addLayout(fila_nums)

        # Serial y código de barras (auto, editables)
        fila_auto = QHBoxLayout(); fila_auto.setSpacing(12)

        col_serial = QVBoxLayout(); col_serial.setSpacing(3)
        col_serial.addWidget(_lbl("Serial (auto):"))
        self._ing_serial = _field("Auto", 100)
        self._ing_serial.setReadOnly(True)
        self._ing_serial.setStyleSheet(
            "QLineEdit { border:1px solid #BBF7D0; border-radius:5px; padding:0 8px;"
            "background:#F0FDF4; color:#15803D; font-weight:bold; }"
        )
        col_serial.addWidget(self._ing_serial)
        fila_auto.addLayout(col_serial)

        col_barras = QVBoxLayout(); col_barras.setSpacing(3)
        col_barras.addWidget(_lbl("Código de barras (auto):"))
        self._ing_barras = _field("Auto")
        self._ing_barras.setReadOnly(True)
        self._ing_barras.setStyleSheet(
            "QLineEdit { border:1px solid #BBF7D0; border-radius:5px; padding:0 8px;"
            "background:#F0FDF4; color:#15803D; font-weight:bold; }"
        )
        col_barras.addWidget(self._ing_barras)
        fila_auto.addLayout(col_barras)

        lay_izq.addLayout(fila_auto)

        nota_auto = QLabel(
            "El serial y el código de barras se generan automáticamente. "
            "Puedes editarlos si necesitas un valor específico."
        )
        nota_auto.setStyleSheet("font-size:10px; color:#6B7280; background:transparent; border:none;")
        nota_auto.setWordWrap(True)
        lay_izq.addWidget(nota_auto)

        # Habilitar edición manual de serial y barras
        def _toggle_editable(editable: bool) -> None:
            for f in (self._ing_serial, self._ing_barras):
                f.setReadOnly(not editable)
                f.setStyleSheet(
                    "QLineEdit { border:1px solid #D1D5DB; border-radius:5px; padding:0 8px; }"
                    if editable else
                    "QLineEdit { border:1px solid #BBF7D0; border-radius:5px; padding:0 8px;"
                    "background:#F0FDF4; color:#15803D; font-weight:bold; }"
                )

        chk_editar_auto = QCheckBox("Editar serial / código manualmente")
        chk_editar_auto.setStyleSheet("font-size:11px; color:#374151; background:transparent; border:none;")
        chk_editar_auto.toggled.connect(_toggle_editable)
        lay_izq.addWidget(chk_editar_auto)

        lay_izq.addStretch()

        # Botón guardar
        self._btn_ingresar = QPushButton("✚  Ingresar al inventario")
        self._btn_ingresar.setFixedHeight(42)
        self._btn_ingresar.setStyleSheet(
            "QPushButton { background:#16A34A; color:white; border-radius:8px;"
            "font-size:13px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#15803D; }"
        )
        self._btn_ingresar.clicked.connect(self._on_ingresar_guardar)
        lay_izq.addWidget(self._btn_ingresar)

        root.addWidget(izq, stretch=2)

        # ── Panel derecho: productos similares ────────────────────────────
        der = QFrame()
        der.setObjectName("ingresarSimilares")
        der.setStyleSheet(
            "QFrame#ingresarSimilares { background:#F8FAFC; border:1px solid #E2E8F0;"
            "border-radius:10px; }"
        )
        lay_der = QVBoxLayout(der)
        lay_der.setContentsMargins(16, 16, 16, 16)
        lay_der.setSpacing(8)

        titulo_sim = QLabel("Productos similares")
        f_s = QFont(); f_s.setPointSize(12); f_s.setBold(True)
        titulo_sim.setFont(f_s)
        titulo_sim.setStyleSheet("color:#374151; background:transparent; border:none;")
        lay_der.addWidget(titulo_sim)

        self._ing_lbl_cat = QLabel("(escribe el nombre para ver sugerencias)")
        self._ing_lbl_cat.setStyleSheet(
            "font-size:11px; color:#6B7280; background:transparent; border:none;"
        )
        self._ing_lbl_cat.setWordWrap(True)
        lay_der.addWidget(self._ing_lbl_cat)

        self._ing_tabla_sim = QTableWidget()
        self._ing_tabla_sim.setColumnCount(4)
        self._ing_tabla_sim.setHorizontalHeaderLabels(["Serial", "Producto", "Talla", "Cant."])
        self._ing_tabla_sim.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ing_tabla_sim.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._ing_tabla_sim.verticalHeader().setVisible(False)
        self._ing_tabla_sim.setShowGrid(False)
        self._ing_tabla_sim.setAlternatingRowColors(True)
        self._ing_tabla_sim.setStyleSheet("""
            QTableWidget { border:none; font-size:11px; }
            QHeaderView::section {
                background:#334155; color:white; font-weight:bold;
                font-size:10px; padding:4px; border:none;
            }
        """)
        hh_sim = self._ing_tabla_sim.horizontalHeader()
        hh_sim.setSectionResizeMode(0, QHeaderView.Fixed); self._ing_tabla_sim.setColumnWidth(0, 70)
        hh_sim.setSectionResizeMode(1, QHeaderView.Stretch)
        hh_sim.setSectionResizeMode(2, QHeaderView.Fixed); self._ing_tabla_sim.setColumnWidth(2, 55)
        hh_sim.setSectionResizeMode(3, QHeaderView.Fixed); self._ing_tabla_sim.setColumnWidth(3, 50)
        lay_der.addWidget(self._ing_tabla_sim, stretch=1)

        root.addWidget(der, stretch=3)

        return tab

    def _ingresar_refrescar_auto(self) -> None:
        """Actualiza serial y código cuando se abre el tab."""
        from services.inventario_gen import generar_siguiente_serial, generar_codigo_barras_auto
        siguiente = generar_siguiente_serial(self._productos)
        self._ing_serial.setText(str(siguiente))
        nombre = self._ing_nombre.text().strip()
        talla  = self._ing_talla.currentText()
        codigo = generar_codigo_barras_auto(nombre, talla, self._productos)
        self._ing_barras.setText(codigo)

    def _ingresar_actualizar_codigo(self, _=None) -> None:
        """Recalcula y muestra el código de barras sugerido según nombre y talla actuales."""
        from services.inventario_gen import generar_codigo_barras_auto
        nombre = self._ing_nombre.text().strip()
        talla  = self._ing_talla.currentText()
        codigo = generar_codigo_barras_auto(nombre, talla, self._productos)
        self._ing_barras.setText(codigo)

    def _ingresar_on_nombre_cambiado(self, texto: str) -> None:
        """Actualiza sugerencias de nombres, código de barras y tabla de similares."""
        from services.inventario_gen import detectar_categoria, generar_codigo_barras_auto

        # Sugerencias para el completer
        nombres_existentes = sorted({p.producto for p in self._productos})
        model = QStringListModel(nombres_existentes, self._ing_completer)
        self._ing_completer.setModel(model)

        # Código de barras
        self._ingresar_actualizar_codigo()

        # Filtrar similares por categoría detectada
        cc = detectar_categoria(texto)
        from services.inventario_gen import _CAT_PREFIJOS
        nombre_cat = next(
            (k.capitalize() for k, v in _CAT_PREFIJOS.items() if v == cc), "Accesorios"
        )

        similares = [
            p for p in self._productos
            if cc == detectar_categoria(p.producto)
        ]
        self._ing_lbl_cat.setText(
            f"Categoría detectada: {nombre_cat}  ({len(similares)} producto(s))"
        )

        self._ing_tabla_sim.setRowCount(0)
        self._ing_tabla_sim.setRowCount(len(similares))
        for row, p in enumerate(similares):
            self._ing_tabla_sim.setRowHeight(row, 26)
            self._ing_tabla_sim.setItem(row, 0, QTableWidgetItem(p.serial or ""))
            item_nom = QTableWidgetItem(p.producto)
            item_nom.setToolTip(p.producto)
            self._ing_tabla_sim.setItem(row, 1, item_nom)
            self._ing_tabla_sim.setItem(row, 2, QTableWidgetItem(p.talla))
            it_cant = QTableWidgetItem(str(p.cantidad))
            it_cant.setTextAlignment(Qt.AlignCenter)
            self._ing_tabla_sim.setItem(row, 3, it_cant)

    def _on_ingresar_guardar(self) -> None:
        """Valida el formulario y persiste el nuevo producto en la base de datos."""
        nombre = self._ing_nombre.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Campo requerido", "Ingresa el nombre del producto.")
            self._ing_nombre.setFocus()
            return

        talla    = self._ing_talla.currentText()
        costo    = float(self._ing_costo.valor_int())
        cantidad = self._ing_cantidad.value()
        serial   = self._ing_serial.text().strip()
        barras   = self._ing_barras.text().strip()

        # Nombre con talla embebida si no es N/A
        nombre_completo = nombre
        if talla and talla != "N/A":
            nombre_completo = f"{nombre} -T:{talla}"

        try:
            p = Producto(
                serial=serial,
                producto=nombre_completo,
                talla=talla,
                costo_unitario=costo,
                cantidad=cantidad,
                codigo_barras=barras,
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Dato inválido", str(exc))
            return

        insertar_producto(p)
        self.refresh()
        self.inventario_actualizado.emit()

        # Limpiar form y regenerar serial
        self._ing_nombre.clear()
        self._ing_talla.setCurrentText("N/A")
        self._ing_costo.clear()
        self._ing_cantidad.setValue(1)
        self._ingresar_refrescar_auto()

        QMessageBox.information(
            self, "Producto ingresado",
            f"✓ '{nombre_completo}' agregado con serial {serial}."
        )

    # ──────────────────────────────────────────────────────────────────────
    # Tab 5: Cambios de producto
    # ──────────────────────────────────────────────────────────────────────

    def _build_tab_cambios(self) -> QWidget:
        """Construye la pestaña de cambio entre dos productos del inventario."""
        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        titulo_cam = QLabel("Cambio de producto")
        f_t2 = QFont(); f_t2.setPointSize(14); f_t2.setBold(True)
        titulo_cam.setFont(f_t2)
        root.addWidget(titulo_cam)

        subtitulo = QLabel(
            "El cliente devuelve un producto y lo cambia por otro. "
            "Escanea o busca ambos artículos."
        )
        subtitulo.setStyleSheet("font-size:12px; color:#6B7280;")
        root.addWidget(subtitulo)

        columnas = QHBoxLayout(); columnas.setSpacing(20)

        # ── Columna SALE ──────────────────────────────────────────────────
        frame_sale = self._build_cambio_columna(
            "sale", "Producto que SALE  (devuelve el cliente)", "#FEF2F2", "#FECACA", "#B91C1C"
        )
        # ── Columna ENTRA ─────────────────────────────────────────────────
        frame_entra = self._build_cambio_columna(
            "entra", "Producto que ENTRA  (quiere el cliente)", "#F0FDF4", "#BBF7D0", "#15803D"
        )

        columnas.addWidget(frame_sale)
        columnas.addWidget(frame_entra)
        root.addLayout(columnas)

        # Botón confirmar
        self._btn_confirmar_cambio = QPushButton("🔄  Confirmar cambio")
        self._btn_confirmar_cambio.setFixedHeight(46)
        self._btn_confirmar_cambio.setStyleSheet(
            "QPushButton { background:#7C3AED; color:white; border-radius:8px;"
            "font-size:14px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#6D28D9; }"
        )
        self._btn_confirmar_cambio.clicked.connect(self._on_confirmar_cambio)
        root.addWidget(self._btn_confirmar_cambio)

        return tab

    def _build_cambio_columna(
        self,
        prefijo: str,
        titulo: str,
        bg: str,
        border: str,
        color_titulo: str,
    ) -> QFrame:
        """Crea el panel de búsqueda y detalle para uno de los dos lados del cambio (sale/entra)."""
        frame = QFrame()
        frame.setObjectName(f"cambioFrame_{prefijo}")
        frame.setStyleSheet(
            f"QFrame#cambioFrame_{prefijo} {{ background:{bg}; border:1px solid {border};"
            "border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)

        lbl_titulo = QLabel(titulo)
        f_t3 = QFont(); f_t3.setPointSize(12); f_t3.setBold(True)
        lbl_titulo.setFont(f_t3)
        lbl_titulo.setStyleSheet(
            f"color:{color_titulo}; background:transparent; border:none;"
        )
        lay.addWidget(lbl_titulo)

        def _lbl(t):
            l = QLabel(t)
            l.setStyleSheet("font-size:11px; color:#374151; background:transparent; border:none;")
            return l

        # Campo de búsqueda / scanner
        lay.addWidget(_lbl("Escanea o ingresa el código de barras:"))
        campo_scanner = QLineEdit()
        campo_scanner.setPlaceholderText("Código de barras… (Enter para buscar)")
        campo_scanner.setFixedHeight(36)
        campo_scanner.setStyleSheet(
            f"QLineEdit {{ border:2px solid {border}; border-radius:6px; padding:0 10px;"
            "font-size:13px; }"
            f"QLineEdit:focus {{ border:2px solid {color_titulo}; }}"
        )
        lay.addWidget(campo_scanner)

        # Búsqueda por nombre
        lay.addWidget(_lbl("O busca por nombre (escribe 2+ letras):"))
        campo_nombre = QLineEdit()
        campo_nombre.setPlaceholderText("Nombre del producto…")
        campo_nombre.setFixedHeight(32)
        campo_nombre.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:5px; padding:0 8px; }"
            "QLineEdit:focus { border:2px solid #6366F1; }"
        )
        lay.addWidget(campo_nombre)

        # Lista de resultados (oculta por defecto)
        lista = QListWidget()
        lista.setFixedHeight(160)
        lista.setStyleSheet(
            "QListWidget { border:1px solid #A5B4FC; border-radius:5px;"
            "background:white; font-size:11px; }"
            "QListWidget::item { padding:5px 8px; }"
            "QListWidget::item:hover { background:#EEF2FF; }"
            "QListWidget::item:selected { background:#6366F1; color:white; }"
        )
        lista.hide()
        lay.addWidget(lista)

        # Info del producto seleccionado
        lbl_info = QLabel("—  ningún producto seleccionado  —")
        lbl_info.setAlignment(Qt.AlignCenter)
        lbl_info.setWordWrap(True)
        lbl_info.setMinimumHeight(52)
        lbl_info.setStyleSheet(
            f"background:{bg}; border:1px dashed {border}; border-radius:6px;"
            "padding:6px; font-size:12px; color:#374151;"
        )
        lay.addWidget(lbl_info)

        lay.addStretch()

        # Guardar referencias
        setattr(self, f"_cambio_{prefijo}_scanner", campo_scanner)
        setattr(self, f"_cambio_{prefijo}_nombre", campo_nombre)
        setattr(self, f"_cambio_{prefijo}_lista", lista)
        setattr(self, f"_cambio_{prefijo}_info", lbl_info)
        setattr(self, f"_cambio_{prefijo}_producto", None)
        setattr(self, f"_cambio_{prefijo}_matches", [])

        # Conectar señales
        campo_scanner.returnPressed.connect(
            lambda p=prefijo: self._cambio_buscar_por_barras(p)
        )
        campo_nombre.textChanged.connect(
            lambda t, p=prefijo: self._cambio_buscar_por_nombre(p)
        )
        lista.itemClicked.connect(
            lambda item, p=prefijo: self._cambio_on_item_seleccionado(p)
        )
        lista.itemActivated.connect(
            lambda item, p=prefijo: self._cambio_on_item_seleccionado(p)
        )

        return frame

    def _cambio_buscar_por_barras(self, prefijo: str) -> None:
        """Busca el producto del lado `prefijo` usando el código de barras escaneado."""
        scanner: QLineEdit = getattr(self, f"_cambio_{prefijo}_scanner")
        barras = scanner.text().strip()
        if not barras:
            return
        p = next((x for x in self._productos if x.codigo_barras == barras), None)
        self._cambio_mostrar_producto(prefijo, p, barras)

    def _cambio_buscar_por_nombre(self, prefijo: str) -> None:
        """Filtra productos del lado `prefijo` por nombre y muestra sugerencias en lista."""
        campo: QLineEdit = getattr(self, f"_cambio_{prefijo}_nombre")
        lista: QListWidget = getattr(self, f"_cambio_{prefijo}_lista")
        texto = campo.text().strip()

        if len(texto) < 2:
            lista.hide()
            setattr(self, f"_cambio_{prefijo}_matches", [])
            return

        texto_lc = texto.lower()
        coincidencias = [
            p for p in self._productos
            if texto_lc in p.producto.lower()
        ]

        if not coincidencias:
            lista.hide()
            lbl: QLabel = getattr(self, f"_cambio_{prefijo}_info")
            lbl.setText(f"Sin resultados para: '{texto}'")
            setattr(self, f"_cambio_{prefijo}_producto", None)
            setattr(self, f"_cambio_{prefijo}_matches", [])
            return

        if len(coincidencias) == 1:
            lista.hide()
            self._cambio_mostrar_producto(prefijo, coincidencias[0])
            return

        # Múltiples coincidencias → mostrar lista seleccionable
        limite = coincidencias[:12]
        setattr(self, f"_cambio_{prefijo}_matches", limite)
        lista.clear()
        for p in limite:
            txt = f"{p.producto[:50]}  |  T:{p.talla}  |  Stock:{p.cantidad}"
            item = QListWidgetItem(txt)
            item.setToolTip(p.producto)
            lista.addItem(item)
        lista.show()

        lbl = getattr(self, f"_cambio_{prefijo}_info")
        lbl.setText(f"{len(coincidencias)} coincidencias — selecciona de la lista")
        setattr(self, f"_cambio_{prefijo}_producto", None)

    def _cambio_on_item_seleccionado(self, prefijo: str) -> None:
        """Carga el producto elegido de la lista de sugerencias y la oculta."""
        lista: QListWidget = getattr(self, f"_cambio_{prefijo}_lista")
        matches: list = getattr(self, f"_cambio_{prefijo}_matches", [])
        idx = lista.currentRow()
        if 0 <= idx < len(matches):
            self._cambio_mostrar_producto(prefijo, matches[idx])
            lista.hide()
            campo: QLineEdit = getattr(self, f"_cambio_{prefijo}_nombre")
            campo.clear()

    def _cambio_mostrar_producto(
        self, prefijo: str, producto, consulta: str = ""
    ) -> None:
        """Muestra los datos del producto encontrado (o mensaje de error si es None) en el panel `prefijo`."""
        # Ocultar lista si estaba visible
        lista = getattr(self, f"_cambio_{prefijo}_lista", None)
        if lista is not None:
            lista.hide()

        lbl: QLabel = getattr(self, f"_cambio_{prefijo}_info")
        if producto is None:
            lbl.setText(f"No encontrado: '{consulta}'")
            setattr(self, f"_cambio_{prefijo}_producto", None)
            return
        setattr(self, f"_cambio_{prefijo}_producto", producto)
        lbl.setText(
            f"<b>{producto.producto}</b><br>"
            f"Serial: {producto.serial}  ·  Talla: {producto.talla}"
            f"  ·  Stock: {producto.cantidad}"
        )

    def _on_confirmar_cambio(self) -> None:
        """Registra el cambio físico: descuenta el producto que sale y suma el que entra."""
        prod_sale  = getattr(self, "_cambio_sale_producto", None)
        prod_entra = getattr(self, "_cambio_entra_producto", None)

        if prod_sale is None or prod_entra is None:
            QMessageBox.warning(
                self, "Datos incompletos",
                "Debes seleccionar ambos productos para realizar el cambio."
            )
            return

        if prod_sale.id == prod_entra.id:
            QMessageBox.warning(
                self, "Mismo producto",
                "El producto que sale y el que entra son el mismo. Selecciona artículos diferentes."
            )
            return

        if prod_sale.cantidad < 1:
            QMessageBox.warning(
                self, "Sin stock",
                f"'{prod_sale.producto}' no tiene stock disponible para devolver."
            )
            return

        resp = QMessageBox.question(
            self,
            "Confirmar cambio",
            f"¿Confirmar el siguiente cambio?\n\n"
            f"  Sale:   {prod_sale.producto}  (stock: {prod_sale.cantidad} → {prod_sale.cantidad - 1})\n"
            f"  Entra:  {prod_entra.producto}  (stock: {prod_entra.cantidad} → {prod_entra.cantidad + 1})\n",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        from database.inventario_repo import actualizar_cantidad_con_tipo

        # Guardar cantidades originales antes de modificar
        cant_sale_ant  = prod_sale.cantidad
        cant_entra_ant = prod_entra.cantidad

        # Actualizar stock y registrar movimiento tipo "Cambio" (sin doble registro)
        actualizar_cantidad_con_tipo(
            prod_sale.id, prod_sale.producto,
            cant_sale_ant - 1, "Cambio",
            notas=f"Sale en cambio — entra: {prod_entra.producto}",
        )
        actualizar_cantidad_con_tipo(
            prod_entra.id, prod_entra.producto,
            cant_entra_ant + 1, "Cambio",
            notas=f"Entra en cambio — sale: {prod_sale.producto}",
        )

        # Actualizar objetos locales para el mensaje final
        prod_sale.cantidad  = cant_sale_ant - 1
        prod_entra.cantidad = cant_entra_ant + 1

        self.refresh()
        self.inventario_actualizado.emit()

        # Limpiar columnas
        for prefijo in ("sale", "entra"):
            getattr(self, f"_cambio_{prefijo}_scanner").clear()
            getattr(self, f"_cambio_{prefijo}_nombre").clear()
            lbl: QLabel = getattr(self, f"_cambio_{prefijo}_info")
            lbl.setText("—  ningún producto seleccionado  —")
            setattr(self, f"_cambio_{prefijo}_producto", None)

        QMessageBox.information(
            self, "Cambio realizado",
            f"✓ Cambio registrado correctamente.\n\n"
            f"  Sale:   {prod_sale.producto}\n"
            f"  Entra:  {prod_entra.producto}"
        )
