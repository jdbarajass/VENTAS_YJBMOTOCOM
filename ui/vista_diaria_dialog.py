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
    QFrame, QWidget, QSplitter,
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
    - Izquierda: tabla de ventas + totales por método de pago + botones de edición
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
        self.setMinimumSize(680, 460)
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

        splitter_h = QSplitter(Qt.Horizontal)
        splitter_h.setHandleWidth(6)
        splitter_h.addWidget(self._build_panel_ventas())
        splitter_h.addWidget(self._build_panel_derecho())
        splitter_h.setStretchFactor(0, 6)
        splitter_h.setStretchFactor(1, 4)
        root.addWidget(splitter_h, stretch=1)

        # Footer
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setFixedHeight(36)
        btn_cerrar.setStyleSheet(
            "QPushButton { border-radius:5px; padding:0 24px; font-size:13px; }"
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

        total_ingresos = sum(v.ingreso_real() for v in self._ventas)
        total_neta     = sum(v.ganancia_neta for v in self._ventas)
        total_gastos   = sum(g.monto for g in self._gastos)

        # Almacenar referencias para actualizar en _refrescar_ventas_ui
        chips_def = [
            (f"{len(self._ventas)} venta(s)", "#1D4ED8", "#DBEAFE", "_chip_nventa"),
            (f"Ingresos: {cop(total_ingresos)}", "#374151", "#F1F5F9", "_chip_ingresos"),
            (f"G. Neta: {cop(total_neta)}",
             "#15803D" if total_neta >= 0 else "#DC2626",
             "#DCFCE7" if total_neta >= 0 else "#FEE2E2",
             "_chip_neta"),
            (f"Gastos op.: {cop(total_gastos)}", "#92400E", "#FEF3C7", "_chip_gastos"),
        ]
        for texto, fg, bg, attr in chips_def:
            lbl_c = QLabel(texto)
            lbl_c.setStyleSheet(
                f"color:{fg}; background:{bg}; border-radius:4px;"
                f"font-size:12px; font-weight:bold; padding:4px 10px;"
            )
            lay.addWidget(lbl_c)
            setattr(self, attr, lbl_c)

        lay.addStretch()

        btn_pdf = QPushButton("📄 Exportar PDF")
        btn_pdf.setFixedHeight(30)
        btn_pdf.setStyleSheet(
            "QPushButton { background:#1D4ED8; color:white; border:none;"
            "border-radius:5px; font-size:12px; font-weight:bold; padding:0 14px; }"
            "QPushButton:hover { background:#1E40AF; }"
        )
        btn_pdf.clicked.connect(self._exportar_pdf_ventas_dia)
        lay.addWidget(btn_pdf)
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
        self._lbl_hdr_ventas = QLabel(f"  VENTAS  —  {len(self._ventas)} producto(s)")
        self._lbl_hdr_ventas.setFixedHeight(36)
        f = QFont(); f.setPointSize(11); f.setBold(True)
        self._lbl_hdr_ventas.setFont(f)
        self._lbl_hdr_ventas.setStyleSheet(
            "background:#16A34A; color:white; border-radius:8px 8px 0 0; padding:0 12px;"
        )
        lay.addWidget(self._lbl_hdr_ventas)

        # Tabla (guarda referencia para refrescar)
        self._tabla_v = self._crear_tabla_ventas()
        self._rellenar_tabla_ventas()
        lay.addWidget(self._tabla_v, stretch=1)

        # Totales (guarda referencia para reemplazar al refrescar)
        self._lay_panel_ventas = lay
        self._frame_totales = self._build_totales()
        lay.addWidget(self._frame_totales)
        return frame

    def _crear_tabla_ventas(self) -> QTableWidget:
        """Crea la estructura de la tabla de ventas (sin poblar filas)."""
        tabla = QTableWidget()
        tabla.setColumnCount(7)
        tabla.setHorizontalHeaderLabels([
            "Producto", "Costo", "Precio Venta", "Método de Pago", "G. Neta", "Notas", "Acciones"
        ])
        tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabla.verticalHeader().setVisible(False)
        tabla.setShowGrid(False)
        tabla.setAlternatingRowColors(True)
        tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        tabla.setStyleSheet("""
            QTableWidget { border:none; font-size:12px; }
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
        hh.setSectionResizeMode(0, QHeaderView.Interactive); tabla.setColumnWidth(0, 210)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); tabla.setColumnWidth(1, 90)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); tabla.setColumnWidth(2, 110)
        hh.setSectionResizeMode(3, QHeaderView.Interactive); tabla.setColumnWidth(3, 140)
        hh.setSectionResizeMode(4, QHeaderView.Interactive); tabla.setColumnWidth(4, 100)
        hh.setSectionResizeMode(5, QHeaderView.Interactive); tabla.setColumnWidth(5, 110)
        hh.setSectionResizeMode(6, QHeaderView.Fixed);       tabla.setColumnWidth(6, 80)
        hh.setStretchLastSection(False)
        return tabla

    def _rellenar_tabla_ventas(self) -> None:
        """Limpia y repuebla las filas de la tabla de ventas."""
        tabla = self._tabla_v
        tabla.setRowCount(len(self._ventas))
        for row, v in enumerate(self._ventas):
            tabla.setRowHeight(row, 32)
            precio_total = v.ingreso_real()
            costo_total  = v.costo * v.cantidad

            from utils.formatters import nombre_con_talla as _nct
            _nombre_base = _nct(v)
            prod_txt = _nombre_base if v.cantidad == 1 else f"{_nombre_base}  (×{v.cantidad})"
            item_prod = QTableWidgetItem(prod_txt)
            item_prod.setToolTip(_nombre_base)
            tabla.setItem(row, 0, item_prod)

            # Col 1 — Costo (gris, para distinguir del precio de venta)
            item_costo = QTableWidgetItem(cop(costo_total))
            item_costo.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_costo.setForeground(QColor("#6B7280"))
            item_costo.setToolTip(f"Costo unit.: {cop(v.costo)}")
            tabla.setItem(row, 1, item_costo)

            # Col 2 — Precio Venta
            item_precio = QTableWidgetItem(cop(precio_total))
            item_precio.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            tabla.setItem(row, 2, item_precio)

            # Col 3 — Método de Pago
            item_met = QTableWidgetItem(v.metodo_pago)
            item_met.setTextAlignment(Qt.AlignCenter)
            if v.pagos_combinados:
                detalle = "  |  ".join(
                    f"{p['metodo']}: {cop(p['monto'])}" for p in v.pagos_combinados
                )
                item_met.setToolTip(detalle)
            tabla.setItem(row, 3, item_met)

            # Col 4 — G. Neta
            item_gn = QTableWidgetItem(cop(v.ganancia_neta))
            item_gn.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_gn.setForeground(
                QColor("#16A34A") if v.ganancia_neta >= 0 else QColor("#DC2626")
            )
            tabla.setItem(row, 4, item_gn)

            # Col 5 — Notas
            tabla.setItem(row, 5, QTableWidgetItem(v.notas or ""))

            # Col 6 — Botón editar
            btn_edit = QPushButton("✏ Editar")
            btn_edit.setFixedHeight(26)
            btn_edit.setStyleSheet(
                "QPushButton { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;"
                "border-radius:4px; font-size:11px; font-weight:bold; padding:0 6px; }"
                "QPushButton:hover { background:#DBEAFE; }"
            )
            btn_edit.clicked.connect(lambda _=False, venta=v: self._abrir_editar_venta(venta))
            cell_w = QWidget()
            cell_w.setStyleSheet("background:transparent;")
            cell_lay = QHBoxLayout(cell_w)
            cell_lay.setContentsMargins(4, 2, 4, 2)
            cell_lay.addWidget(btn_edit)
            tabla.setCellWidget(row, 6, cell_w)

        tabla.resizeColumnToContents(0)
        tabla.setColumnWidth(0, min(tabla.columnWidth(0), 480))

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
                totales_met[v.metodo_pago] += v.ingreso_real()

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
                "Addi":     ("#EDE9FE", "#6D28D9"),
                "Otro":     ("#F3F4F6", "#374151"),
            }
            for metodo, total in sorted(totales_met.items()):
                if "Datafono" in metodo:
                    bg, fg = "#FEF9C3", "#854D0E"
                elif "Transferencia" in metodo:
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
        total_ingresos = sum(v.ingreso_real() for v in self._ventas)
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
    # Edición de ventas
    # ------------------------------------------------------------------

    def _abrir_editar_venta(self, venta: Venta) -> None:
        from ui.edit_venta_dialog import EditVentaDialog
        dlg = EditVentaDialog(venta, self)
        dlg.venta_actualizada.connect(lambda _: self._refrescar_ventas_ui())
        dlg.exec()

    def _refrescar_ventas_ui(self) -> None:
        """Recarga ventas desde BD y actualiza tabla, totales y chips del header."""
        from database.ventas_repo import obtener_ventas_por_fecha
        self._ventas = obtener_ventas_por_fecha(self._fecha)

        total_ingresos = sum(v.ingreso_real() for v in self._ventas)
        total_neta     = sum(v.ganancia_neta for v in self._ventas)

        # Actualizar chips del header
        self._chip_nventa.setText(f"{len(self._ventas)} venta(s)")
        self._chip_ingresos.setText(f"Ingresos: {cop(total_ingresos)}")
        color_neta = "#15803D" if total_neta >= 0 else "#DC2626"
        bg_neta    = "#DCFCE7" if total_neta >= 0 else "#FEE2E2"
        self._chip_neta.setText(f"G. Neta: {cop(total_neta)}")
        self._chip_neta.setStyleSheet(
            f"color:{color_neta}; background:{bg_neta}; border-radius:4px;"
            f"font-size:12px; font-weight:bold; padding:4px 10px;"
        )

        # Actualizar encabezado del panel de ventas
        self._lbl_hdr_ventas.setText(f"  VENTAS  —  {len(self._ventas)} producto(s)")

        # Repoblar tabla
        self._rellenar_tabla_ventas()

        # Reemplazar frame de totales
        item = self._lay_panel_ventas.takeAt(2)
        if item and item.widget():
            item.widget().deleteLater()
        self._frame_totales = self._build_totales()
        self._lay_panel_ventas.addWidget(self._frame_totales)

    # ------------------------------------------------------------------
    # Exportación PDF
    # ------------------------------------------------------------------

    def _exportar_pdf_ventas_dia(self) -> None:
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import os

        fecha_str = self._fecha.strftime("%Y-%m-%d")
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF de ventas",
            f"Ventas_{fecha_str}.pdf",
            "Archivos PDF (*.pdf)"
        )
        if not ruta:
            return
        try:
            from pathlib import Path
            self._generar_pdf_ventas(Path(ruta))
            os.startfile(ruta)
        except Exception as exc:
            QMessageBox.critical(self, "Error al exportar",
                                 f"No se pudo generar el PDF:\n{exc}")

    def _generar_pdf_ventas(self, ruta) -> None:
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.units import cm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle, HRFlowable,
        )
        from utils.formatters import nombre_con_talla

        C_AZUL   = rl_colors.HexColor("#1E293B")
        C_VERDE  = rl_colors.HexColor("#16A34A")
        C_VERDE_C= rl_colors.HexColor("#DCFCE7")
        C_ROJO   = rl_colors.HexColor("#DC2626")
        C_GRIS_C = rl_colors.HexColor("#F1F5F9")
        C_BORDE  = rl_colors.HexColor("#E2E8F0")
        C_GRIS_T = rl_colors.HexColor("#6B7280")
        C_AZUL_V = rl_colors.HexColor("#1D4ED8")

        styles  = getSampleStyleSheet()
        st_base = styles["Normal"]

        def st(name, **kw):
            return ParagraphStyle(name, parent=st_base, **kw)

        st_tit  = st("tit", fontName="Helvetica-Bold", fontSize=16,
                     textColor=C_AZUL, spaceAfter=2)
        st_sub  = st("sub", fontName="Helvetica", fontSize=11,
                     textColor=rl_colors.HexColor("#374151"), spaceAfter=6)
        st_hdr  = st("hdr", fontName="Helvetica-Bold", fontSize=10,
                     textColor=rl_colors.white, alignment=TA_CENTER)
        st_cel  = st("cel", fontName="Helvetica", fontSize=10,
                     textColor=rl_colors.HexColor("#111827"), leading=13)
        st_r    = st("r",   fontName="Helvetica", fontSize=10,
                     textColor=rl_colors.HexColor("#111827"),
                     alignment=TA_RIGHT, leading=13)
        st_rgr  = st("rgr", fontName="Helvetica", fontSize=10,
                     textColor=C_GRIS_T, alignment=TA_RIGHT, leading=13)
        st_rb   = st("rb",  fontName="Helvetica-Bold", fontSize=10,
                     textColor=rl_colors.HexColor("#111827"),
                     alignment=TA_RIGHT, leading=13)
        st_tot  = st("tot", fontName="Helvetica-Bold", fontSize=10,
                     textColor=rl_colors.HexColor("#111827"), leading=13)

        doc = SimpleDocTemplate(
            str(ruta),
            pagesize=landscape(letter),
            leftMargin=1.5*cm, rightMargin=1.5*cm,
            topMargin=1.5*cm,  bottomMargin=1.5*cm,
            title=f"Ventas {self._fecha} — YJBMOTOCOM",
        )

        story = []
        story.append(Paragraph("YJBMOTOCOM — Ventas del Día", st_tit))
        story.append(Paragraph(_titulo_fecha_largo(self._fecha), st_sub))
        story.append(HRFlowable(width="100%", thickness=1,
                                color=C_BORDE, spaceAfter=8))

        # Anchos de columna para landscape letter (~24.9 cm útiles)
        # #(1) Costo(3.2) PrecioVenta(3.5) Método(3.5) GNeta(3.0) → Producto = resto ~10.7cm
        col_w = [1*cm, 10.7*cm, 3.2*cm, 3.5*cm, 3.5*cm, 3.0*cm]

        encabezados = ["#", "Producto", "Costo", "Precio Venta", "Método Pago", "G. Neta"]
        fila_hdr = [Paragraph(f"<b>{h}</b>", st_hdr) for h in encabezados]
        data = [fila_hdr]

        total_ingresos = 0.0
        total_costo    = 0.0
        total_neta     = 0.0

        for i, v in enumerate(self._ventas, start=1):
            nombre = nombre_con_talla(v)
            if v.cantidad > 1:
                nombre += f"  (×{v.cantidad})"
            costo_t  = v.costo * v.cantidad
            precio_t = v.ingreso_real()
            total_ingresos += precio_t
            total_costo    += costo_t
            total_neta     += v.ganancia_neta

            gn_col = "#15803D" if v.ganancia_neta >= 0 else "#DC2626"
            met_txt = v.metodo_pago
            if v.pagos_combinados:
                met_txt = "Combinado"

            data.append([
                Paragraph(str(i), st("ni", parent=st_base, fontSize=10,
                                     alignment=TA_CENTER)),
                Paragraph(nombre,      st_cel),
                Paragraph(cop(costo_t), st_rgr),
                Paragraph(cop(precio_t), st_r),
                Paragraph(met_txt, st("mc", parent=st_base, fontSize=10,
                                      alignment=TA_CENTER)),
                Paragraph(
                    f'<font color="{gn_col}">{cop(v.ganancia_neta)}</font>',
                    st_r),
            ])

        # Fila de totales
        gn_tot_col = "#15803D" if total_neta >= 0 else "#DC2626"
        data.append([
            Paragraph("", st_cel),
            Paragraph("<b>TOTALES</b>", st_tot),
            Paragraph(f"<b>{cop(total_costo)}</b>",
                      st("tgr", parent=st_base, fontName="Helvetica-Bold",
                         fontSize=10, textColor=C_GRIS_T, alignment=TA_RIGHT)),
            Paragraph(f"<b>{cop(total_ingresos)}</b>", st_rb),
            Paragraph("", st_cel),
            Paragraph(
                f'<b><font color="{gn_tot_col}">{cop(total_neta)}</font></b>',
                st_rb),
        ])

        n_rows  = len(data)        # header + datos + totals
        n_datos = n_rows - 2       # filas de datos (sin header ni totals)

        ts = TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),       C_AZUL),
            ("TEXTCOLOR",     (0, 0), (-1, 0),       rl_colors.white),
            ("VALIGN",        (0, 0), (-1, -1),      "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1),      5),
            ("BOTTOMPADDING", (0, 0), (-1, -1),      5),
            ("LEFTPADDING",   (0, 0), (-1, -1),      6),
            ("RIGHTPADDING",  (0, 0), (-1, -1),      6),
            ("LINEBELOW",     (0, 0), (-1, 0),       1, C_AZUL),
            ("BOX",           (0, 0), (-1, -1),      1, C_BORDE),
            # Filas alternas en datos
            *[("BACKGROUND", (0, i), (-1, i), C_GRIS_C)
              for i in range(2, n_rows - 1, 2)],
            # Fila de totales
            ("LINEABOVE",  (0, n_rows - 1), (-1, n_rows - 1), 1, C_AZUL),
            ("BACKGROUND", (0, n_rows - 1), (-1, n_rows - 1), C_GRIS_C),
            ("FONTNAME",   (0, n_rows - 1), (-1, n_rows - 1), "Helvetica-Bold"),
        ])

        tabla_pdf = Table(data, colWidths=col_w, repeatRows=1)
        tabla_pdf.setStyle(ts)
        story.append(tabla_pdf)
        story.append(Spacer(1, 0.6*cm))

        # Bloque resumen alineado a la derecha
        gn_color_s = "#15803D" if total_neta >= 0 else "#DC2626"
        resumen_data = [
            [Paragraph("Total Ingresos", st_tot),
             Paragraph(f"<b>{cop(total_ingresos)}</b>",
                       st("ri", parent=st_base, fontName="Helvetica-Bold",
                          fontSize=11, textColor=C_AZUL_V, alignment=TA_RIGHT))],
            [Paragraph("Total Costo", st_tot),
             Paragraph(f"<b>{cop(total_costo)}</b>",
                       st("rc", parent=st_base, fontName="Helvetica-Bold",
                          fontSize=11, textColor=C_GRIS_T, alignment=TA_RIGHT))],
            [Paragraph("Ganancia Neta", st_tot),
             Paragraph(
                 f'<b><font color="{gn_color_s}">{cop(total_neta)}</font></b>',
                 st("rg2", parent=st_base, fontName="Helvetica-Bold",
                    fontSize=11, alignment=TA_RIGHT))],
        ]
        t_res = Table(resumen_data, colWidths=[6*cm, 5*cm])
        t_res.setStyle(TableStyle([
            ("BOX",            (0, 0), (-1, -1), 1, C_BORDE),
            ("LINEBELOW",      (0, 0), (-1, -2), 0.5, C_BORDE),
            ("BACKGROUND",     (0, 0), (-1, -1), C_GRIS_C),
            ("TOPPADDING",     (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 6),
            ("LEFTPADDING",    (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        # Empujar el bloque resumen a la derecha con una tabla contenedora
        usable_w = 24.9 * cm
        spacer_w = usable_w - 11 * cm
        story.append(Table([[Paragraph("", st_cel), t_res]],
                           colWidths=[spacer_w, 11 * cm]))

        doc.build(story)

    # ------------------------------------------------------------------
    # Panel derecho — Préstamos + Gastos
    # ------------------------------------------------------------------

    def _build_panel_derecho(self) -> QSplitter:
        splitter_v = QSplitter(Qt.Vertical)
        splitter_v.setHandleWidth(6)
        splitter_v.setStyleSheet("background:transparent;")
        splitter_v.addWidget(self._build_panel_prestamos())
        splitter_v.addWidget(self._build_panel_gastos())
        splitter_v.setStretchFactor(0, 6)
        splitter_v.setStretchFactor(1, 4)
        return splitter_v

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
            QTableWidget { border:none; font-size:11px; }
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

        tabla.resizeColumnToContents(1)
        tabla.setColumnWidth(1, min(tabla.columnWidth(1), 320))

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
            QTableWidget { border:none; font-size:11px; }
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

        tabla.resizeColumnToContents(0)
        tabla.setColumnWidth(0, min(tabla.columnWidth(0), 320))

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
