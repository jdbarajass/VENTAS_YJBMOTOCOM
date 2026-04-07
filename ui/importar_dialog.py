"""
ui/importar_dialog.py
Diálogo para importar ventas desde un archivo .xlsx exportado por YJBMOTOCOM.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from services.importador import importar_desde_excel, ResultadoImportacion
from database.ventas_repo import (
    eliminar_ventas_por_fecha, eliminar_ventas_por_mes,
    obtener_ventas_por_fecha, obtener_ventas_por_mes,
    insertar_venta,
)
from database.prestamos_repo import eliminar_todos_prestamos, insertar_prestamo
from utils.formatters import cop, fecha_corta


class ImportarDialog(QDialog):
    """Diálogo para importar ventas desde Excel y reemplazar el período detectado."""

    importacion_completada = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Importar Ventas desde Excel")
        self.setMinimumSize(760, 540)
        self._resultado: ResultadoImportacion | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(12)

        # Título
        lbl_titulo = QLabel("Importar Ventas desde Excel")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        lbl_titulo.setFont(f)
        root.addWidget(lbl_titulo)

        lbl_sub = QLabel(
            "Selecciona un archivo <b>.xlsx</b> exportado por YJBMOTOCOM. "
            "El programa detectará automáticamente si es diario o mensual y "
            "reemplazará las ventas existentes para ese período."
        )
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color:#6B7280; font-size:12px;")
        root.addWidget(lbl_sub)

        # Selector de archivo
        fila = QHBoxLayout()
        self._lbl_archivo = QLabel("Ningún archivo seleccionado")
        self._lbl_archivo.setStyleSheet(
            "border:1px solid #D1D5DB; border-radius:5px; padding:6px 10px;"
            "background:white; color:#9CA3AF; font-size:11px;"
        )
        self._lbl_archivo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._lbl_archivo.setFixedHeight(34)

        btn_sel = QPushButton("Seleccionar archivo…")
        btn_sel.setFixedHeight(34)
        btn_sel.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 16px; background:white; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_sel.clicked.connect(self._seleccionar_archivo)

        fila.addWidget(self._lbl_archivo)
        fila.addWidget(btn_sel)
        root.addLayout(fila)

        # Panel info (azul)
        self._frame_info = self._frame_color("#EFF6FF", "#BFDBFE")
        self._frame_info.setVisible(False)
        info_lay = QVBoxLayout(self._frame_info)
        info_lay.setContentsMargins(12, 8, 12, 8)
        self._lbl_info = QLabel()
        self._lbl_info.setStyleSheet(
            "color:#1E40AF; font-size:12px; background:transparent; border:none;"
        )
        info_lay.addWidget(self._lbl_info)
        root.addWidget(self._frame_info)

        # Panel advertencia reemplazo (amarillo)
        self._frame_warn = self._frame_color("#FEF3C7", "#FDE68A")
        self._frame_warn.setVisible(False)
        warn_lay = QVBoxLayout(self._frame_warn)
        warn_lay.setContentsMargins(12, 8, 12, 8)
        self._lbl_warn = QLabel()
        self._lbl_warn.setWordWrap(True)
        self._lbl_warn.setStyleSheet(
            "color:#92400E; font-size:12px; background:transparent; border:none;"
        )
        warn_lay.addWidget(self._lbl_warn)
        root.addWidget(self._frame_warn)

        # Panel errores (rojo)
        self._frame_err = self._frame_color("#FEF2F2", "#FECACA")
        self._frame_err.setVisible(False)
        err_lay = QVBoxLayout(self._frame_err)
        err_lay.setContentsMargins(12, 8, 12, 8)
        self._lbl_err = QLabel()
        self._lbl_err.setWordWrap(True)
        self._lbl_err.setStyleSheet(
            "color:#DC2626; font-size:11px; background:transparent; border:none;"
        )
        err_lay.addWidget(self._lbl_err)
        root.addWidget(self._frame_err)

        # Tabla preview
        lbl_prev = QLabel("Vista previa (primeras 10 filas):")
        lbl_prev.setStyleSheet("color:#374151; font-size:11px; font-weight:bold;")
        root.addWidget(lbl_prev)

        self._tabla = QTableWidget()
        self._tabla.setColumnCount(7)
        self._tabla.setHorizontalHeaderLabels(
            ["Fecha", "Producto", "Cant.", "Precio", "Método", "Comisión", "G. Neta"]
        )
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setShowGrid(False)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.setMaximumHeight(210)
        self._tabla.setStyleSheet("""
            QTableWidget { border:1px solid #E5E7EB; font-size:11px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:10px; padding:4px; border:none;
            }
            QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }
        """)
        hh = self._tabla.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Fixed);  self._tabla.setColumnWidth(0, 88)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.Fixed);  self._tabla.setColumnWidth(2, 48)
        hh.setSectionResizeMode(3, QHeaderView.Fixed);  self._tabla.setColumnWidth(3, 110)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);  self._tabla.setColumnWidth(4, 120)
        hh.setSectionResizeMode(5, QHeaderView.Fixed);  self._tabla.setColumnWidth(5, 100)
        hh.setSectionResizeMode(6, QHeaderView.Fixed);  self._tabla.setColumnWidth(6, 100)
        root.addWidget(self._tabla)

        # Botones
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(36)
        btn_cancelar.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px; padding:0 18px; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_cancelar.clicked.connect(self.reject)

        self._btn_importar = QPushButton("⬆  Importar y Reemplazar")
        self._btn_importar.setFixedHeight(36)
        self._btn_importar.setEnabled(False)
        self._btn_importar.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:5px;"
            "padding:0 18px; font-weight:bold; }"
            "QPushButton:hover { background:#1D4ED8; }"
            "QPushButton:disabled { background:#9CA3AF; }"
        )
        self._btn_importar.clicked.connect(self._on_importar)

        btn_row.addWidget(btn_cancelar)
        btn_row.addSpacing(8)
        btn_row.addWidget(self._btn_importar)
        root.addLayout(btn_row)

    def _frame_color(self, bg: str, border: str) -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            f"QFrame {{ background:{bg}; border:1px solid {border}; border-radius:6px; }}"
        )
        return f

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def _seleccionar_archivo(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Excel de YJBMOTOCOM", "", "Excel (*.xlsx)"
        )
        if not ruta:
            return
        self._lbl_archivo.setText(ruta)
        self._lbl_archivo.setStyleSheet(
            "border:1px solid #D1D5DB; border-radius:5px; padding:6px 10px;"
            "background:white; color:#374151; font-size:11px;"
        )
        self._procesar_archivo(Path(ruta))

    def _procesar_archivo(self, ruta: Path) -> None:
        resultado = importar_desde_excel(ruta)
        self._resultado = resultado

        # Errores de parsing
        if resultado.errores:
            self._frame_err.setVisible(True)
            self._lbl_err.setText(
                "Advertencias al leer el archivo:\n• " +
                "\n• ".join(resultado.errores)
            )
        else:
            self._frame_err.setVisible(False)

        if not resultado.ventas:
            self._frame_info.setVisible(False)
            self._frame_warn.setVisible(False)
            self._btn_importar.setEnabled(False)
            self._tabla.setRowCount(0)
            return

        # Info período
        self._frame_info.setVisible(True)
        info_txt = (
            f"Período detectado: <b>{resultado.periodo_str}</b>  •  "
            f"<b>{len(resultado.ventas)}</b> ventas encontradas en el archivo"
        )
        if resultado.prestamos:
            info_txt += f"  •  <b>{len(resultado.prestamos)}</b> préstamos encontrados"
        self._lbl_info.setText(info_txt)

        # Verificar existentes en BD
        if resultado.tipo == "dia" and resultado.fecha:
            existentes = len(obtener_ventas_por_fecha(resultado.fecha))
        elif resultado.tipo == "mes" and resultado.año and resultado.mes:
            existentes = len(obtener_ventas_por_mes(resultado.año, resultado.mes))
        else:
            existentes = 0

        tiene_prestamos = len(resultado.prestamos) > 0
        if existentes > 0 or tiene_prestamos:
            self._frame_warn.setVisible(True)
            partes = []
            if existentes > 0:
                partes.append(
                    f"las <b>{existentes} ventas</b> existentes para <b>{resultado.periodo_str}</b> "
                    f"serán reemplazadas por las <b>{len(resultado.ventas)}</b> del archivo"
                )
            if tiene_prestamos:
                partes.append(
                    f"<b>todos los préstamos</b> actuales serán reemplazados por los "
                    f"<b>{len(resultado.prestamos)}</b> del archivo"
                )
            self._lbl_warn.setText("⚠  Al importar: " + "; ".join(partes) + ".")
        else:
            self._frame_warn.setVisible(False)

        self._poblar_preview(resultado)
        self._btn_importar.setEnabled(True)

    def _poblar_preview(self, resultado: ResultadoImportacion) -> None:
        preview = resultado.ventas[:10]
        self._tabla.setRowCount(len(preview))
        for row, v in enumerate(preview):
            self._tabla.setRowHeight(row, 26)
            self._celda(row, 0, fecha_corta(v.fecha), Qt.AlignCenter)
            self._celda(row, 1, v.producto)
            self._celda(row, 2, str(v.cantidad), Qt.AlignCenter)
            self._celda(row, 3, cop(v.precio), Qt.AlignRight | Qt.AlignVCenter)
            self._celda(row, 4, v.metodo_pago, Qt.AlignCenter)
            self._celda(row, 5, cop(v.comision), Qt.AlignRight | Qt.AlignVCenter)
            self._celda(row, 6, cop(v.ganancia_neta), Qt.AlignRight | Qt.AlignVCenter)

    def _celda(self, row: int, col: int, texto: str,
               alin: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> None:
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alin)
        self._tabla.setItem(row, col, item)

    def _on_importar(self) -> None:
        if not self._resultado or not self._resultado.ventas:
            return

        res = self._resultado
        try:
            # 1. Eliminar ventas del período
            if res.tipo == "dia" and res.fecha:
                eliminar_ventas_por_fecha(res.fecha)
            elif res.tipo == "mes" and res.año and res.mes:
                eliminar_ventas_por_mes(res.año, res.mes)

            # 2. Insertar ventas del Excel
            for v in res.ventas:
                v.id = None
                insertar_venta(v)

            # 3. Reemplazar préstamos si el archivo los trae
            if res.prestamos:
                eliminar_todos_prestamos()
                for p in res.prestamos:
                    p.id = None
                    insertar_prestamo(p)

        except Exception as exc:
            QMessageBox.critical(self, "Error al importar", str(exc))
            return

        detalle = f"<b>{len(res.ventas)} ventas</b> para <b>{res.periodo_str}</b>"
        if res.prestamos:
            detalle += f" y <b>{len(res.prestamos)} préstamos</b>"
        QMessageBox.information(
            self,
            "Importación exitosa",
            f"Se importaron correctamente {detalle}.",
        )
        self.importacion_completada.emit()
        self.accept()
