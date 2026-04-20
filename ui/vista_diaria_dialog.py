"""
ui/vista_diaria_dialog.py
Popup de vista completa del día: ventas, préstamos y gastos operativos.
Inspirado en el layout del Excel de seguimiento diario.
"""

from collections import defaultdict
from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QFrame, QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from models.venta import Venta
from utils.formatters import cop, fecha_corta

_DIAS_ES   = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
_MESES_ES  = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _titulo_fecha_largo(f: date) -> str:
    return f"{_DIAS_ES[f.weekday()]}, {f.day} de {_MESES_ES[f.month]} {f.year}"


class VistaDiariaDialog(QDialog):
    """
    Ventana con la vista completa de un día seleccionado:
    - Izquierda: tabla de ventas + totales por método de pago
    - Derecha arriba: todos los préstamos registrados
    - Derecha abajo: gastos operativos del día
    """

    def __init__(self, ventas: list, fecha: date, parent=None) -> None:
        super().__init__(parent)
        self._ventas = ventas
        self._fecha  = fecha
        self._gastos: list = []
        self._prestamos: list = []
        self._cargar_datos()
        self._build_ui()
        self.setWindowTitle(f"Vista del Día — {_titulo_fecha_largo(fecha)}")
        # Ventana normal con maximizar, minimizar y cerrar
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowCloseButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowMinimizeButtonHint
        )
        self.setMinimumSize(860, 560)
        self.showMaximized()

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------

    def _cargar_datos(self) -> None:
        try:
            from database.gastos_dia_repo import obtener_gastos_por_fecha
            self._gastos = obtener_gastos_por_fecha(self._fecha)
        except Exception:
            self._gastos = []
        try:
            from database.prestamos_repo import obtener_prestamos_pendientes
            self._prestamos = obtener_prestamos_pendientes()
        except Exception:
            self._prestamos = []

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 14)
        root.setSpacing(12)

        root.addLayout(self._build_header())

        content = QHBoxLayout()
        content.setSpacing(14)
        content.addWidget(self._build_panel_ventas(), stretch=6)
        content.addWidget(self._build_panel_derecho(), stretch=4)
        root.addLayout(content, stretch=1)

        # Footer
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedHeight(36)
        btn_cerrar.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px;"
            "background:white; color:#374151; padding:0 24px; font-size:13px; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_cerrar.clicked.connect(self.accept)
        footer = QHBoxLayout()
        footer.addStretch()
        footer.addWidget(btn_cerrar)
        root.addLayout(footer)

    def _build_header(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setSpacing(10)

        lbl = QLabel(_titulo_fecha_largo(self._fecha))
        f = QFont(); f.setPointSize(15); f.setBold(True)
        lbl.setFont(f)
        lay.addWidget(lbl)
        lay.addSpacing(16)

        total_ingresos = sum(v.precio * v.cantidad for v in self._ventas)
        total_neta     = sum(v.ganancia_neta for v in self._ventas)
        total_gastos   = sum(g.monto for g in self._gastos)

        chips = [
            (f"{len(self._ventas)} venta(s)", "#1D4ED8", "#DBEAFE"),
            (f"Ingresos: {cop(total_ingresos)}", "#374151", "#F1F5F9"),
            (f"G. Neta: {cop(total_neta)}",
             "#15803D" if total_neta >= 0 else "#DC2626",
             "#DCFCE7" if total_neta >= 0 else "#FEE2E2"),
            (f"Gastos op.: {cop(total_gastos)}", "#92400E", "#FEF3C7"),
        ]
        for texto, fg, bg in chips:
            lbl_c = QLabel(texto)
            lbl_c.setStyleSheet(
                f"color:{fg}; background:{bg}; border-radius:4px;"
                f"font-size:12px; font-weight:bold; padding:4px 10px;"
            )
            lay.addWidget(lbl_c)

        lay.addStretch()
        return lay

    # ------------------------------------------------------------------
    # Panel izquierdo — Ventas
    # ------------------------------------------------------------------

    def _build_panel_ventas(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Encabezado verde (como el Excel)
        hdr = QLabel(f"  VENTAS  —  {len(self._ventas)} producto(s)")
        hdr.setFixedHeight(36)
        f = QFont(); f.setPointSize(11); f.setBold(True)
        hdr.setFont(f)
        hdr.setStyleSheet(
            "background:#16A34A; color:white; border-radius:8px 8px 0 0; padding:0 12px;"
        )
        lay.addWidget(hdr)

        # Tabla
        tabla = self._tabla_ventas()
        lay.addWidget(tabla, stretch=1)

        # Totales
        lay.addWidget(self._build_totales())
        return frame

    def _tabla_ventas(self) -> QTableWidget:
        tabla = QTableWidget()
        tabla.setColumnCount(5)
        tabla.setHorizontalHeaderLabels([
            "Producto", "Precio Venta", "Método de Pago", "G. Neta", "Notas"
        ])
        tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabla.verticalHeader().setVisible(False)
        tabla.setShowGrid(False)
        tabla.setAlternatingRowColors(True)
        tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        tabla.setStyleSheet("""
            QTableWidget { border:none; font-size:12px; background:white; }
            QTableWidget::item { padding:4px 8px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:11px; padding:5px; border:none;
            }
            QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }
            QToolTip {
                background:#1E293B; color:#FFFFFF;
                border:1px solid #475569; padding:5px 8px;
                font-size:12px; border-radius:4px;
            }
        """)
        hh = tabla.horizontalHeader()
        hh.setMinimumSectionSize(60)
        hh.setSectionResizeMode(0, QHeaderView.Interactive); tabla.setColumnWidth(0, 230)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); tabla.setColumnWidth(1, 115)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); tabla.setColumnWidth(2, 145)
        hh.setSectionResizeMode(3, QHeaderView.Interactive); tabla.setColumnWidth(3, 105)
        hh.setSectionResizeMode(4, QHeaderView.Interactive); tabla.setColumnWidth(4, 120)
        hh.setStretchLastSection(False)

        tabla.setRowCount(len(self._ventas))
        for row, v in enumerate(self._ventas):
            tabla.setRowHeight(row, 30)
            precio_total = v.precio * v.cantidad

            prod_txt = v.producto if v.cantidad == 1 else f"{v.producto}  (×{v.cantidad})"
            item_prod = QTableWidgetItem(prod_txt)
            item_prod.setToolTip(v.producto)
            tabla.setItem(row, 0, item_prod)

            item_precio = QTableWidgetItem(cop(precio_total))
            item_precio.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tabla.setItem(row, 1, item_precio)

            item_met = QTableWidgetItem(v.metodo_pago)
            item_met.setTextAlignment(Qt.AlignCenter)
            if v.pagos_combinados:
                detalle = "  |  ".join(
                    f"{p['metodo']}: {cop(p['monto'])}" for p in v.pagos_combinados
                )
                item_met.setToolTip(detalle)
            tabla.setItem(row, 2, item_met)

            item_gn = QTableWidgetItem(cop(v.ganancia_neta))
            item_gn.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_gn.setForeground(
                QColor("#16A34A") if v.ganancia_neta >= 0 else QColor("#DC2626")
            )
            tabla.setItem(row, 3, item_gn)

            tabla.setItem(row, 4, QTableWidgetItem(v.notas or ""))

        return tabla

    def _build_totales(self) -> QFrame:
        """Sección inferior con desglose por método y grand total."""
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background:#F8FAFC; border-top:1px solid #E2E8F0;"
            "border-radius:0 0 8px 8px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 8, 14, 10)
        lay.setSpacing(6)

        # Desglose por método (expandiendo pagos combinados)
        totales_met: dict[str, float] = defaultdict(float)
        for v in self._ventas:
            if v.pagos_combinados:
                for p in v.pagos_combinados:
                    totales_met[p["metodo"]] += p["monto"]
            else:
                totales_met[v.metodo_pago] += v.precio * v.cantidad

        if totales_met:
            fila_met = QHBoxLayout()
            fila_met.setSpacing(8)
            lbl_por = QLabel("Por método:")
            lbl_por.setStyleSheet(
                "color:#6B7280; font-size:11px; font-weight:bold; background:transparent;"
            )
            fila_met.addWidget(lbl_por)

            _COL = {
                "Efectivo": ("#DCFCE7", "#15803D"),
                "Bold":     ("#FEF3C7", "#92400E"),
                "Addi":     ("#EDE9FE", "#6D28D9"),
                "Otro":     ("#F3F4F6", "#374151"),
            }
            for metodo, total in sorted(totales_met.items()):
                if "Transferencia" in metodo:
                    bg, fg = "#DBEAFE", "#1D4ED8"
                else:
                    bg, fg = _COL.get(metodo, ("#F3F4F6", "#374151"))
                lbl = QLabel(f"{metodo}: {cop(total)}")
                lbl.setStyleSheet(
                    f"background:{bg}; color:{fg}; border-radius:4px;"
                    f"font-size:11px; font-weight:bold; padding:2px 8px;"
                )
                fila_met.addWidget(lbl)
            fila_met.addStretch()
            lay.addLayout(fila_met)

        # Grand totals
        total_ingresos = sum(v.precio * v.cantidad for v in self._ventas)
        total_neta     = sum(v.ganancia_neta for v in self._ventas)

        fila_tot = QHBoxLayout()
        fila_tot.addStretch()

        def _chip_total(etiqueta, valor, color):
            lbl = QLabel(f"{etiqueta}:  <b>{valor}</b>")
            lbl.setStyleSheet(f"color:{color}; font-size:13px; background:transparent;")
            return lbl

        sep = QLabel("  |  ")
        sep.setStyleSheet("color:#D1D5DB; background:transparent;")

        color_neta = "#15803D" if total_neta >= 0 else "#DC2626"
        fila_tot.addWidget(_chip_total("TOTAL INGRESOS", cop(total_ingresos), "#1D4ED8"))
        fila_tot.addWidget(sep)
        fila_tot.addWidget(_chip_total("GANANCIA NETA", cop(total_neta), color_neta))
        lay.addLayout(fila_tot)
        return frame

    # ------------------------------------------------------------------
    # Panel derecho — Préstamos + Gastos
    # ------------------------------------------------------------------

    def _build_panel_derecho(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        lay.addWidget(self._build_panel_prestamos(), stretch=6)
        lay.addWidget(self._build_panel_gastos(), stretch=4)
        return w

    def _build_panel_prestamos(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Encabezado naranja
        hdr = QLabel(f"  PRÉSTAMOS  —  {len(self._prestamos)} registro(s)")
        hdr.setFixedHeight(36)
        f = QFont(); f.setPointSize(11); f.setBold(True)
        hdr.setFont(f)
        hdr.setStyleSheet(
            "background:#D97706; color:white; border-radius:8px 8px 0 0; padding:0 12px;"
        )
        lay.addWidget(hdr)

        if not self._prestamos:
            lbl = QLabel("Sin préstamos registrados.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color:#9CA3AF; font-size:12px; padding:20px; background:transparent;"
            )
            lay.addWidget(lbl)
            return frame

        tabla = QTableWidget()
        tabla.setColumnCount(4)
        tabla.setHorizontalHeaderLabels(["Fecha", "Producto", "Almacén", "Estado"])
        tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabla.verticalHeader().setVisible(False)
        tabla.setShowGrid(False)
        tabla.setAlternatingRowColors(True)
        tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        tabla.setStyleSheet("""
            QTableWidget { border:none; font-size:11px; background:white; }
            QTableWidget::item { padding:3px 6px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:10px; padding:4px; border:none;
            }
            QToolTip {
                background:#1E293B; color:#FFFFFF;
                border:1px solid #475569; padding:4px 7px;
                font-size:11px; border-radius:4px;
            }
        """)
        hh = tabla.horizontalHeader()
        hh.setMinimumSectionSize(55)
        hh.setSectionResizeMode(0, QHeaderView.Interactive); tabla.setColumnWidth(0, 78)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); tabla.setColumnWidth(1, 160)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); tabla.setColumnWidth(2, 95)
        hh.setSectionResizeMode(3, QHeaderView.Interactive); tabla.setColumnWidth(3, 78)
        hh.setStretchLastSection(False)

        tabla.setRowCount(len(self._prestamos))
        for row, p in enumerate(self._prestamos):
            tabla.setRowHeight(row, 26)
            tabla.setItem(row, 0, QTableWidgetItem(fecha_corta(p.fecha)))

            item_prod = QTableWidgetItem(p.producto)
            tooltip = p.producto
            if p.observaciones:
                tooltip += f"\n{p.observaciones}"
            item_prod.setToolTip(tooltip)
            tabla.setItem(row, 1, item_prod)

            tabla.setItem(row, 2, QTableWidgetItem(p.almacen))

            item_est = QTableWidgetItem(p.estado.capitalize())
            item_est.setTextAlignment(Qt.AlignCenter)
            if p.estado == "pendiente":
                item_est.setForeground(QColor("#D97706"))
            elif p.estado == "devuelto":
                item_est.setForeground(QColor("#15803D"))
            else:
                item_est.setForeground(QColor("#6B7280"))
            tabla.setItem(row, 3, item_est)

        lay.addWidget(tabla, stretch=1)
        return frame

    def _build_panel_gastos(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Encabezado rojo
        hdr = QLabel(f"  GASTOS OPERATIVOS  —  {fecha_corta(self._fecha)}")
        hdr.setFixedHeight(36)
        f = QFont(); f.setPointSize(11); f.setBold(True)
        hdr.setFont(f)
        hdr.setStyleSheet(
            "background:#DC2626; color:white; border-radius:8px 8px 0 0; padding:0 12px;"
        )
        lay.addWidget(hdr)

        if not self._gastos:
            lbl = QLabel("Sin gastos operativos para este día.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color:#9CA3AF; font-size:12px; padding:16px; background:transparent;"
            )
            lay.addWidget(lbl)
            return frame

        tabla = QTableWidget()
        tabla.setColumnCount(3)
        tabla.setHorizontalHeaderLabels(["Descripción", "Categoría", "Monto"])
        tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabla.verticalHeader().setVisible(False)
        tabla.setShowGrid(False)
        tabla.setAlternatingRowColors(True)
        tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        tabla.setStyleSheet("""
            QTableWidget { border:none; font-size:11px; background:white; }
            QTableWidget::item { padding:3px 6px; }
            QHeaderView::section {
                background:#1E293B; color:white; font-weight:bold;
                font-size:10px; padding:4px; border:none;
            }
        """)
        hh = tabla.horizontalHeader()
        hh.setMinimumSectionSize(55)
        hh.setSectionResizeMode(0, QHeaderView.Interactive); tabla.setColumnWidth(0, 200)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); tabla.setColumnWidth(1, 90)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); tabla.setColumnWidth(2, 95)
        hh.setStretchLastSection(False)

        tabla.setRowCount(len(self._gastos))
        for row, g in enumerate(self._gastos):
            tabla.setRowHeight(row, 26)
            tabla.setItem(row, 0, QTableWidgetItem(g.descripcion))
            tabla.setItem(row, 1, QTableWidgetItem(g.categoria))
            item_m = QTableWidgetItem(cop(g.monto))
            item_m.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_m.setForeground(QColor("#DC2626"))
            tabla.setItem(row, 2, item_m)

        lay.addWidget(tabla, stretch=1)

        # Total gastos
        total_gastos = sum(g.monto for g in self._gastos)
        lbl_tot = QLabel(f"Total gastos:  <b>{cop(total_gastos)}</b>")
        lbl_tot.setAlignment(Qt.AlignRight)
        lbl_tot.setStyleSheet(
            "color:#DC2626; font-size:12px; padding:4px 12px 6px 12px;"
            "background:#FEF2F2; border-top:1px solid #FECACA;"
            "border-radius:0 0 8px 8px;"
        )
        lay.addWidget(lbl_tot)
        return frame
