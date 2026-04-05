"""
ui/historial_panel.py
Historial mensual: tarjetas de resumen + tabla diaria + tabla detalle ventas.
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame, QSizePolicy,
    QFileDialog, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from controllers.historial_controller import HistorialController
from controllers.venta_controller import VentaController
from services.reportes import ResumenDiario, ResumenMensual
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
        root.addWidget(self._panel_tabla(), stretch=1)

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

        self.btn_exportar = QPushButton("⬇  Exportar Excel")
        self.btn_exportar.setFixedHeight(34)
        self.btn_exportar.setStyleSheet(
            "QPushButton { background:#16A34A; color:white; border-radius:5px;"
            "padding:0 14px; font-weight:bold; }"
            "QPushButton:hover { background:#15803D; }"
            "QPushButton:disabled { background:#9CA3AF; }"
        )
        self.btn_exportar.clicked.connect(self._on_exportar)

        btn_importar = QPushButton("⬆  Importar Excel")
        btn_importar.setFixedHeight(34)
        btn_importar.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:5px;"
            "padding:0 14px; font-weight:bold; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btn_importar.clicked.connect(self._on_importar_excel)

        self.combo_mes.currentIndexChanged.connect(lambda _: self.refresh())
        self.spin_año.valueChanged.connect(lambda _: self.refresh())

        lay.addWidget(titulo)
        lay.addSpacing(12)
        lay.addWidget(btn_prev)
        lay.addWidget(self.combo_mes)
        lay.addWidget(self.spin_año)
        lay.addWidget(btn_next)
        lay.addStretch()
        lay.addWidget(btn_importar)
        lay.addWidget(self.btn_exportar)
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
        hh.setSectionResizeMode(0, QHeaderView.Fixed);  self.tabla_diaria.setColumnWidth(0, 90)
        hh.setSectionResizeMode(1, QHeaderView.Fixed);  self.tabla_diaria.setColumnWidth(1, 55)
        hh.setSectionResizeMode(2, QHeaderView.Fixed);  self.tabla_diaria.setColumnWidth(2, 115)
        hh.setSectionResizeMode(3, QHeaderView.Fixed);  self.tabla_diaria.setColumnWidth(3, 110)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);  self.tabla_diaria.setColumnWidth(4, 110)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        hh.setSectionResizeMode(6, QHeaderView.Fixed);  self.tabla_diaria.setColumnWidth(6, 90)

        lay.addWidget(self.tabla_diaria)
        return frame

    # ---- Tabla detalle de ventas ----

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

        # Col 0 oculta: id venta
        # Cols visibles: Fecha|Producto|Cant|Precio|Método|Ventas|Ingresos|G.Neta|Gasto|Utilidad|Estado|✎|🗑
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(14)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Fecha", "Producto", "Cant", "Precio", "Método",
            "Ventas", "Ingresos", "G. Neta", "Gasto", "Utilidad", "Estado", "✎", "🗑"
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
        hh.setSectionResizeMode(11, QHeaderView.Fixed);  self.tabla.setColumnWidth(11, 80)
        hh.setSectionResizeMode(12, QHeaderView.Fixed);  self.tabla.setColumnWidth(12, 38)
        hh.setSectionResizeMode(13, QHeaderView.Fixed);  self.tabla.setColumnWidth(13, 38)

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

        # ---- Tabla ventas individuales ----
        resumen_dia = {rd.fecha: rd for rd in r.resumen_por_dia}

        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(self._ventas))
        for row, v in enumerate(self._ventas):
            self.tabla.setRowHeight(row, 32)
            rd = resumen_dia.get(v.fecha)

            self.tabla.setItem(row, 0, QTableWidgetItem(str(v.id)))
            self._celda(row, 1, fecha_corta(v.fecha), Qt.AlignCenter)
            self._celda(row, 2, v.producto)
            self._celda(row, 3, str(v.cantidad), Qt.AlignCenter)
            self._celda(row, 4, cop(v.precio), Qt.AlignRight | Qt.AlignVCenter)
            self._celda(row, 5, v.metodo_pago, Qt.AlignCenter)
            self._celda(row, 6, str(rd.cantidad_ventas) if rd else "-", Qt.AlignCenter)
            self._celda(row, 7, cop(rd.total_ingresos) if rd else "-", Qt.AlignRight | Qt.AlignVCenter)

            item_gn = QTableWidgetItem(cop(v.ganancia_neta))
            item_gn.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_gn.setForeground(QColor("#16A34A") if v.ganancia_neta >= 0 else QColor("#DC2626"))
            self.tabla.setItem(row, 8, item_gn)

            self._celda(row, 9, cop(rd.gasto_diario) if rd else "-",
                        Qt.AlignRight | Qt.AlignVCenter)

            if rd:
                item_ut = QTableWidgetItem(cop(rd.utilidad_real))
                item_ut.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item_ut.setForeground(
                    QColor("#16A34A") if rd.utilidad_real >= 0 else QColor("#DC2626")
                )
                self.tabla.setItem(row, 10, item_ut)
            else:
                self._celda(row, 10, "-", Qt.AlignCenter)

            if rd:
                estado_txt = "+" if rd.es_positivo else "−"
                item_est = QTableWidgetItem(estado_txt)
                item_est.setTextAlignment(Qt.AlignCenter)
                item_est.setForeground(QColor("#15803D") if rd.es_positivo else QColor("#DC2626"))
                self.tabla.setItem(row, 11, item_est)
            else:
                self._celda(row, 11, "-", Qt.AlignCenter)

            # Botones directos (sin wrapper) para que se vean correctamente
            self.tabla.setCellWidget(row, 12, self._btn_editar(v.id))
            self.tabla.setCellWidget(row, 13, self._btn_eliminar(v.id))

        self.btn_exportar.setEnabled(r.cantidad_ventas > 0)

    # ------------------------------------------------------------------
    # Helpers de celda
    # ------------------------------------------------------------------

    def _celda(self, row: int, col: int, texto: str,
               alin: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alin)
        self.tabla.setItem(row, col, item)

    def _celda_d(self, row: int, col: int, texto: str,
                 alin: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alin)
        self.tabla_diaria.setItem(row, col, item)

    # ------------------------------------------------------------------
    # Botones de acción (devuelven QPushButton directo, sin wrapper)
    # ------------------------------------------------------------------

    def _btn_editar(self, venta_id: int) -> QPushButton:
        btn = QPushButton("✎")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Editar venta")
        btn.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#2563EB; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:14px; margin:3px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn.clicked.connect(lambda checked=False, vid=venta_id: self._on_editar_venta(vid))
        return btn

    def _btn_eliminar(self, venta_id: int) -> QPushButton:
        btn = QPushButton("🗑")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip("Eliminar venta")
        btn.setStyleSheet(
            "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:13px; margin:3px; }"
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

    # ------------------------------------------------------------------
    # Exportar Excel
    # ------------------------------------------------------------------

    def _on_importar_excel(self) -> None:
        from ui.importar_dialog import ImportarDialog
        dlg = ImportarDialog(self)
        dlg.importacion_completada.connect(self.refresh)
        dlg.importacion_completada.connect(self.venta_modificada.emit)
        dlg.exec()

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
            QMessageBox.information(
                self, "Exportación exitosa", f"Archivo guardado en:\n{ruta}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error al exportar", str(exc))
