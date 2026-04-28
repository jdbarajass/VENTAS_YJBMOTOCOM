"""
ui/ventas_dia_panel.py
Panel de ventas del día: tabla CRUD + gastos operativos + barra resumen + exportar Excel.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDateEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
    QFrame, QLineEdit, QScrollArea, QComboBox,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

from controllers.ventas_dia_controller import VentasDiaController
from database.config_repo import obtener_configuracion
from ui.edit_venta_dialog import EditVentaDialog
from ui.venta_form import MoneyLineEdit
from utils.formatters import cop, fecha_corta
from models.gasto_dia import CATEGORIAS_GASTO

# Columnas de la tabla (índices)
COL_ID       = 0   # oculto
COL_NUM      = 1
COL_FECHA    = 2
COL_PRODUCTO = 3
COL_CANT     = 4
COL_COSTO    = 5
COL_PRECIO   = 6
COL_METODO   = 7
COL_COMISION = 8
COL_NETA     = 9
COL_NOTAS    = 10
COL_ACCIONES = 11

TOTAL_COLS   = 12


class VentasDiaPanel(QWidget):
    """Vista de ventas del día con tabla, edición, eliminación, gastos operativos y export."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = VentasDiaController()
        self._ventas: list = []
        self._gastos: list = []
        self._build_ui()
        self._cargar_datos()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        root.addLayout(self._barra_superior())
        root.addWidget(self._build_tabla())
        root.addWidget(self._panel_gastos_dia())
        root.addWidget(self._sep())
        root.addLayout(self._barra_resumen())
        root.addWidget(self._panel_metodos_pago())

    def _barra_superior(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Ventas del Día")
        font = QFont(); font.setPointSize(16); font.setBold(True)
        titulo.setFont(font)

        self.date_selector = QDateEdit()
        self.date_selector.setCalendarPopup(True)
        self.date_selector.setDate(QDate.currentDate())
        self.date_selector.setDisplayFormat("dd/MM/yyyy")
        self.date_selector.setFixedHeight(34)
        self.date_selector.setFixedWidth(130)
        self.date_selector.dateChanged.connect(lambda _: self._cargar_datos())

        _nav_style = (
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 12px; background:white; color:#374151; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_prev = QPushButton("< Anterior")
        btn_prev.setFixedHeight(34)
        btn_prev.setStyleSheet(_nav_style)
        btn_prev.clicked.connect(self._dia_anterior)

        btn_next = QPushButton("Siguiente >")
        btn_next.setFixedHeight(34)
        btn_next.setStyleSheet(_nav_style)
        btn_next.clicked.connect(self._dia_siguiente)

        self.btn_hoy = QPushButton("Hoy")
        self.btn_hoy.setFixedHeight(34)
        self.btn_hoy.setFixedWidth(60)
        self.btn_hoy.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        self.btn_hoy.clicked.connect(self._ir_hoy)

        lay.addWidget(titulo)
        lay.addSpacing(16)
        lay.addWidget(btn_prev)
        lay.addWidget(self.date_selector)
        lay.addWidget(btn_next)
        lay.addWidget(self.btn_hoy)
        lay.addStretch()
        return lay

    def _build_tabla(self) -> QTableWidget:
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(TOTAL_COLS)
        self.tabla.setHorizontalHeaderLabels([
            "id", "#", "Fecha", "Producto", "Cant.",
            "Costo", "Precio venta", "Método",
            "Comisión", "Ganancia neta", "Notas", "Acciones"
        ])
        self.tabla.setColumnHidden(COL_ID, True)

        # Comportamiento
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setStyleSheet("""
            QTableWidget { border: none; font-size: 12px; }
            QTableWidget::item { padding: 4px 8px; }
            QHeaderView::section {
                background-color: #1E293B; color: white;
                font-weight: bold; font-size: 11px;
                padding: 6px; border: none;
            }
            QHeaderView::section:hover { background-color: #334155; }
            QTableWidget::item:selected { background-color: #DBEAFE; color: #1E3A5F; }
            QToolTip {
                background: #1E293B; color: #FFFFFF;
                border: 1px solid #475569; padding: 5px 8px;
                font-size: 12px; border-radius: 4px;
            }
        """)

        # Anchos de columna — todas interactivas (el usuario puede deslizar cualquier columna)
        hh = self.tabla.horizontalHeader()
        hh.setSectionResizeMode(COL_NUM,      QHeaderView.Interactive); self.tabla.setColumnWidth(COL_NUM, 64)
        hh.setSectionResizeMode(COL_FECHA,    QHeaderView.Interactive); self.tabla.setColumnWidth(COL_FECHA, 100)
        hh.setSectionResizeMode(COL_PRODUCTO, QHeaderView.Interactive); self.tabla.setColumnWidth(COL_PRODUCTO, 210)
        hh.setSectionResizeMode(COL_CANT,     QHeaderView.Interactive); self.tabla.setColumnWidth(COL_CANT, 52)
        hh.setSectionResizeMode(COL_COSTO,    QHeaderView.Interactive); self.tabla.setColumnWidth(COL_COSTO, 110)
        hh.setSectionResizeMode(COL_PRECIO,   QHeaderView.Interactive); self.tabla.setColumnWidth(COL_PRECIO, 120)
        hh.setSectionResizeMode(COL_METODO,   QHeaderView.Interactive); self.tabla.setColumnWidth(COL_METODO, 130)
        hh.setSectionResizeMode(COL_COMISION, QHeaderView.Interactive); self.tabla.setColumnWidth(COL_COMISION, 105)
        hh.setSectionResizeMode(COL_NETA,     QHeaderView.Interactive); self.tabla.setColumnWidth(COL_NETA, 120)
        hh.setSectionResizeMode(COL_NOTAS,    QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_ACCIONES, QHeaderView.Fixed);       self.tabla.setColumnWidth(COL_ACCIONES, 200)

        return self.tabla

    def _panel_gastos_dia(self) -> QFrame:
        """Panel compacto para registrar gastos operativos del día."""
        frame = QFrame()
        frame.setObjectName("gastosFrame")
        frame.setStyleSheet(
            "QFrame#gastosFrame { background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; }"
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(8)

        # Título
        titulo = QLabel("Gastos Operativos del Día")
        font = QFont(); font.setPointSize(11); font.setBold(True)
        titulo.setFont(font)
        titulo.setStyleSheet("color: #92400E; background: transparent; border: none;")
        layout.addWidget(titulo)

        # Fila de entrada
        fila = QHBoxLayout()
        fila.setSpacing(8)

        self.campo_gasto_desc = QLineEdit()
        self.campo_gasto_desc.setPlaceholderText("Descripción (ej: Aceite motor, Repuesto freno…)")
        self.campo_gasto_desc.setFixedHeight(32)
        self.campo_gasto_desc.setStyleSheet(
            "QLineEdit { border: 1px solid #D1D5DB; border-radius: 5px;"
            "padding: 0 8px; background: white; }"
            "QLineEdit:focus { border: 2px solid #F59E0B; }"
        )

        self.combo_gasto_cat = QComboBox()
        self.combo_gasto_cat.addItems(CATEGORIAS_GASTO)
        self.combo_gasto_cat.setFixedHeight(32)
        self.combo_gasto_cat.setFixedWidth(130)
        self.combo_gasto_cat.setStyleSheet(
            "QComboBox { border: 1px solid #D1D5DB; border-radius: 5px;"
            "padding: 0 8px; background: white; }"
            "QComboBox:focus { border: 2px solid #F59E0B; }"
        )

        self.campo_gasto_monto = MoneyLineEdit()
        self.campo_gasto_monto.setPlaceholderText("0")
        self.campo_gasto_monto.setFixedHeight(32)
        self.campo_gasto_monto.setFixedWidth(130)
        self.campo_gasto_monto.setStyleSheet(
            "QLineEdit { border: 1px solid #D1D5DB; border-radius: 5px;"
            "padding: 0 8px; background: white; }"
            "QLineEdit:focus { border: 2px solid #F59E0B; }"
        )

        btn_agregar = QPushButton("+ Agregar")
        btn_agregar.setFixedHeight(32)
        btn_agregar.setStyleSheet(
            "QPushButton { background: #F59E0B; color: white; border-radius: 5px;"
            "padding: 0 14px; font-weight: bold; border: none; }"
            "QPushButton:hover { background: #D97706; }"
        )
        btn_agregar.clicked.connect(self._on_agregar_gasto)

        fila.addWidget(self.campo_gasto_desc, stretch=3)
        fila.addWidget(self.combo_gasto_cat)
        fila.addWidget(self.campo_gasto_monto)
        fila.addWidget(btn_agregar)
        layout.addLayout(fila)

        # Lista scrollable de gastos
        self._gastos_lista_widget = QWidget()
        self._gastos_lista_widget.setStyleSheet("background: transparent;")
        self._gastos_lista_layout = QVBoxLayout(self._gastos_lista_widget)
        self._gastos_lista_layout.setContentsMargins(0, 0, 0, 0)
        self._gastos_lista_layout.setSpacing(3)

        scroll = QScrollArea()
        scroll.setWidget(self._gastos_lista_widget)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(110)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        layout.addWidget(scroll)

        return frame

    def _barra_resumen(self) -> QHBoxLayout:
        """Barra inferior con métricas del día."""
        lay = QHBoxLayout()
        lay.setSpacing(16)

        self.lbl_cantidad   = self._chip("0 ventas",         "#374151")
        self.lbl_ingresos   = self._chip("Ingresos: $ 0",    "#1D4ED8")
        self.lbl_costos     = self._chip("Costos: $ 0",      "#6B7280")
        self.lbl_comisiones = self._chip("Comisiones: $ 0",  "#92400E")
        self.lbl_neta_total = self._chip("G. neta: $ 0",     "#15803D")
        self.lbl_pct_neta   = self._chip("G.Neta: —",        "#15803D")
        self.lbl_gastos_op  = self._chip("Gastos op.: $ 0",  "#B45309")
        self.lbl_utilidad   = self._chip("Utilidad: $ 0",    "#15803D")
        self.lbl_pct_util   = self._chip("Util: —",          "#374151")

        for lbl in (self.lbl_cantidad, self.lbl_ingresos, self.lbl_costos,
                    self.lbl_comisiones, self.lbl_neta_total, self.lbl_pct_neta,
                    self.lbl_gastos_op, self.lbl_utilidad, self.lbl_pct_util):
            lay.addWidget(lbl)

        lay.addStretch()
        return lay

    def _panel_metodos_pago(self) -> QFrame:
        """Franja con el total de ingresos desglosado por método de pago."""
        frame = QFrame()
        frame.setObjectName("metodosFrame")
        frame.setStyleSheet(
            "QFrame#metodosFrame { background:#F8FAFC; border:1px solid #E2E8F0;"
            "border-radius:6px; }"
        )
        outer = QHBoxLayout(frame)
        outer.setContentsMargins(12, 6, 12, 6)
        outer.setSpacing(0)

        lbl_titulo = QLabel("Por método de pago:")
        lbl_titulo.setStyleSheet(
            "color:#64748B; font-size:11px; font-weight:bold;"
            "background:transparent; border:none;"
        )
        outer.addWidget(lbl_titulo)
        outer.addSpacing(10)

        # Layout dinámico donde se insertan los chips por método
        self._lay_metodos = QHBoxLayout()
        self._lay_metodos.setSpacing(10)
        outer.addLayout(self._lay_metodos)
        outer.addStretch()

        # Inicializar con mensaje vacío
        self._lbl_sin_ventas = QLabel("Sin ventas registradas para esta fecha.")
        self._lbl_sin_ventas.setStyleSheet(
            "color:#94A3B8; font-size:11px; background:transparent; border:none;"
        )
        self._lay_metodos.addWidget(self._lbl_sin_ventas)

        return frame

    def _chip(self, texto: str, color: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 12px;"
            f"background: #F1F5F9; border-radius: 4px; padding: 4px 10px;"
        )
        return lbl

    def _sep(self) -> QFrame:
        s = QFrame(); s.setFrameShape(QFrame.HLine)
        s.setStyleSheet("color: #E5E7EB;")
        return s

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------

    def _cargar_datos(self) -> None:
        """Recarga la tabla con las ventas y gastos de la fecha seleccionada."""
        qd = self.date_selector.date()
        fecha = date(qd.year(), qd.month(), qd.day())
        self._ventas = self._ctrl.cargar_ventas(fecha)
        self._gastos = self._ctrl.cargar_gastos(fecha)
        self._poblar_tabla()
        self._poblar_gastos()
        self._actualizar_resumen()

    def _poblar_tabla(self) -> None:
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(self._ventas))

        # --- Indicador visual de carrito (grupo_venta_id) ---
        # Paleta de fondos suaves para distinguir grupos distintos
        _GRUPO_COLORES = [
            QColor("#DBEAFE"),  # azul
            QColor("#FCE7F3"),  # rosa
            QColor("#D1FAE5"),  # verde
            QColor("#EDE9FE"),  # violeta
            QColor("#FEF3C7"),  # ámbar
        ]
        # Lista ordenada de grupo_ids únicos presentes hoy
        grupo_ids: list[int] = []
        for v in self._ventas:
            gid = getattr(v, "grupo_venta_id", None)
            if gid is not None and gid not in grupo_ids:
                grupo_ids.append(gid)
        # Cuenta de items por grupo (para badge "1/2", "2/2", etc.)
        grupo_counts: dict[int, int] = {}
        for v in self._ventas:
            gid = getattr(v, "grupo_venta_id", None)
            if gid is not None:
                grupo_counts[gid] = grupo_counts.get(gid, 0) + 1
        grupo_cursor: dict[int, int] = {}  # posición actual dentro del grupo

        for row, v in enumerate(self._ventas):
            self.tabla.setRowHeight(row, 36)

            gid = getattr(v, "grupo_venta_id", None)
            color_grupo: QColor | None = None
            if gid is not None:
                color_grupo = _GRUPO_COLORES[grupo_ids.index(gid) % len(_GRUPO_COLORES)]
                grupo_cursor[gid] = grupo_cursor.get(gid, 0) + 1

            self._celda(row, COL_ID, str(v.id), Qt.AlignCenter)

            # Columna # — agrega badge "pos/total" si la venta pertenece a un carrito
            if gid is not None:
                pos   = grupo_cursor[gid]
                total = grupo_counts[gid]
                num_text = f"{row + 1}  [{pos}/{total}]"
            else:
                num_text = str(row + 1)
            self._celda(row, COL_NUM, num_text, Qt.AlignCenter)

            self._celda(row, COL_FECHA,    fecha_corta(v.fecha), Qt.AlignCenter)
            # Producto con tooltip
            item_prod = QTableWidgetItem(v.producto)
            item_prod.setToolTip(v.producto)
            self.tabla.setItem(row, COL_PRODUCTO, item_prod)
            self._celda(row, COL_CANT,     str(v.cantidad),      Qt.AlignCenter)
            self._celda(row, COL_COSTO,    cop(v.costo),         Qt.AlignRight | Qt.AlignVCenter)
            self._celda(row, COL_PRECIO,   cop(v.precio),        Qt.AlignRight | Qt.AlignVCenter)
            item_met = QTableWidgetItem(v.metodo_pago)
            item_met.setTextAlignment(Qt.AlignCenter)
            if v.pagos_combinados:
                from utils.formatters import cop as _cop
                detalle = "  |  ".join(
                    f"{p['metodo']}: {_cop(p['monto'])}" for p in v.pagos_combinados
                )
                item_met.setToolTip(detalle)
            self.tabla.setItem(row, COL_METODO, item_met)
            self._celda(row, COL_COMISION, cop(v.comision),      Qt.AlignRight | Qt.AlignVCenter)

            # Ganancia neta con color
            item_neta = QTableWidgetItem(cop(v.ganancia_neta))
            item_neta.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if v.ganancia_neta >= 0:
                item_neta.setForeground(QColor("#16A34A"))
            else:
                item_neta.setForeground(QColor("#DC2626"))
            self.tabla.setItem(row, COL_NETA, item_neta)

            self._celda(row, COL_NOTAS, v.notas or "")

            # Aplicar fondo de grupo a todas las celdas (excluye la celda de botones)
            if color_grupo is not None:
                for col in range(COL_ACCIONES):
                    item = self.tabla.item(row, col)
                    if item:
                        item.setBackground(color_grupo)

            # Botones de acción
            self.tabla.setCellWidget(row, COL_ACCIONES, self._widget_acciones(v.id))

    def _poblar_gastos(self) -> None:
        """Actualiza la lista visual de gastos operativos."""
        while self._gastos_lista_layout.count():
            item = self._gastos_lista_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._gastos:
            lbl = QLabel("Sin gastos operativos registrados para este día.")
            lbl.setStyleSheet(
                "color: #9CA3AF; font-size: 11px; background: transparent; border: none;"
            )
            self._gastos_lista_layout.addWidget(lbl)
            return

        # Colores por categoría
        _CAT_COLOR = {
            "Transporte":   ("#DBEAFE", "#1D4ED8"),
            "Alimentación": ("#DCFCE7", "#15803D"),
            "Insumos":      ("#FEF3C7", "#92400E"),
            "Banco":        ("#EDE9FE", "#6D28D9"),
            "Otro":         ("#F3F4F6", "#374151"),
        }

        for g in self._gastos:
            fila = QWidget()
            fila.setStyleSheet(
                "QWidget { background: white; border-radius: 4px; border: none; }"
            )
            lay = QHBoxLayout(fila)
            lay.setContentsMargins(8, 3, 8, 3)
            lay.setSpacing(8)

            # Chip de categoría
            cat_bg, cat_fg = _CAT_COLOR.get(g.categoria, ("#F3F4F6", "#374151"))
            lbl_cat = QLabel(g.categoria)
            lbl_cat.setStyleSheet(
                f"background: {cat_bg}; color: {cat_fg}; border-radius: 4px;"
                "font-size: 10px; font-weight: bold; padding: 1px 6px; border: none;"
            )
            lbl_cat.setFixedWidth(90)
            lbl_cat.setAlignment(Qt.AlignCenter)

            lbl_desc = QLabel(g.descripcion)
            lbl_desc.setStyleSheet("background: transparent; border: none; color: #374151;")

            lbl_monto = QLabel(cop(g.monto))
            lbl_monto.setStyleSheet(
                "background: transparent; border: none; color: #DC2626; font-weight: bold;"
            )
            lbl_monto.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            btn_del = QPushButton("🗑")
            btn_del.setFixedSize(24, 24)
            btn_del.setStyleSheet(
                "QPushButton { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA;"
                "border-radius: 4px; font-size: 11px; }"
                "QPushButton:hover { background: #FEE2E2; }"
            )
            btn_del.clicked.connect(lambda _, gid=g.id: self._on_eliminar_gasto(gid))

            lay.addWidget(lbl_cat)
            lay.addWidget(lbl_desc, stretch=3)
            lay.addWidget(lbl_monto, stretch=1)
            lay.addWidget(btn_del)

            self._gastos_lista_layout.addWidget(fila)

    def _celda(self, row: int, col: int, texto: str,
               alineacion: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alineacion)
        if texto:
            item.setToolTip(texto)
        self.tabla.setItem(row, col, item)

    def _widget_acciones(self, venta_id: int) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(4)

        btn_editar = QPushButton("Editar")
        btn_editar.setFixedHeight(26)
        btn_editar.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn_editar.clicked.connect(lambda _, vid=venta_id: self._on_editar(vid))

        btn_recibo = QPushButton("Recibo")
        btn_recibo.setFixedHeight(26)
        btn_recibo.setToolTip("Generar e imprimir recibo PDF")
        btn_recibo.setStyleSheet(
            "QPushButton { background:#F0FDF4; color:#15803D; border:1px solid #BBF7D0;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
            "QPushButton:hover { background:#DCFCE7; }"
        )
        btn_recibo.clicked.connect(lambda _, vid=venta_id: self._on_imprimir_recibo(vid))

        btn_eliminar = QPushButton("Borrar")
        btn_eliminar.setFixedHeight(26)
        btn_eliminar.setStyleSheet(
            "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 8px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn_eliminar.clicked.connect(lambda _, vid=venta_id: self._on_eliminar(vid))

        lay.addWidget(btn_editar)
        lay.addWidget(btn_recibo)
        lay.addWidget(btn_eliminar)
        return w

    def _actualizar_resumen(self) -> None:
        n          = sum(v.cantidad for v in self._ventas)
        ingresos   = sum(v.precio * v.cantidad for v in self._ventas)
        costos     = sum(v.costo * v.cantidad for v in self._ventas)
        comisiones = sum(v.comision for v in self._ventas)
        neta       = sum(v.ganancia_neta for v in self._ventas)
        gastos_op  = sum(g.monto for g in self._gastos)
        cfg        = obtener_configuracion()
        utilidad   = round(neta - gastos_op - cfg.gasto_diario, 2)

        pct_neta = round(neta / ingresos * 100, 1) if ingresos > 0 else 0.0
        pct_util = round(utilidad / ingresos * 100, 1) if ingresos > 0 else 0.0

        self.lbl_cantidad.setText(f"{n} venta{'s' if n != 1 else ''}")
        self.lbl_ingresos.setText(f"Ingresos: {cop(ingresos)}")
        self.lbl_costos.setText(f"Costos: {cop(costos)}")
        self.lbl_comisiones.setText(f"Comisiones: {cop(comisiones)}")
        self.lbl_neta_total.setText(f"G. neta: {cop(neta)}")
        self.lbl_pct_neta.setText(f"G.Neta: {pct_neta:+.1f}%")
        self.lbl_gastos_op.setText(f"Gastos op.: {cop(gastos_op)}")
        self.lbl_utilidad.setText(f"Utilidad: {cop(utilidad)}")
        self.lbl_pct_util.setText(f"Util: {pct_util:+.1f}%")

        color_neta = "#15803D" if neta >= 0 else "#DC2626"
        self.lbl_neta_total.setStyleSheet(
            f"color: {color_neta}; font-weight: bold; font-size: 12px;"
            f"background: #F1F5F9; border-radius: 4px; padding: 4px 10px;"
        )
        color_pct_neta = "#15803D" if pct_neta >= 20 else ("#D97706" if pct_neta >= 10 else "#DC2626")
        self.lbl_pct_neta.setStyleSheet(
            f"color: {color_pct_neta}; font-weight: bold; font-size: 12px;"
            f"background: #F1F5F9; border-radius: 4px; padding: 4px 10px;"
        )
        color_util = "#15803D" if utilidad >= 0 else "#DC2626"
        self.lbl_utilidad.setStyleSheet(
            f"color: {color_util}; font-weight: bold; font-size: 12px;"
            f"background: #F1F5F9; border-radius: 4px; padding: 4px 10px;"
        )
        color_pct_util = "#15803D" if pct_util >= 10 else ("#D97706" if pct_util >= 0 else "#DC2626")
        self.lbl_pct_util.setStyleSheet(
            f"color: {color_pct_util}; font-weight: bold; font-size: 12px;"
            f"background: #F1F5F9; border-radius: 4px; padding: 4px 10px;"
        )

        # Totales por metodo de pago (expandiendo pagos combinados)
        from controllers.dashboard_controller import _expandir_metodos
        self._actualizar_metodos(_expandir_metodos(self._ventas))

    def _actualizar_metodos(self, totales: dict) -> None:
        """Reemplaza los chips de métodos de pago con los datos actuales."""
        # Limpiar chips anteriores
        while self._lay_metodos.count():
            item = self._lay_metodos.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not totales:
            self._lbl_sin_ventas = QLabel("Sin ventas registradas para esta fecha.")
            self._lbl_sin_ventas.setStyleSheet(
                "color:#94A3B8; font-size:11px; background:transparent; border:none;"
            )
            self._lay_metodos.addWidget(self._lbl_sin_ventas)
            return

        # Colores por metodo (los sub-tipos de transferencia heredan el color azul)
        _COLORES = {
            "Efectivo":               ("#DCFCE7", "#15803D"),
            "Addi":                   ("#EDE9FE", "#6D28D9"),
            "Transferencia":          ("#DBEAFE", "#1D4ED8"),
            "Transferencia NU":       ("#DBEAFE", "#1D4ED8"),
            "Transferencia QR":       ("#E0F2FE", "#0369A1"),
            "Transferencia NEQUI":    ("#EFF6FF", "#2563EB"),
            "Transferencia DAVIPLATA":("#F0F9FF", "#0284C7"),
            "Otro":                   ("#F3F4F6", "#374151"),
        }

        for metodo, total in sorted(totales.items()):
            bg, fg = _COLORES.get(metodo, ("#DBEAFE", "#1D4ED8") if "Transferencia" in metodo else ("#F3F4F6", "#374151"))
            lbl = QLabel(f"{metodo}: {cop(total)}")
            lbl.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:4px;"
                f"font-size:11px; font-weight:bold; padding:3px 10px;"
            )
            self._lay_metodos.addWidget(lbl)

    # ------------------------------------------------------------------
    # Acciones CRUD — ventas
    # ------------------------------------------------------------------

    def _on_editar(self, venta_id: int) -> None:
        venta = next((v for v in self._ventas if v.id == venta_id), None)
        if not venta:
            return
        dialog = EditVentaDialog(venta, self)
        dialog.venta_actualizada.connect(lambda _: self._cargar_datos())
        dialog.exec()

    def _on_eliminar(self, venta_id: int) -> None:
        venta = next((v for v in self._ventas if v.id == venta_id), None)
        nombre = venta.producto if venta else f"id {venta_id}"

        resp = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Eliminar la venta de <b>{nombre}</b>?<br>"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self._ctrl.eliminar(venta_id)
            self._cargar_datos()

    def _on_imprimir_recibo(self, venta_id: int) -> None:
        """Genera el PDF del recibo y lo abre con el visor predeterminado."""
        venta = next((v for v in self._ventas if v.id == venta_id), None)
        if not venta:
            return
        try:
            from services.recibo_generator import generar_recibo
            from utils.pdf_utils import abrir_pdf
            path = generar_recibo(venta)
            abrir_pdf(path)
        except Exception as exc:
            QMessageBox.warning(
                self, "Error al generar recibo",
                f"No se pudo generar el PDF:\n{exc}"
            )

    # ------------------------------------------------------------------
    # Acciones CRUD — gastos operativos
    # ------------------------------------------------------------------

    def _on_agregar_gasto(self) -> None:
        descripcion = self.campo_gasto_desc.text().strip()
        monto = self.campo_gasto_monto.valor_int()
        categoria = self.combo_gasto_cat.currentText()

        if not descripcion:
            QMessageBox.warning(self, "Dato requerido",
                                "Ingresa una descripción para el gasto.")
            self.campo_gasto_desc.setFocus()
            return
        if monto <= 0:
            QMessageBox.warning(self, "Dato inválido",
                                "El monto debe ser mayor a cero.")
            self.campo_gasto_monto.setFocus()
            return

        qd = self.date_selector.date()
        fecha = date(qd.year(), qd.month(), qd.day())

        try:
            self._ctrl.agregar_gasto(descripcion, float(monto), fecha, categoria)
            self.campo_gasto_desc.clear()
            self.campo_gasto_monto.clear()
            self._gastos = self._ctrl.cargar_gastos(fecha)
            self._poblar_gastos()
            self._actualizar_resumen()
        except ValueError as exc:
            QMessageBox.warning(self, "Error", str(exc))

    def _on_eliminar_gasto(self, gasto_id: int) -> None:
        self._ctrl.eliminar_gasto(gasto_id)
        qd = self.date_selector.date()
        fecha = date(qd.year(), qd.month(), qd.day())
        self._gastos = self._ctrl.cargar_gastos(fecha)
        self._poblar_gastos()
        self._actualizar_resumen()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Recarga la tabla. Llamado desde MainWindow tras registrar una venta."""
        self._cargar_datos()

    def _ir_hoy(self) -> None:
        self.date_selector.setDate(QDate.currentDate())

    def _dia_anterior(self) -> None:
        self.date_selector.setDate(self.date_selector.date().addDays(-1))

    def _dia_siguiente(self) -> None:
        self.date_selector.setDate(self.date_selector.date().addDays(1))
