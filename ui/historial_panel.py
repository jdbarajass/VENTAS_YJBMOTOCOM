"""
ui/historial_panel.py
Historial mensual: tarjetas de resumen + tabla diaria + tabla detalle ventas.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QSizePolicy,
    QMessageBox, QLineEdit,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from controllers.historial_controller import HistorialController
from controllers.venta_controller import VentaController
from services.reportes import ResumenMensual
from utils.formatters import cop, fecha_corta, MESES_ES
from models.venta import Venta


class HistorialPanel(QWidget):
    """Vista de historial mensual completa."""

    venta_modificada = Signal()   # emitido al editar o eliminar una venta

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = HistorialController()
        self._venta_ctrl = VentaController()
        self._resumen: ResumenMensual | None = None
        self._ventas: list[Venta] = []
        self._fecha_seleccionada: date | None = None
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(14)

        root.addLayout(self._barra_superior())
        root.addLayout(self._fila_resumen())
        root.addWidget(self._panel_resumen_diario())
        root.addWidget(self._panel_detalle_dia(), stretch=1)

    # ---- Barra superior ----

    def _barra_superior(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Historial Mensual")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)

        self.combo_mes = QComboBox()
        self.combo_mes.setFixedHeight(34)
        self.combo_mes.setFixedWidth(115)
        for num, nombre in MESES_ES.items():
            self.combo_mes.addItem(nombre, num)
        self.combo_mes.setCurrentIndex(date.today().month - 1)

        self.spin_año = QSpinBox()
        self.spin_año.setRange(2020, 2040)
        self.spin_año.setValue(date.today().year)
        self.spin_año.setFixedHeight(34)
        self.spin_año.setFixedWidth(75)
        self.spin_año.setButtonSymbols(QSpinBox.NoButtons)

        btn_prev = self._btn_nav("< Anterior")
        btn_next = self._btn_nav("Siguiente >")
        btn_prev.clicked.connect(self._mes_anterior)
        btn_next.clicked.connect(self._mes_siguiente)

        self.combo_mes.currentIndexChanged.connect(lambda _: self.refresh())
        self.spin_año.valueChanged.connect(lambda _: self.refresh())

        lay.addWidget(titulo)
        lay.addSpacing(12)
        lay.addWidget(btn_prev)
        lay.addWidget(self.combo_mes)
        lay.addWidget(self.spin_año)
        lay.addWidget(btn_next)
        lay.addStretch()
        return lay

    def _btn_nav(self, texto: str) -> QPushButton:
        btn = QPushButton(texto)
        btn.setFixedHeight(34)
        btn.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px;"
            "background:white; color:#374151; padding:0 10px; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        return btn

    # ---- Tarjetas de resumen ----

    def _fila_resumen(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(12)

        self.card_ventas    = self._tarjeta("Ventas del mes",        "0",   "#1D4ED8")
        self.card_ingresos  = self._tarjeta("Ingresos totales",      "$ 0", "#374151")
        self.card_g_neta    = self._tarjeta("Ganancia neta",         "$ 0", "#374151")
        self.card_utilidad  = self._tarjeta("Utilidad real del mes", "$ 0", "#374151")
        self.card_positivos = self._tarjeta("Días positivos",        "0",   "#15803D")
        self.card_negativos = self._tarjeta("Días negativos",        "0",   "#DC2626")

        for c in (self.card_ventas, self.card_ingresos, self.card_g_neta,
                  self.card_utilidad, self.card_positivos, self.card_negativos):
            lay.addWidget(c)
        return lay

    def _tarjeta(self, titulo: str, valor: str, color: str) -> QFrame:
        w = QFrame()
        w.setFrameShape(QFrame.StyledPanel)
        w.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:8px; }"
        )
        w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)

        lbl_t = QLabel(titulo.upper())
        lbl_t.setStyleSheet("color:#9CA3AF; font-size:9px; font-weight:bold;")
        lbl_v = QLabel(valor)
        f = QFont(); f.setPointSize(16); f.setBold(True)
        lbl_v.setFont(f)
        lbl_v.setStyleSheet(f"color: {color};")
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_v)

        w._lbl_valor = lbl_v
        w._color_base = color
        return w

    # ---- Tabla resumen por día (reemplaza gráfica) ----

    def _panel_resumen_diario(self) -> QFrame:
        """
        Tabla compacta con un fila por día trabajado.
        Mucho más fácil de leer que una gráfica de barras.
        """
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)

        encabezado = QLabel("  Resumen por Día")
        f = QFont(); f.setPointSize(11); f.setBold(True)
        encabezado.setFont(f)
        encabezado.setContentsMargins(16, 10, 16, 4)
        lay.addWidget(encabezado)

        self.tabla_diaria = QTableWidget()
        self.tabla_diaria.setColumnCount(7)
        self.tabla_diaria.setHorizontalHeaderLabels([
            "Fecha", "Ventas", "Ingresos", "G. Neta", "Gastos op.", "Utilidad", "Estado"
        ])
        self.tabla_diaria.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_diaria.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_diaria.verticalHeader().setVisible(False)
        self.tabla_diaria.setShowGrid(False)
        self.tabla_diaria.setAlternatingRowColors(True)
        self.tabla_diaria.setMaximumHeight(200)
        self.tabla_diaria.setStyleSheet("""
            QTableWidget { border:none; font-size:12px; }
            QTableWidget::item { padding:3px 8px; }
            QHeaderView::section {
                background:#334155; color:white; font-weight:bold;
                font-size:11px; padding:5px; border:none;
            }
            QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }
        """)

        hh = self.tabla_diaria.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Interactive); self.tabla_diaria.setColumnWidth(0, 90)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); self.tabla_diaria.setColumnWidth(1, 55)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); self.tabla_diaria.setColumnWidth(2, 115)
        hh.setSectionResizeMode(3, QHeaderView.Interactive); self.tabla_diaria.setColumnWidth(3, 110)
        hh.setSectionResizeMode(4, QHeaderView.Interactive); self.tabla_diaria.setColumnWidth(4, 110)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        hh.setSectionResizeMode(6, QHeaderView.Interactive); self.tabla_diaria.setColumnWidth(6, 90)

        self.tabla_diaria.setCursor(Qt.PointingHandCursor)
        self.tabla_diaria.cellClicked.connect(self._on_dia_seleccionado)
        lay.addWidget(self.tabla_diaria)
        return frame

    # ---- Panel detalle del día ----

    def _panel_detalle_dia(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)

        # ---- Header con título y botón cerrar ----
        header_bar = QWidget()
        header_bar.setStyleSheet("background:transparent;")
        hb_lay = QHBoxLayout(header_bar)
        hb_lay.setContentsMargins(16, 10, 10, 4)
        hb_lay.setSpacing(8)

        self._lbl_detalle_titulo = QLabel("  Detalle del Día")
        f = QFont(); f.setPointSize(11); f.setBold(True)
        self._lbl_detalle_titulo.setFont(f)

        # Campo de búsqueda global por producto (filtra todo el mes)
        self._campo_busqueda_hist = QLineEdit()
        self._campo_busqueda_hist.setPlaceholderText("Buscar producto en el mes…")
        self._campo_busqueda_hist.setFixedHeight(28)
        self._campo_busqueda_hist.setFixedWidth(230)
        self._campo_busqueda_hist.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 8px; background:white; font-size:11px; }"
            "QLineEdit:focus { border:2px solid #2563EB; }"
        )
        self._campo_busqueda_hist.textChanged.connect(self._on_busqueda_hist)

        self._btn_cerrar_detalle = QPushButton("✕ Cerrar")
        self._btn_cerrar_detalle.setFixedHeight(26)
        self._btn_cerrar_detalle.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:4px;"
            "background:white; color:#6B7280; padding:0 10px; font-size:11px; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        self._btn_cerrar_detalle.clicked.connect(self._cerrar_detalle)
        self._btn_cerrar_detalle.setVisible(False)

        hb_lay.addWidget(self._lbl_detalle_titulo)
        hb_lay.addStretch()
        hb_lay.addWidget(self._campo_busqueda_hist)
        hb_lay.addSpacing(8)
        hb_lay.addWidget(self._btn_cerrar_detalle)
        lay.addWidget(header_bar)

        # ---- Placeholder ----
        self._lbl_placeholder = QLabel("← Haz clic en un día del Resumen para ver sus ventas")
        self._lbl_placeholder.setAlignment(Qt.AlignCenter)
        self._lbl_placeholder.setStyleSheet(
            "color:#9CA3AF; font-size:13px; padding:30px; background:transparent;"
        )
        lay.addWidget(self._lbl_placeholder)

        # ---- Tabla detalle (oculta inicialmente) ----
        self.tabla_detalle = QTableWidget()
        self.tabla_detalle.setColumnCount(10)
        self.tabla_detalle.setHorizontalHeaderLabels([
            "Producto", "Cant.", "Costo", "Precio de Venta", "Método", "G. Neta", "Margen %", "Notas", "✎", "🗑"
        ])
        self.tabla_detalle.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla_detalle.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_detalle.setAlternatingRowColors(True)
        self.tabla_detalle.verticalHeader().setVisible(False)
        self.tabla_detalle.setShowGrid(False)
        self.tabla_detalle.setStyleSheet("""
            QTableWidget { border:none; font-size:12px; }
            QTableWidget::item { padding:3px 8px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:11px; padding:5px; border:none;
            }
            QHeaderView::section:hover { background:#334155; }
            QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }
            QToolTip {
                background:#1E293B; color:#FFFFFF;
                border:1px solid #475569; padding:5px 8px;
                font-size:12px; border-radius:4px;
            }
        """)

        hh = self.tabla_detalle.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Interactive); self.tabla_detalle.setColumnWidth(0, 180)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); self.tabla_detalle.setColumnWidth(1, 50)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); self.tabla_detalle.setColumnWidth(2, 90)
        hh.setSectionResizeMode(3, QHeaderView.Interactive); self.tabla_detalle.setColumnWidth(3, 110)
        hh.setSectionResizeMode(4, QHeaderView.Interactive); self.tabla_detalle.setColumnWidth(4, 120)
        hh.setSectionResizeMode(5, QHeaderView.Interactive); self.tabla_detalle.setColumnWidth(5, 100)
        hh.setSectionResizeMode(6, QHeaderView.Fixed);       self.tabla_detalle.setColumnWidth(6, 80)
        # Notas: ocupa el espacio restante
        hh.setSectionResizeMode(7, QHeaderView.Stretch)
        hh.setSectionResizeMode(8, QHeaderView.Fixed);       self.tabla_detalle.setColumnWidth(8, 68)
        hh.setSectionResizeMode(9, QHeaderView.Fixed);       self.tabla_detalle.setColumnWidth(9, 68)

        self.tabla_detalle.setVisible(False)
        lay.addWidget(self.tabla_detalle, stretch=1)
        return frame

    # ------------------------------------------------------------------
    # Datos
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        mes = self.combo_mes.currentData()
        año = self.spin_año.value()
        self._resumen = self._ctrl.cargar_resumen_mes(año, mes)
        self._ventas  = self._ctrl.cargar_ventas_mes(año, mes)
        self._actualizar_ui()

    def _actualizar_ui(self) -> None:
        r = self._resumen
        if r is None:
            return

        # ---- Tarjetas ----
        self.card_ventas._lbl_valor.setText(str(r.cantidad_ventas))
        self.card_ingresos._lbl_valor.setText(cop(r.total_ingresos))

        color_neta = "#16A34A" if r.ganancia_neta >= 0 else "#DC2626"
        self.card_g_neta._lbl_valor.setText(cop(r.ganancia_neta))
        self.card_g_neta._lbl_valor.setStyleSheet(
            f"color:{color_neta}; font-size:16px; font-weight:bold;"
        )

        color_util = "#16A34A" if r.utilidad_real >= 0 else "#DC2626"
        self.card_utilidad._lbl_valor.setText(cop(r.utilidad_real))
        self.card_utilidad._lbl_valor.setStyleSheet(
            f"color:{color_util}; font-size:16px; font-weight:bold;"
        )

        self.card_positivos._lbl_valor.setText(str(r.dias_positivos))
        self.card_negativos._lbl_valor.setText(str(r.dias_negativos))

        # ---- Tabla diaria ----
        self.tabla_diaria.setRowCount(len(r.resumen_por_dia))
        for row, rd in enumerate(r.resumen_por_dia):
            self.tabla_diaria.setRowHeight(row, 28)
            self._celda_d(row, 0, fecha_corta(rd.fecha), Qt.AlignCenter)
            self._celda_d(row, 1, str(rd.cantidad_ventas), Qt.AlignCenter)
            self._celda_d(row, 2, cop(rd.total_ingresos), Qt.AlignRight | Qt.AlignVCenter)

            item_gn = QTableWidgetItem(cop(rd.ganancia_neta))
            item_gn.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_gn.setForeground(QColor("#16A34A") if rd.ganancia_neta >= 0 else QColor("#DC2626"))
            self.tabla_diaria.setItem(row, 3, item_gn)

            gop_txt = cop(rd.gastos_operativos) if rd.gastos_operativos > 0 else "—"
            self._celda_d(row, 4, gop_txt, Qt.AlignRight | Qt.AlignVCenter)

            item_ut = QTableWidgetItem(cop(rd.utilidad_real))
            item_ut.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_ut.setForeground(QColor("#16A34A") if rd.utilidad_real >= 0 else QColor("#DC2626"))
            self.tabla_diaria.setItem(row, 5, item_ut)

            estado_txt = "Positivo" if rd.es_positivo else "Negativo"
            item_est = QTableWidgetItem(estado_txt)
            item_est.setTextAlignment(Qt.AlignCenter)
            item_est.setForeground(QColor("#15803D") if rd.es_positivo else QColor("#DC2626"))
            self.tabla_diaria.setItem(row, 6, item_est)

        # ---- Refrescar detalle si había un día seleccionado ----
        if self._fecha_seleccionada is not None:
            ventas_dia = [v for v in self._ventas if v.fecha == self._fecha_seleccionada]
            if ventas_dia:
                self._poblar_detalle(ventas_dia, self._fecha_seleccionada)
            else:
                self._cerrar_detalle()

    # ------------------------------------------------------------------
    # Helpers de celda
    # ------------------------------------------------------------------

    def _celda_d(self, row: int, col: int, texto: str,
                 alin: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alin)
        self.tabla_diaria.setItem(row, col, item)

    def _celda_det(self, row: int, col: int, texto: str,
                   alin: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alin)
        self.tabla_detalle.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Detalle del día
    # ------------------------------------------------------------------

    def _on_dia_seleccionado(self, row: int, col: int) -> None:
        if self._resumen is None or row >= len(self._resumen.resumen_por_dia):
            return
        rd = self._resumen.resumen_por_dia[row]
        self._fecha_seleccionada = rd.fecha
        ventas_dia = [v for v in self._ventas if v.fecha == rd.fecha]
        self._poblar_detalle(ventas_dia, rd.fecha)

    def _poblar_detalle(self, ventas: list, fecha: date) -> None:
        self._lbl_placeholder.setVisible(False)
        self.tabla_detalle.setVisible(True)
        self._btn_cerrar_detalle.setVisible(True)
        self._lbl_detalle_titulo.setText(
            f"  Ventas del {fecha_corta(fecha)}  —  {len(ventas)} venta(s)"
        )
        self.tabla_detalle.setRowCount(len(ventas))
        for row, v in enumerate(ventas):
            self.tabla_detalle.setRowHeight(row, 32)

            # Producto — con tooltip para ver nombre completo al posar el mouse
            item_prod = QTableWidgetItem(v.producto)
            item_prod.setToolTip(v.producto)
            self.tabla_detalle.setItem(row, 0, item_prod)

            self._celda_det(row, 1, str(v.cantidad), Qt.AlignCenter)

            # Costo unitario
            self._celda_det(row, 2, cop(v.costo), Qt.AlignRight | Qt.AlignVCenter)

            # Precio de Venta
            self._celda_det(row, 3, cop(v.precio), Qt.AlignRight | Qt.AlignVCenter)

            item_met = QTableWidgetItem(v.metodo_pago)
            item_met.setTextAlignment(Qt.AlignCenter)
            if v.pagos_combinados:
                from utils.formatters import cop as _cop
                detalle = "  |  ".join(
                    f"{p['metodo']}: {_cop(p['monto'])}" for p in v.pagos_combinados
                )
                item_met.setToolTip(detalle)
            self.tabla_detalle.setItem(row, 4, item_met)

            item_gn = QTableWidgetItem(cop(v.ganancia_neta))
            item_gn.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_gn.setForeground(
                QColor("#16A34A") if v.ganancia_neta >= 0 else QColor("#DC2626")
            )
            self.tabla_detalle.setItem(row, 5, item_gn)

            # Margen %
            ingresos = v.precio * v.cantidad
            if ingresos > 0:
                margen = round(v.ganancia_neta / ingresos * 100, 1)
                margen_txt = f"{margen:+.1f}%"
                margen_color = (
                    QColor("#15803D") if margen >= 20 else
                    QColor("#D97706") if margen >= 10 else
                    QColor("#DC2626")
                )
            else:
                margen_txt = "—"
                margen_color = QColor("#9CA3AF")
            item_margen = QTableWidgetItem(margen_txt)
            item_margen.setTextAlignment(Qt.AlignCenter)
            item_margen.setForeground(margen_color)
            self.tabla_detalle.setItem(row, 6, item_margen)

            self._celda_det(row, 7, v.notas or "")
            self.tabla_detalle.setCellWidget(row, 8, self._btn_editar(v.id))
            self.tabla_detalle.setCellWidget(row, 9, self._btn_eliminar(v.id))

    def _on_busqueda_hist(self, texto: str) -> None:
        """Filtra la tabla de detalle por nombre de producto en todo el mes."""
        texto = texto.strip().lower()
        if not texto:
            # Sin texto: revertir a vista del día seleccionado (o placeholder)
            if self._fecha_seleccionada is not None:
                ventas_dia = [v for v in self._ventas if v.fecha == self._fecha_seleccionada]
                self._poblar_detalle(ventas_dia, self._fecha_seleccionada)
            else:
                self.tabla_detalle.setVisible(False)
                self._lbl_placeholder.setVisible(True)
                self._btn_cerrar_detalle.setVisible(False)
                self._lbl_detalle_titulo.setText("  Detalle del Día")
            return

        # Con texto: buscar en todo el mes
        coincidencias = [v for v in self._ventas if texto in v.producto.lower()]
        mes = self.combo_mes.currentData()
        año = self.spin_año.value()
        from utils.formatters import MESES_ES
        lbl_mes = MESES_ES.get(mes, "")
        self._lbl_placeholder.setVisible(False)
        self.tabla_detalle.setVisible(True)
        self._btn_cerrar_detalle.setVisible(True)
        self._lbl_detalle_titulo.setText(
            f"  Búsqueda en {lbl_mes} {año}  —  {len(coincidencias)} resultado(s)"
        )
        self.tabla_detalle.setRowCount(len(coincidencias))
        for row, v in enumerate(coincidencias):
            self.tabla_detalle.setRowHeight(row, 32)
            item_prod = QTableWidgetItem(v.producto)
            item_prod.setToolTip(v.producto)
            self.tabla_detalle.setItem(row, 0, item_prod)
            self._celda_det(row, 1, str(v.cantidad), Qt.AlignCenter)
            self._celda_det(row, 2, cop(v.costo), Qt.AlignRight | Qt.AlignVCenter)
            self._celda_det(row, 3, cop(v.precio), Qt.AlignRight | Qt.AlignVCenter)
            item_met = QTableWidgetItem(v.metodo_pago)
            item_met.setTextAlignment(Qt.AlignCenter)
            if v.pagos_combinados:
                detalle = "  |  ".join(
                    f"{p['metodo']}: {cop(p['monto'])}" for p in v.pagos_combinados
                )
                item_met.setToolTip(detalle)
            self.tabla_detalle.setItem(row, 4, item_met)
            item_gn = QTableWidgetItem(cop(v.ganancia_neta))
            item_gn.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_gn.setForeground(
                QColor("#16A34A") if v.ganancia_neta >= 0 else QColor("#DC2626")
            )
            self.tabla_detalle.setItem(row, 5, item_gn)
            # Margen %
            ingresos = v.precio * v.cantidad
            if ingresos > 0:
                margen = round(v.ganancia_neta / ingresos * 100, 1)
                margen_txt = f"{margen:+.1f}%"
                margen_color = (
                    QColor("#15803D") if margen >= 20 else
                    QColor("#D97706") if margen >= 10 else
                    QColor("#DC2626")
                )
            else:
                margen_txt = "—"
                margen_color = QColor("#9CA3AF")
            item_margen = QTableWidgetItem(margen_txt)
            item_margen.setTextAlignment(Qt.AlignCenter)
            item_margen.setForeground(margen_color)
            self.tabla_detalle.setItem(row, 6, item_margen)
            # Fecha en columna notas para dar contexto al buscar todo el mes
            self._celda_det(row, 7, fecha_corta(v.fecha))
            self.tabla_detalle.setCellWidget(row, 8, self._btn_editar(v.id))
            self.tabla_detalle.setCellWidget(row, 9, self._btn_eliminar(v.id))

    def _cerrar_detalle(self) -> None:
        self._fecha_seleccionada = None
        self._campo_busqueda_hist.blockSignals(True)
        self._campo_busqueda_hist.clear()
        self._campo_busqueda_hist.blockSignals(False)
        self.tabla_detalle.setVisible(False)
        self._lbl_placeholder.setVisible(True)
        self._btn_cerrar_detalle.setVisible(False)
        self._lbl_detalle_titulo.setText("  Detalle del Día")

    # ------------------------------------------------------------------
    # Botones de acción (devuelven QPushButton directo, sin wrapper)
    # ------------------------------------------------------------------

    def _btn_editar(self, venta_id: int) -> QPushButton:
        btn = QPushButton("Editar")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Editar venta")
        btn.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#2563EB; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:11px; font-weight:bold; margin:3px; padding:0 6px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn.clicked.connect(lambda checked=False, vid=venta_id: self._on_editar_venta(vid))
        return btn

    def _btn_eliminar(self, venta_id: int) -> QPushButton:
        btn = QPushButton("Borrar")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Eliminar venta")
        btn.setStyleSheet(
            "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:11px; font-weight:bold; margin:3px; padding:0 6px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn.clicked.connect(lambda checked=False, vid=venta_id: self._on_eliminar_venta(vid))
        return btn

    def _on_editar_venta(self, venta_id: int) -> None:
        venta = next((v for v in self._ventas if v.id == venta_id), None)
        if venta is None:
            return
        from ui.edit_venta_dialog import EditVentaDialog
        dlg = EditVentaDialog(venta, self)
        def _tras_editar(_):
            self.refresh()
            self.venta_modificada.emit()
        dlg.venta_actualizada.connect(_tras_editar)
        dlg.exec()

    def _on_eliminar_venta(self, venta_id: int) -> None:
        venta = next((v for v in self._ventas if v.id == venta_id), None)
        if venta is None:
            return
        resp = QMessageBox.question(
            self,
            "Eliminar venta",
            f"¿Eliminar la venta de <b>{venta.producto}</b>?<br>"
            "Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self._venta_ctrl.eliminar_venta(venta_id)
            self.refresh()
            self.venta_modificada.emit()

    # ------------------------------------------------------------------
    # Navegación de mes
    # ------------------------------------------------------------------

    def _mes_anterior(self) -> None:
        mes = self.combo_mes.currentData()
        año = self.spin_año.value()
        if mes == 1:
            self.combo_mes.setCurrentIndex(11)
            self.spin_año.setValue(año - 1)
        else:
            self.combo_mes.setCurrentIndex(mes - 2)

    def _mes_siguiente(self) -> None:
        mes = self.combo_mes.currentData()
        año = self.spin_año.value()
        if mes == 12:
            self.combo_mes.setCurrentIndex(0)
            self.spin_año.setValue(año + 1)
        else:
            self.combo_mes.setCurrentIndex(mes)

