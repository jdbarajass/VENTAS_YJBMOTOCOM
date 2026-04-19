"""
ui/cargue_pedidos_widget.py
Widget para cargar PDFs de pedidos de ACCESORIOS PARA MOTOS S.A.S.
y actualizar el inventario de cascos (suma stock o crea nuevas referencias).
"""
from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QMessageBox, QLineEdit, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from utils.formatters import cop


# ──────────────────────────────────────────────────────────────────────────────
# Fila de trabajo interno
# ──────────────────────────────────────────────────────────────────────────────

class _FilaImport(NamedTuple):
    nombre_sugerido: str
    talla: str
    costo_sin_iva: float
    cantidad: int
    cb_generado: str
    inv_id: int | None       # None = NUEVO, int = ID existente


# ──────────────────────────────────────────────────────────────────────────────
# Columnas de la tabla
# ──────────────────────────────────────────────────────────────────────────────
COL_ESTADO    = 0
COL_NOMBRE    = 1
COL_TALLA     = 2
COL_COSTO     = 3
COL_CANTIDAD  = 4
COL_CB        = 5
COL_ELIMINAR  = 6


class CarguesPedidosWidget(QWidget):
    """
    Sub-panel que vive dentro de la pestaña 'Cargue de pedidos' en FacturasPanel.
    Flujo: Cargar PDF → revisar/editar tabla → Confirmar importación.
    """

    inventario_actualizado = Signal()   # emite cuando se confirma la importación

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filas: list[_FilaImport] = []
        self._build_ui()

    # ──────────────────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── Cabecera ──────────────────────────────────────────────────────
        cab = QHBoxLayout()
        t = QLabel("Cargue de Factura de Cascos al Inventario")
        f = QFont(); f.setBold(True); f.setPointSize(13)
        t.setFont(f); t.setStyleSheet("color:#1E293B;")
        cab.addWidget(t)
        cab.addStretch()
        root.addLayout(cab)

        info = QLabel(
            "Selecciona el proveedor, carga el PDF del pedido y el sistema extrae los cascos, "
            "sugiere nombres y genera códigos de barras. "
            "Revisa, edita si es necesario y confirma para actualizar el inventario."
        )
        info.setWordWrap(True)
        info.setStyleSheet(
            "font-size:11px;color:#6B7280;"
            "background:#F8FAFC;border:1px solid #E2E8F0;"
            "border-radius:6px;padding:8px 12px;"
        )
        root.addWidget(info)

        # ── Selector de proveedor ─────────────────────────────────────────
        prov_row = QHBoxLayout(); prov_row.setSpacing(10)
        lbl_prov = QLabel("Proveedor:")
        lbl_prov.setStyleSheet("font-size:12px;font-weight:bold;color:#374151;")
        self._combo_proveedor = QComboBox()
        self._combo_proveedor.addItems([
            "— Seleccione proveedor —",
            "ACCESORIOS PARA MOTOS S.A.S.  (XTRONG)",
            "DISTRIFABRICA RAMIREZ SAS  (SHAFT / HRO / ICH)",
            "Otro proveedor",
        ])
        self._combo_proveedor.setFixedHeight(32)
        self._combo_proveedor.setStyleSheet(
            "QComboBox{border:1px solid #D1D5DB;border-radius:6px;"
            "padding:0 10px;font-size:12px;background:white;}"
            "QComboBox::drop-down{border:none;}"
        )
        prov_row.addWidget(lbl_prov)
        prov_row.addWidget(self._combo_proveedor)
        prov_row.addStretch()
        root.addLayout(prov_row)

        # ── Barra de carga ────────────────────────────────────────────────
        barra = QHBoxLayout(); barra.setSpacing(10)

        self._btn_cargar = QPushButton("📂  Cargar PDF de Pedido")
        self._btn_cargar.setFixedHeight(36)
        self._btn_cargar.setStyleSheet(
            "QPushButton{background:#2563EB;color:white;border:none;"
            "border-radius:6px;padding:0 18px;font-size:12px;font-weight:bold;}"
            "QPushButton:hover{background:#1D4ED8;}"
        )
        self._btn_cargar.clicked.connect(self._on_cargar_pdf)

        self._lbl_archivo = QLabel("Ningún archivo cargado")
        self._lbl_archivo.setStyleSheet("font-size:11px;color:#6B7280;")

        self._lbl_resumen = QLabel("")
        self._lbl_resumen.setStyleSheet(
            "font-size:11px;font-weight:bold;color:#0369A1;"
            "background:#EFF6FF;border:1px solid #BAE6FD;"
            "border-radius:5px;padding:4px 10px;"
        )
        self._lbl_resumen.setVisible(False)

        barra.addWidget(self._btn_cargar)
        barra.addWidget(self._lbl_archivo, stretch=1)
        barra.addWidget(self._lbl_resumen)
        root.addLayout(barra)

        # ── Tabla de revisión ─────────────────────────────────────────────
        self._tabla = QTableWidget()
        self._tabla.setColumnCount(7)
        self._tabla.setHorizontalHeaderLabels([
            "Estado", "Nombre en inventario (editable)", "Talla",
            "Costo unit.", "Cantidad", "Código barras", ""
        ])
        self._tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla.setAlternatingRowColors(True)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.setShowGrid(False)
        self._tabla.setStyleSheet("""
            QTableWidget{border:none;font-size:11px;}
            QTableWidget::item{padding:3px 8px;}
            QHeaderView::section{
                background:#1E293B;color:white;
                font-weight:bold;font-size:10px;
                padding:5px;border:none;
            }
            QTableWidget::item:selected{background:#FEF9C3;color:#78350F;}
        """)
        hh = self._tabla.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(COL_ESTADO,    QHeaderView.Fixed);    self._tabla.setColumnWidth(COL_ESTADO,    90)
        hh.setSectionResizeMode(COL_NOMBRE,    QHeaderView.Stretch)
        hh.setSectionResizeMode(COL_TALLA,     QHeaderView.Fixed);    self._tabla.setColumnWidth(COL_TALLA,     52)
        hh.setSectionResizeMode(COL_COSTO,     QHeaderView.Fixed);    self._tabla.setColumnWidth(COL_COSTO,    105)
        hh.setSectionResizeMode(COL_CANTIDAD,  QHeaderView.Fixed);    self._tabla.setColumnWidth(COL_CANTIDAD,  70)
        hh.setSectionResizeMode(COL_CB,        QHeaderView.Fixed);    self._tabla.setColumnWidth(COL_CB,       115)
        hh.setSectionResizeMode(COL_ELIMINAR,  QHeaderView.Fixed);    self._tabla.setColumnWidth(COL_ELIMINAR,  38)
        self._tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        root.addWidget(self._tabla, stretch=1)

        # ── Botones de acción ─────────────────────────────────────────────
        pie = QHBoxLayout(); pie.setSpacing(10)

        self._lbl_leyenda = QLabel(
            "🟢 NUEVO = se crea en inventario   "
            "🔵 SUMA = se suma la cantidad al existente"
        )
        self._lbl_leyenda.setStyleSheet("font-size:10px;color:#6B7280;")

        self._btn_confirmar = QPushButton("✔  Confirmar e Importar al Inventario")
        self._btn_confirmar.setFixedHeight(36)
        self._btn_confirmar.setEnabled(False)
        self._btn_confirmar.setStyleSheet(
            "QPushButton{background:#15803D;color:white;border:none;"
            "border-radius:6px;padding:0 20px;font-size:12px;font-weight:bold;}"
            "QPushButton:hover{background:#166534;}"
            "QPushButton:disabled{background:#9CA3AF;}"
        )
        self._btn_confirmar.clicked.connect(self._on_confirmar)

        self._btn_limpiar = QPushButton("Limpiar")
        self._btn_limpiar.setFixedHeight(36)
        self._btn_limpiar.setEnabled(False)
        self._btn_limpiar.setStyleSheet(
            "QPushButton{border:1px solid #D1D5DB;border-radius:6px;"
            "background:white;padding:0 16px;font-size:12px;}"
            "QPushButton:hover{background:#F3F4F6;}"
            "QPushButton:disabled{color:#9CA3AF;}"
        )
        self._btn_limpiar.clicked.connect(self._limpiar)

        pie.addWidget(self._lbl_leyenda)
        pie.addStretch()
        pie.addWidget(self._btn_limpiar)
        pie.addWidget(self._btn_confirmar)
        root.addLayout(pie)

    # ──────────────────────────────────────────────────────────────────────
    # Cargar PDF
    # ──────────────────────────────────────────────────────────────────────

    def _on_cargar_pdf(self):
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar factura de pedido",
            str(Path.home()), "PDF (*.pdf)"
        )
        if not ruta:
            return

        self._lbl_archivo.setText(Path(ruta).name)
        self._tabla.setRowCount(0)
        self._filas.clear()
        self._btn_confirmar.setEnabled(False)
        self._btn_limpiar.setEnabled(False)
        self._lbl_resumen.setVisible(False)

        seleccion = self._combo_proveedor.currentText()

        # ── Validar que se haya seleccionado proveedor ────────────────────
        if seleccion.startswith("—"):
            QMessageBox.warning(
                self, "Selecciona un proveedor",
                "Debes seleccionar el proveedor antes de cargar el PDF.\n\n"
                "Elige entre ACCESORIOS PARA MOTOS, DISTRIFABRICA o 'Otro proveedor'."
            )
            return

        es_distrifabrica = "DISTRIFABRICA" in seleccion
        es_otro = "Otro" in seleccion

        try:
            from services.pdf_pedido_parser import parsear_pdf, generar_codigos_barras
            from services.pdf_distrifabrica_parser import (
                parsear_pdf_distrifabrica, generar_codigos_barras_distrifabrica,
            )

            if es_distrifabrica:
                items = parsear_pdf_distrifabrica(ruta)
                _gen_cbs = generar_codigos_barras_distrifabrica
            elif es_otro:
                # Intentar con ambos parsers: primero ACCESORIOS, luego DISTRIFABRICA
                items = parsear_pdf(ruta)
                _gen_cbs = generar_codigos_barras
                if not items:
                    items = parsear_pdf_distrifabrica(ruta)
                    _gen_cbs = generar_codigos_barras_distrifabrica
            else:
                items = parsear_pdf(ruta)
                _gen_cbs = generar_codigos_barras
        except ImportError as exc:
            QMessageBox.critical(self, "Dependencia faltante", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Error al leer el PDF", str(exc))
            return

        if not items:
            if es_otro:
                QMessageBox.warning(
                    self, "Formato no reconocido",
                    "No se pudieron extraer datos de este PDF.\n\n"
                    "El formato no coincide con los proveedores conocidos "
                    "(ACCESORIOS PARA MOTOS S.A.S. ni DISTRIFABRICA RAMIREZ SAS).\n\n"
                    "Si es un proveedor nuevo, comparte una factura de muestra para agregar soporte."
                )
            elif es_distrifabrica:
                QMessageBox.information(
                    self, "Sin ítems",
                    "No se encontraron cascos en el PDF de DISTRIFABRICA RAMIREZ SAS.\n"
                    "Verifica que el archivo sea el correcto."
                )
            else:
                QMessageBox.information(
                    self, "Sin ítems",
                    "No se encontraron cascos XTRONG en el PDF.\n"
                    "Verifica que el archivo sea una factura de ACCESORIOS PARA MOTOS S.A.S."
                )
            return

        # Generar códigos de barras
        try:
            cbs = _gen_cbs(items)
        except Exception:
            cbs = {}

        # Verificar si ya existen en inventario
        from database.inventario_repo import obtener_producto_por_nombre_exacto

        filas: list[_FilaImport] = []
        for i, item in enumerate(items):
            cb = cbs.get(i, "")
            existente = obtener_producto_por_nombre_exacto(item.nombre_sugerido)
            filas.append(_FilaImport(
                nombre_sugerido=item.nombre_sugerido,
                talla=item.talla,
                costo_sin_iva=item.costo_sin_iva,
                cantidad=item.cantidad,
                cb_generado=cb,
                inv_id=existente.id if existente else None,
            ))

        self._filas = filas
        self._poblar_tabla()
        n_new  = sum(1 for f in filas if f.inv_id is None)
        n_suma = len(filas) - n_new
        self._lbl_resumen.setText(
            f"{len(filas)} cascos  •  🟢 {n_new} nuevos  •  🔵 {n_suma} suman stock"
        )
        self._lbl_resumen.setVisible(True)
        self._btn_confirmar.setEnabled(True)
        self._btn_limpiar.setEnabled(True)

    # ──────────────────────────────────────────────────────────────────────
    # Poblar tabla
    # ──────────────────────────────────────────────────────────────────────

    def _poblar_tabla(self):
        self._tabla.setRowCount(0)
        self._tabla.setRowCount(len(self._filas))

        for row, fila in enumerate(self._filas):
            self._tabla.setRowHeight(row, 30)

            # Col 0 — Estado
            es_nuevo = fila.inv_id is None
            badge = QLabel("  NUEVO  " if es_nuevo else f"SUMA +{fila.cantidad}")
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedHeight(22)
            if es_nuevo:
                badge.setStyleSheet(
                    "background:#DCFCE7;color:#15803D;font-size:9px;"
                    "font-weight:bold;border-radius:4px;"
                )
            else:
                badge.setStyleSheet(
                    "background:#DBEAFE;color:#1D4ED8;font-size:9px;"
                    "font-weight:bold;border-radius:4px;"
                )
            cont = QWidget()
            lay  = QHBoxLayout(cont); lay.setContentsMargins(4,4,4,4)
            lay.addWidget(badge)
            self._tabla.setCellWidget(row, COL_ESTADO, cont)

            # Col 1 — Nombre (editable inline)
            editor = QLineEdit(fila.nombre_sugerido)
            editor.setStyleSheet(
                "QLineEdit{border:none;background:transparent;font-size:10px;padding:0 4px;}"
                "QLineEdit:focus{background:#FFFBEB;border:1px solid #FDE68A;border-radius:3px;}"
            )
            editor.textChanged.connect(lambda txt, r=row: self._on_nombre_editado(r, txt))
            self._tabla.setCellWidget(row, COL_NOMBRE, editor)

            # Col 2 — Talla
            it_t = QTableWidgetItem(fila.talla)
            it_t.setTextAlignment(Qt.AlignCenter)
            it_t.setForeground(QColor("#374151"))
            self._tabla.setItem(row, COL_TALLA, it_t)

            # Col 3 — Costo
            it_c = QTableWidgetItem(cop(fila.costo_sin_iva))
            it_c.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._tabla.setItem(row, COL_COSTO, it_c)

            # Col 4 — Cantidad
            it_q = QTableWidgetItem(str(fila.cantidad))
            it_q.setTextAlignment(Qt.AlignCenter)
            self._tabla.setItem(row, COL_CANTIDAD, it_q)

            # Col 5 — Código de barras
            it_cb = QTableWidgetItem(fila.cb_generado or "—")
            it_cb.setTextAlignment(Qt.AlignCenter)
            it_cb.setForeground(QColor("#6B7280") if es_nuevo else QColor("#374151"))
            self._tabla.setItem(row, COL_CB, it_cb)

            # Col 6 — Eliminar
            btn_x = QPushButton("✕")
            btn_x.setFixedSize(26, 26)
            btn_x.setStyleSheet(
                "QPushButton{border:none;background:transparent;color:#9CA3AF;font-size:13px;}"
                "QPushButton:hover{color:#EF4444;background:#FEE2E2;border-radius:4px;}"
            )
            btn_x.setToolTip("Quitar de la importación")
            btn_x.clicked.connect(lambda _, r=row: self._eliminar_fila(r))
            cont_x = QWidget()
            lx = QHBoxLayout(cont_x); lx.setContentsMargins(4, 2, 4, 2)
            lx.addWidget(btn_x)
            self._tabla.setCellWidget(row, COL_ELIMINAR, cont_x)

    def _eliminar_fila(self, row: int):
        """Quita una fila de la lista de importación y refresca la tabla."""
        if row < 0 or row >= len(self._filas):
            return
        self._filas.pop(row)
        self._poblar_tabla()
        if self._filas:
            n_new  = sum(1 for f in self._filas if f.inv_id is None)
            n_suma = len(self._filas) - n_new
            self._lbl_resumen.setText(
                f"{len(self._filas)} cascos  •  🟢 {n_new} nuevos  •  🔵 {n_suma} suman stock"
            )
        else:
            self._lbl_resumen.setVisible(False)
            self._btn_confirmar.setEnabled(False)

    def _on_nombre_editado(self, row: int, nuevo_nombre: str):
        """Actualiza el nombre sugerido y re-verifica si existe en inventario."""
        if row >= len(self._filas):
            return
        f = self._filas[row]
        from database.inventario_repo import obtener_producto_por_nombre_exacto
        existente = obtener_producto_por_nombre_exacto(nuevo_nombre.strip())
        self._filas[row] = _FilaImport(
            nombre_sugerido=nuevo_nombre.strip(),
            talla=f.talla,
            costo_sin_iva=f.costo_sin_iva,
            cantidad=f.cantidad,
            cb_generado=f.cb_generado,
            inv_id=existente.id if existente else None,
        )
        # Actualizar badge de estado
        es_nuevo = existente is None
        badge = QLabel("  NUEVO  " if es_nuevo else f"SUMA +{f.cantidad}")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(22)
        if es_nuevo:
            badge.setStyleSheet(
                "background:#DCFCE7;color:#15803D;font-size:9px;"
                "font-weight:bold;border-radius:4px;"
            )
        else:
            badge.setStyleSheet(
                "background:#DBEAFE;color:#1D4ED8;font-size:9px;"
                "font-weight:bold;border-radius:4px;"
            )
        cont = QWidget()
        lay  = QHBoxLayout(cont); lay.setContentsMargins(4, 4, 4, 4)
        lay.addWidget(badge)
        self._tabla.setCellWidget(row, COL_ESTADO, cont)

    # ──────────────────────────────────────────────────────────────────────
    # Confirmar importación
    # ──────────────────────────────────────────────────────────────────────

    def _on_confirmar(self):
        if not self._filas:
            return

        n_new = sum(1 for f in self._filas if f.inv_id is None)
        n_sum = len(self._filas) - n_new
        resp = QMessageBox.question(
            self, "Confirmar importación",
            f"<b>Se van a realizar los siguientes cambios:</b><br><br>"
            f"🟢  <b>{n_new}</b> referencias nuevas se crearán en inventario.<br>"
            f"🔵  <b>{n_sum}</b> referencias existentes recibirán stock adicional.<br><br>"
            f"¿Confirmas la importación?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if resp != QMessageBox.Yes:
            return

        from database.connection import DatabaseConnection
        from database.inventario_repo import (
            obtener_todos_productos,
            insertar_producto,
        )
        from models.producto import Producto

        conn = DatabaseConnection.get()
        creados = 0
        sumados = 0
        errores = 0

        # Leer nombre actualizado del editor en la tabla
        for row, fila in enumerate(self._filas):
            editor = self._tabla.cellWidget(row, COL_NOMBRE)
            nombre_final = editor.text().strip() if editor else fila.nombre_sugerido

            try:
                if fila.inv_id is not None:
                    # Sumar cantidad al existente
                    conn.execute(
                        "UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?",
                        (fila.cantidad, fila.inv_id),
                    )
                    sumados += 1
                else:
                    # Crear nueva referencia
                    # Obtener siguiente serial
                    max_s = conn.execute(
                        "SELECT MAX(CAST(serial AS INTEGER)) FROM inventario WHERE serial GLOB '[0-9]*'"
                    ).fetchone()[0] or 0
                    nuevo_serial = str(int(max_s) + 1)

                    conn.execute(
                        """INSERT INTO inventario
                           (serial, producto, costo_unitario, cantidad, codigo_barras)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            nuevo_serial,
                            nombre_final,
                            round(fila.costo_sin_iva),
                            fila.cantidad,
                            fila.cb_generado,
                        ),
                    )
                    creados += 1
            except Exception:
                errores += 1

        conn.commit()

        msg = f"Importación completada:\n\n✅ {creados} referencias creadas\n✅ {sumados} referencias actualizadas"
        if errores:
            msg += f"\n⚠ {errores} errores (revisa los datos)"
        QMessageBox.information(self, "Importación finalizada", msg)

        self.inventario_actualizado.emit()
        self._limpiar()

    # ──────────────────────────────────────────────────────────────────────
    # Limpiar
    # ──────────────────────────────────────────────────────────────────────

    def _limpiar(self):
        self._tabla.setRowCount(0)
        self._filas.clear()
        self._lbl_archivo.setText("Ningún archivo cargado")
        self._lbl_resumen.setVisible(False)
        self._btn_confirmar.setEnabled(False)
        self._btn_limpiar.setEnabled(False)
