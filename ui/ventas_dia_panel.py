"""
ui/ventas_dia_panel.py
Panel de ventas del día: tabla CRUD + gastos operativos + barra resumen + exportar Excel.
"""

from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDateEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox,
    QFileDialog, QFrame, QSizePolicy, QLineEdit, QScrollArea,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor

from controllers.ventas_dia_controller import VentasDiaController
from database.config_repo import obtener_configuracion
from ui.edit_venta_dialog import EditVentaDialog
from ui.venta_form import MoneyLineEdit
from utils.formatters import cop, fecha_corta

# Columnas de la tabla (índices)
COL_ID       = 0   # oculto
COL_NUM      = 1
COL_FECHA    = 2
COL_PRODUCTO = 3
COL_COSTO    = 4
COL_PRECIO   = 5
COL_METODO   = 6
COL_COMISION = 7
COL_NETA     = 8
COL_NOTAS    = 9
COL_ACCIONES = 10

TOTAL_COLS   = 11


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

        lbl_fecha = QLabel("Fecha:")
        lbl_fecha.setStyleSheet("color: #6B7280;")

        self.date_selector = QDateEdit()
        self.date_selector.setCalendarPopup(True)
        self.date_selector.setDate(QDate.currentDate())
        self.date_selector.setDisplayFormat("dd/MM/yyyy")
        self.date_selector.setFixedHeight(34)
        self.date_selector.setFixedWidth(130)
        self.date_selector.dateChanged.connect(lambda _: self._cargar_datos())

        self.btn_hoy = QPushButton("Hoy")
        self.btn_hoy.setFixedHeight(34)
        self.btn_hoy.setFixedWidth(60)
        self.btn_hoy.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        self.btn_hoy.clicked.connect(self._ir_hoy)

        self.btn_exportar = QPushButton("⬇  Exportar Excel")
        self.btn_exportar.setFixedHeight(34)
        self.btn_exportar.setStyleSheet(
            "QPushButton { background:#16A34A; color:white; border-radius:5px; padding:0 14px; font-weight:bold; }"
            "QPushButton:hover { background:#15803D; }"
            "QPushButton:disabled { background:#9CA3AF; }"
        )
        self.btn_exportar.clicked.connect(self._on_exportar)

        lay.addWidget(titulo)
        lay.addSpacing(16)
        lay.addWidget(lbl_fecha)
        lay.addWidget(self.date_selector)
        lay.addWidget(self.btn_hoy)
        lay.addStretch()
        lay.addWidget(self.btn_exportar)
        return lay

    def _build_tabla(self) -> QTableWidget:
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(TOTAL_COLS)
        self.tabla.setHorizontalHeaderLabels([
            "id", "#", "Fecha", "Producto",
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
            QTableWidget::item:selected { background-color: #DBEAFE; color: #1E3A5F; }
        """)

        # Anchos de columna
        hh = self.tabla.horizontalHeader()
        hh.setSectionResizeMode(COL_NUM,      QHeaderView.Fixed);       self.tabla.setColumnWidth(COL_NUM, 40)
        hh.setSectionResizeMode(COL_FECHA,    QHeaderView.Fixed);       self.tabla.setColumnWidth(COL_FECHA, 100)
        hh.setSectionResizeMode(COL_PRODUCTO, QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_COSTO,    QHeaderView.Fixed);       self.tabla.setColumnWidth(COL_COSTO, 110)
        hh.setSectionResizeMode(COL_PRECIO,   QHeaderView.Fixed);       self.tabla.setColumnWidth(COL_PRECIO, 120)
        hh.setSectionResizeMode(COL_METODO,   QHeaderView.Fixed);       self.tabla.setColumnWidth(COL_METODO, 105)
        hh.setSectionResizeMode(COL_COMISION, QHeaderView.Fixed);       self.tabla.setColumnWidth(COL_COMISION, 105)
        hh.setSectionResizeMode(COL_NETA,     QHeaderView.Fixed);       self.tabla.setColumnWidth(COL_NETA, 120)
        hh.setSectionResizeMode(COL_NOTAS,    QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_ACCIONES, QHeaderView.Fixed);       self.tabla.setColumnWidth(COL_ACCIONES, 110)

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
        self.lbl_gastos_op  = self._chip("Gastos op.: $ 0",  "#B45309")
        self.lbl_utilidad   = self._chip("Utilidad: $ 0",    "#15803D")

        for lbl in (self.lbl_cantidad, self.lbl_ingresos, self.lbl_costos,
                    self.lbl_comisiones, self.lbl_neta_total,
                    self.lbl_gastos_op, self.lbl_utilidad):
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

        for row, v in enumerate(self._ventas):
            self.tabla.setRowHeight(row, 36)

            self._celda(row, COL_ID,       str(v.id),            Qt.AlignCenter)
            self._celda(row, COL_NUM,      str(row + 1),         Qt.AlignCenter)
            self._celda(row, COL_FECHA,    fecha_corta(v.fecha), Qt.AlignCenter)
            self._celda(row, COL_PRODUCTO, v.producto)
            self._celda(row, COL_COSTO,    cop(v.costo),         Qt.AlignRight | Qt.AlignVCenter)
            self._celda(row, COL_PRECIO,   cop(v.precio),        Qt.AlignRight | Qt.AlignVCenter)
            self._celda(row, COL_METODO,   v.metodo_pago,        Qt.AlignCenter)
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

            # Botones de acción
            self.tabla.setCellWidget(row, COL_ACCIONES, self._widget_acciones(v.id))

        self.btn_exportar.setEnabled(len(self._ventas) > 0)

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

        for g in self._gastos:
            fila = QWidget()
            fila.setStyleSheet(
                "QWidget { background: white; border-radius: 4px; border: none; }"
            )
            lay = QHBoxLayout(fila)
            lay.setContentsMargins(8, 3, 8, 3)
            lay.setSpacing(8)

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

            lay.addWidget(lbl_desc, stretch=3)
            lay.addWidget(lbl_monto, stretch=1)
            lay.addWidget(btn_del)

            self._gastos_lista_layout.addWidget(fila)

    def _celda(self, row: int, col: int, texto: str,
               alineacion: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alineacion)
        self.tabla.setItem(row, col, item)

    def _widget_acciones(self, venta_id: int) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)

        btn_editar = QPushButton("✎ Editar")
        btn_editar.setFixedHeight(26)
        btn_editar.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:11px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn_editar.clicked.connect(lambda _, vid=venta_id: self._on_editar(vid))

        btn_eliminar = QPushButton("🗑")
        btn_eliminar.setFixedHeight(26)
        btn_eliminar.setFixedWidth(30)
        btn_eliminar.setStyleSheet(
            "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:13px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn_eliminar.clicked.connect(lambda _, vid=venta_id: self._on_eliminar(vid))

        lay.addWidget(btn_editar)
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

        self.lbl_cantidad.setText(f"{n} venta{'s' if n != 1 else ''}")
        self.lbl_ingresos.setText(f"Ingresos: {cop(ingresos)}")
        self.lbl_costos.setText(f"Costos: {cop(costos)}")
        self.lbl_comisiones.setText(f"Comisiones: {cop(comisiones)}")
        self.lbl_neta_total.setText(f"G. neta: {cop(neta)}")
        self.lbl_gastos_op.setText(f"Gastos op.: {cop(gastos_op)}")
        self.lbl_utilidad.setText(f"Utilidad: {cop(utilidad)}")

        color_neta = "#15803D" if neta >= 0 else "#DC2626"
        self.lbl_neta_total.setStyleSheet(
            f"color: {color_neta}; font-weight: bold; font-size: 12px;"
            f"background: #F1F5F9; border-radius: 4px; padding: 4px 10px;"
        )
        color_util = "#15803D" if utilidad >= 0 else "#DC2626"
        self.lbl_utilidad.setStyleSheet(
            f"color: {color_util}; font-weight: bold; font-size: 12px;"
            f"background: #F1F5F9; border-radius: 4px; padding: 4px 10px;"
        )

        # Totales por método de pago
        totales: dict[str, float] = {}
        for v in self._ventas:
            # "Transferencia NEQUI" → "Transferencia"
            metodo = v.metodo_pago.split()[0]
            totales[metodo] = totales.get(metodo, 0.0) + v.precio * v.cantidad
        self._actualizar_metodos(totales)

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

        # Colores por método
        _COLORES = {
            "Efectivo":      ("#DCFCE7", "#15803D"),
            "Bold":          ("#FEF3C7", "#92400E"),
            "Addi":          ("#EDE9FE", "#6D28D9"),
            "Transferencia": ("#DBEAFE", "#1D4ED8"),
            "Otro":          ("#F3F4F6", "#374151"),
        }

        for metodo, total in sorted(totales.items()):
            bg, fg = _COLORES.get(metodo, ("#F3F4F6", "#374151"))
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

    def _on_exportar(self) -> None:
        if not self._ventas:
            return

        qd = self.date_selector.date()
        fecha = date(qd.year(), qd.month(), qd.day())
        nombre_sugerido = f"Ventas_{fecha.strftime('%Y-%m-%d')}.xlsx"

        ruta, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Excel",
            nombre_sugerido,
            "Excel (*.xlsx)",
        )
        if not ruta:
            return

        try:
            self._ctrl.exportar_excel(self._ventas, fecha, Path(ruta))
            QMessageBox.information(
                self, "Exportación exitosa",
                f"Archivo guardado en:\n{ruta}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error al exportar", str(exc))

    # ------------------------------------------------------------------
    # Acciones CRUD — gastos operativos
    # ------------------------------------------------------------------

    def _on_agregar_gasto(self) -> None:
        descripcion = self.campo_gasto_desc.text().strip()
        monto = self.campo_gasto_monto.valor_int()

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
            self._ctrl.agregar_gasto(descripcion, float(monto), fecha)
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
