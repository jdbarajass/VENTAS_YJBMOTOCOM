"""
ui/historial_panel.py
Historial mensual: resumen + gráfica de utilidad diaria + tabla detalle.
Gráfica dibujada con QPainter — sin dependencias externas de charting.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QSizePolicy,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush

from controllers.historial_controller import HistorialController
from controllers.venta_controller import VentaController
from services.reportes import ResumenDiario, ResumenMensual
from utils.formatters import cop, nombre_mes, fecha_corta, MESES_ES
from models.venta import Venta


# ======================================================================
# Gráfica de barras (QPainter)
# ======================================================================

class GraficaBarras(QWidget):
    """
    Gráfica de barras para la utilidad real por día.
    Verde = día positivo | Rojo = día negativo | Gris = sin ventas.
    Sin dependencias de QtCharts.
    """

    _COLOR_POS   = QColor("#16A34A")
    _COLOR_NEG   = QColor("#DC2626")
    _COLOR_CERO  = QColor("#E5E7EB")
    _COLOR_GRID  = QColor("#F3F4F6")
    _COLOR_EJE   = QColor("#9CA3AF")
    _COLOR_TEXTO = QColor("#6B7280")

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._datos: list[ResumenDiario] = []
        self.setMinimumHeight(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background-color: #FFFFFF; border-radius: 8px;")

    def set_datos(self, resumenes: list[ResumenDiario]) -> None:
        self._datos = resumenes
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._datos:
            self._pintar_vacio()
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W, H = self.width(), self.height()
        ML, MR, MT, MB = 58, 16, 16, 32   # márgenes izq, der, arr, aba

        area_w = W - ML - MR
        area_h = H - MT - MB

        valores = [r.utilidad_real for r in self._datos]
        max_v = max(valores) if max(valores) > 0 else 0
        min_v = min(valores) if min(valores) < 0 else 0
        rango = max_v - min_v or 1

        # Posición Y del cero
        zero_y = MT + area_h * (max_v / rango)

        # ---- Cuadrícula ----
        num_lineas = 5
        p.setPen(QPen(self._COLOR_GRID, 1))
        for i in range(num_lineas + 1):
            y = int(MT + area_h * i / num_lineas)
            p.drawLine(ML, y, W - MR, y)

        # ---- Línea de cero ----
        p.setPen(QPen(self._COLOR_CERO, 2))
        p.drawLine(ML, int(zero_y), W - MR, int(zero_y))

        # ---- Etiquetas eje Y ----
        p.setPen(QPen(self._COLOR_TEXTO))
        font = p.font(); font.setPointSize(8); p.setFont(font)
        for i in range(num_lineas + 1):
            y = int(MT + area_h * i / num_lineas)
            valor_y = max_v - rango * i / num_lineas
            texto = self._fmt_eje(valor_y)
            p.drawText(0, y - 6, ML - 4, 14, Qt.AlignRight | Qt.AlignVCenter, texto)

        # ---- Barras ----
        n = len(self._datos)
        slot_w = area_w / n
        bar_w = max(4, slot_w * 0.65)
        gap = (slot_w - bar_w) / 2

        for i, rd in enumerate(self._datos):
            x = ML + i * slot_w + gap
            v = rd.utilidad_real

            if rd.cantidad_ventas == 0:
                color = self._COLOR_CERO
                bar_h = max(3, area_h * 0.015)
                bar_y = zero_y - bar_h / 2
            elif v >= 0:
                color = self._COLOR_POS
                bar_h = max(3, area_h * v / rango)
                bar_y = zero_y - bar_h
            else:
                color = self._COLOR_NEG
                bar_h = max(3, area_h * (-v) / rango)
                bar_y = zero_y

            p.fillRect(QRect(int(x), int(bar_y), int(bar_w), int(bar_h)), color)

        # ---- Etiquetas eje X (cada 5 días) ----
        p.setPen(QPen(self._COLOR_TEXTO))
        font.setPointSize(8); p.setFont(font)
        for i, rd in enumerate(self._datos):
            dia = rd.fecha.day
            if dia == 1 or dia % 5 == 0:
                x = int(ML + i * slot_w + slot_w / 2)
                p.drawText(x - 12, H - MB + 4, 24, MB - 4,
                           Qt.AlignCenter, str(dia))

        p.end()

    def _pintar_vacio(self) -> None:
        p = QPainter(self)
        p.setPen(QPen(QColor("#9CA3AF")))
        f = p.font(); f.setPointSize(11); p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, "Sin datos para este mes")
        p.end()

    @staticmethod
    def _fmt_eje(valor: float) -> str:
        """Formato compacto para etiquetas del eje Y (en miles)."""
        if abs(valor) >= 1_000_000:
            return f"{valor / 1_000_000:.1f}M"
        if abs(valor) >= 1_000:
            return f"{int(valor / 1_000)}k"
        return str(int(valor))


# ======================================================================
# Panel principal del historial mensual
# ======================================================================

class HistorialPanel(QWidget):
    """Vista de historial mensual completa."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = HistorialController()
        self._venta_ctrl = VentaController()
        self._resumen: ResumenMensual | None = None
        self._ventas: list[Venta] = []
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
        root.addWidget(self._panel_grafica())
        root.addWidget(self._panel_tabla(), stretch=1)

    # ---- Barra superior ----

    def _barra_superior(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Historial Mensual")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)

        # Selector mes
        self.combo_mes = QComboBox()
        self.combo_mes.setFixedHeight(34)
        self.combo_mes.setFixedWidth(115)
        for num, nombre in MESES_ES.items():
            self.combo_mes.addItem(nombre, num)
        self.combo_mes.setCurrentIndex(date.today().month - 1)

        # Selector año
        self.spin_año = QSpinBox()
        self.spin_año.setRange(2020, 2040)
        self.spin_año.setValue(date.today().year)
        self.spin_año.setFixedHeight(34)
        self.spin_año.setFixedWidth(75)
        self.spin_año.setButtonSymbols(QSpinBox.NoButtons)

        btn_prev = self._btn_nav("◀")
        btn_next = self._btn_nav("▶")
        btn_prev.clicked.connect(self._mes_anterior)
        btn_next.clicked.connect(self._mes_siguiente)

        self.btn_exportar = QPushButton("⬇  Exportar Excel")
        self.btn_exportar.setFixedHeight(34)
        self.btn_exportar.setStyleSheet(
            "QPushButton { background:#16A34A; color:white; border-radius:5px;"
            "padding:0 14px; font-weight:bold; }"
            "QPushButton:hover { background:#15803D; }"
            "QPushButton:disabled { background:#9CA3AF; }"
        )
        self.btn_exportar.clicked.connect(self._on_exportar)

        self.combo_mes.currentIndexChanged.connect(lambda _: self.refresh())
        self.spin_año.valueChanged.connect(lambda _: self.refresh())

        lay.addWidget(titulo)
        lay.addSpacing(12)
        lay.addWidget(btn_prev)
        lay.addWidget(self.combo_mes)
        lay.addWidget(self.spin_año)
        lay.addWidget(btn_next)
        lay.addStretch()
        lay.addWidget(self.btn_exportar)
        return lay

    def _btn_nav(self, texto: str) -> QPushButton:
        btn = QPushButton(texto)
        btn.setFixedSize(30, 34)
        btn.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        return btn

    # ---- Fila de tarjetas de resumen ----

    def _fila_resumen(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(12)

        self.card_ventas    = self._tarjeta("Ventas del mes",       "0",    "#1D4ED8")
        self.card_ingresos  = self._tarjeta("Ingresos totales",     "$ 0",  "#374151")
        self.card_g_neta    = self._tarjeta("Ganancia neta",        "$ 0",  "#374151")
        self.card_utilidad  = self._tarjeta("Utilidad real del mes","$ 0",  "#374151")
        self.card_positivos = self._tarjeta("Días positivos",       "0",    "#15803D")
        self.card_negativos = self._tarjeta("Días negativos",       "0",    "#DC2626")

        for c in (self.card_ventas, self.card_ingresos, self.card_g_neta,
                  self.card_utilidad, self.card_positivos, self.card_negativos):
            lay.addWidget(c)
        return lay

    def _tarjeta(self, titulo: str, valor: str, color: str) -> QWidget:
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

    # ---- Panel de gráfica ----

    def _panel_grafica(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(8)

        encabezado = QHBoxLayout()
        lbl = QLabel("Utilidad Real por Día")
        f = QFont(); f.setPointSize(12); f.setBold(True)
        lbl.setFont(f)

        leyenda_pos = self._leyenda("Positivo", "#16A34A")
        leyenda_neg = self._leyenda("Negativo", "#DC2626")
        leyenda_sin = self._leyenda("Sin ventas", "#E5E7EB")

        encabezado.addWidget(lbl)
        encabezado.addStretch()
        encabezado.addWidget(leyenda_pos)
        encabezado.addWidget(leyenda_neg)
        encabezado.addWidget(leyenda_sin)

        self.grafica = GraficaBarras()
        lay.addLayout(encabezado)
        lay.addWidget(self.grafica)
        return frame

    def _leyenda(self, texto: str, color: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)
        cuadro = QLabel()
        cuadro.setFixedSize(12, 12)
        cuadro.setStyleSheet(f"background:{color}; border-radius:2px;")
        lbl = QLabel(texto)
        lbl.setStyleSheet("color:#6B7280; font-size:11px;")
        h.addWidget(cuadro)
        h.addWidget(lbl)
        return w

    # ---- Tabla de ventas del mes ----

    def _panel_tabla(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)

        encabezado = QLabel("  Ventas del Mes")
        f = QFont(); f.setPointSize(11); f.setBold(True)
        encabezado.setFont(f)
        encabezado.setContentsMargins(16, 10, 16, 0)
        lay.addWidget(encabezado)

        # Col 0 oculta: id de la venta
        # Cols: ID | Fecha | Producto | Cant | Precio | Método | Ventas | Ingresos | G.Neta | Gasto | Utilidad | Estado | ✎ | 🗑
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(14)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Fecha", "Producto", "Cant", "Precio", "Método",
            "Ventas", "Ingresos", "G. Neta", "Gasto", "Utilidad", "Estado", "", ""
        ])
        self.tabla.setColumnHidden(0, True)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setStyleSheet("""
            QTableWidget { border:none; font-size:12px; }
            QTableWidget::item { padding:3px 8px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:11px; padding:5px; border:none;
            }
            QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }
        """)

        hh = self.tabla.horizontalHeader()
        hh.setSectionResizeMode(1,  QHeaderView.Fixed);  self.tabla.setColumnWidth(1,  88)
        hh.setSectionResizeMode(2,  QHeaderView.Stretch)
        hh.setSectionResizeMode(3,  QHeaderView.Fixed);  self.tabla.setColumnWidth(3,  46)
        hh.setSectionResizeMode(4,  QHeaderView.Fixed);  self.tabla.setColumnWidth(4,  100)
        hh.setSectionResizeMode(5,  QHeaderView.Fixed);  self.tabla.setColumnWidth(5,  130)
        hh.setSectionResizeMode(6,  QHeaderView.Fixed);  self.tabla.setColumnWidth(6,  55)
        hh.setSectionResizeMode(7,  QHeaderView.Fixed);  self.tabla.setColumnWidth(7,  105)
        hh.setSectionResizeMode(8,  QHeaderView.Fixed);  self.tabla.setColumnWidth(8,  100)
        hh.setSectionResizeMode(9,  QHeaderView.Fixed);  self.tabla.setColumnWidth(9,  100)
        hh.setSectionResizeMode(10, QHeaderView.Fixed);  self.tabla.setColumnWidth(10, 100)
        hh.setSectionResizeMode(11, QHeaderView.Fixed);  self.tabla.setColumnWidth(11, 88)
        hh.setSectionResizeMode(12, QHeaderView.Fixed);  self.tabla.setColumnWidth(12, 46)
        hh.setSectionResizeMode(13, QHeaderView.Fixed);  self.tabla.setColumnWidth(13, 46)

        lay.addWidget(self.tabla)
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

        # Tarjetas resumen
        self.card_ventas._lbl_valor.setText(str(r.cantidad_ventas))
        self.card_ingresos._lbl_valor.setText(cop(r.total_ingresos))

        color_neta = "#16A34A" if r.ganancia_neta >= 0 else "#DC2626"
        self.card_g_neta._lbl_valor.setText(cop(r.ganancia_neta))
        self.card_g_neta._lbl_valor.setStyleSheet(f"color:{color_neta}; font-size:16px; font-weight:bold;")

        color_util = "#16A34A" if r.utilidad_real >= 0 else "#DC2626"
        self.card_utilidad._lbl_valor.setText(cop(r.utilidad_real))
        self.card_utilidad._lbl_valor.setStyleSheet(
            f"color:{color_util}; font-size:16px; font-weight:bold;"
        )

        self.card_positivos._lbl_valor.setText(str(r.dias_positivos))
        self.card_negativos._lbl_valor.setText(str(r.dias_negativos))

        # Gráfica
        self.grafica.set_datos(r.resumen_por_dia)

        # Tabla — ventas individuales con contexto diario
        from PySide6.QtGui import QColor as C
        resumen_dia = {rd.fecha: rd for rd in r.resumen_por_dia}

        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(self._ventas))
        for row, v in enumerate(self._ventas):
            self.tabla.setRowHeight(row, 30)
            rd = resumen_dia.get(v.fecha)

            # Col 0 (oculta): id
            self.tabla.setItem(row, 0, QTableWidgetItem(str(v.id)))

            # Fecha
            self._celda(row, 1, fecha_corta(v.fecha), Qt.AlignCenter)

            # Producto
            self._celda(row, 2, v.producto)

            # Cantidad
            self._celda(row, 3, str(v.cantidad), Qt.AlignCenter)

            # Precio unitario
            self._celda(row, 4, cop(v.precio), Qt.AlignRight | Qt.AlignVCenter)

            # Método de pago
            self._celda(row, 5, v.metodo_pago, Qt.AlignCenter)

            # Ventas del día
            self._celda(row, 6, str(rd.cantidad_ventas) if rd else "-", Qt.AlignCenter)

            # Ingresos del día
            self._celda(row, 7, cop(rd.total_ingresos) if rd else "-", Qt.AlignRight | Qt.AlignVCenter)

            # Ganancia neta individual (verde/rojo)
            item_gn = QTableWidgetItem(cop(v.ganancia_neta))
            item_gn.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_gn.setForeground(C("#16A34A") if v.ganancia_neta >= 0 else C("#DC2626"))
            self.tabla.setItem(row, 8, item_gn)

            # Gasto del día
            self._celda(row, 9, cop(rd.gasto_diario) if rd else "-", Qt.AlignRight | Qt.AlignVCenter)

            # Utilidad del día (verde/rojo)
            if rd:
                item_ut = QTableWidgetItem(cop(rd.utilidad_real))
                item_ut.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item_ut.setForeground(C("#16A34A") if rd.utilidad_real >= 0 else C("#DC2626"))
                self.tabla.setItem(row, 10, item_ut)
            else:
                self._celda(row, 10, "-", Qt.AlignCenter)

            # Estado del día
            if rd:
                estado_txt = "✔ +" if rd.es_positivo else "✘ −"
                item_est = QTableWidgetItem(estado_txt)
                item_est.setTextAlignment(Qt.AlignCenter)
                item_est.setForeground(C("#15803D") if rd.es_positivo else C("#DC2626"))
                self.tabla.setItem(row, 11, item_est)
            else:
                self._celda(row, 11, "-", Qt.AlignCenter)

            # Botón editar
            self.tabla.setCellWidget(row, 12, self._btn_editar(v.id))

            # Botón eliminar
            self.tabla.setCellWidget(row, 13, self._btn_eliminar(v.id))

        # Botón exportar
        self.btn_exportar.setEnabled(r.cantidad_ventas > 0)

    def _celda(self, row: int, col: int, texto: str,
               alin: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alin)
        self.tabla.setItem(row, col, item)

    def _btn_editar(self, venta_id: int) -> QWidget:
        """Crea el botón de lápiz para editar una venta."""
        btn = QPushButton("✎")
        btn.setFixedSize(32, 26)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Editar venta")
        btn.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#2563EB; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:14px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn.clicked.connect(lambda checked=False, vid=venta_id: self._on_editar_venta(vid))
        # Centrar el botón dentro de la celda
        wrapper = QWidget()
        lay = QHBoxLayout(wrapper)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.addWidget(btn)
        return wrapper

    def _btn_eliminar(self, venta_id: int) -> QWidget:
        """Crea el botón de papelera para eliminar una venta."""
        btn = QPushButton("🗑")
        btn.setFixedSize(32, 26)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Eliminar venta")
        btn.setStyleSheet(
            "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:13px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn.clicked.connect(lambda checked=False, vid=venta_id: self._on_eliminar_venta(vid))
        wrapper = QWidget()
        lay = QHBoxLayout(wrapper)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.addWidget(btn)
        return wrapper

    def _on_eliminar_venta(self, venta_id: int) -> None:
        """Pide confirmación y elimina la venta."""
        venta = next((v for v in self._ventas if v.id == venta_id), None)
        if venta is None:
            return
        resp = QMessageBox.question(
            self,
            "Eliminar venta",
            f"¿Eliminar la venta de <b>{venta.producto}</b>?<br>"
            f"Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            self._venta_ctrl.eliminar_venta(venta_id)
            self.refresh()

    def _on_editar_venta(self, venta_id: int) -> None:
        """Abre el diálogo de edición para la venta con el id dado."""
        venta = next((v for v in self._ventas if v.id == venta_id), None)
        if venta is None:
            return
        from ui.edit_venta_dialog import EditVentaDialog
        dlg = EditVentaDialog(venta, self)
        dlg.venta_actualizada.connect(lambda _: self.refresh())
        dlg.exec()

    # ------------------------------------------------------------------
    # Navegación de mes
    # ------------------------------------------------------------------

    def _mes_anterior(self) -> None:
        mes = self.combo_mes.currentData()
        año = self.spin_año.value()
        if mes == 1:
            self.combo_mes.setCurrentIndex(11)   # Diciembre
            self.spin_año.setValue(año - 1)
        else:
            self.combo_mes.setCurrentIndex(mes - 2)

    def _mes_siguiente(self) -> None:
        mes = self.combo_mes.currentData()
        año = self.spin_año.value()
        if mes == 12:
            self.combo_mes.setCurrentIndex(0)    # Enero
            self.spin_año.setValue(año + 1)
        else:
            self.combo_mes.setCurrentIndex(mes)

    # ------------------------------------------------------------------
    # Exportar Excel
    # ------------------------------------------------------------------

    def _on_exportar(self) -> None:
        mes = self.combo_mes.currentData()
        año = self.spin_año.value()
        nombre_sugerido = f"Historial_{año}-{mes:02d}.xlsx"

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar Excel mensual", nombre_sugerido, "Excel (*.xlsx)"
        )
        if not ruta:
            return
        try:
            from pathlib import Path
            self._ctrl.exportar_excel(año, mes, Path(ruta))
            QMessageBox.information(self, "Exportación exitosa",
                                    f"Archivo guardado en:\n{ruta}")
        except Exception as exc:
            QMessageBox.critical(self, "Error al exportar", str(exc))
