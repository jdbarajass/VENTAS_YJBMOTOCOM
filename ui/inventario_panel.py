"""
ui/inventario_panel.py
Panel de gestión de inventario: tabla, formulario, importación desde Excel.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFrame, QFileDialog, QMessageBox,
    QSpinBox, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from database.inventario_repo import (
    obtener_todos_productos, insertar_producto,
    actualizar_producto, eliminar_producto, eliminar_todo_inventario,
)
from services.inventario_importador import importar_inventario_excel
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
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(12)

        root.addLayout(self._barra_superior())
        root.addWidget(self._panel_form())
        root.addWidget(self._build_tabla(), stretch=1)
        root.addWidget(self._barra_resumen())

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

        btn_nuevo = QPushButton("+ Nuevo Producto")
        btn_nuevo.setFixedHeight(34)
        btn_nuevo.setStyleSheet(
            "QPushButton { border:1px solid #2563EB; border-radius:5px; padding:0 14px;"
            "color:#2563EB; background:white; font-weight:bold; }"
            "QPushButton:hover { background:#EFF6FF; }"
        )
        btn_nuevo.clicked.connect(self._on_nuevo)

        btn_importar = QPushButton("⬆  Importar Excel")
        btn_importar.setFixedHeight(34)
        btn_importar.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:5px;"
            "padding:0 14px; font-weight:bold; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btn_importar.clicked.connect(self._on_importar)

        lay.addWidget(titulo)
        lay.addSpacing(16)
        lay.addWidget(self._campo_busqueda)
        lay.addStretch()
        lay.addWidget(btn_nuevo)
        lay.addWidget(btn_importar)
        return lay

    def _panel_form(self) -> QFrame:
        """Formulario colapsable para agregar / editar un producto."""
        self._frame_form = QFrame()
        self._frame_form.setObjectName("formFrame")
        self._frame_form.setStyleSheet(
            "QFrame#formFrame { background:#F0F9FF; border:1px solid #BAE6FD;"
            "border-radius:8px; }"
        )
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
                "QLineEdit { border:1px solid #D1D5DB; border-radius:4px;"
                "padding:0 8px; background:white; }"
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
            "QLineEdit { border:1px solid #D1D5DB; border-radius:4px;"
            "padding:0 8px; background:white; }"
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

        # Fila 2: cantidad | código de barras
        self._f_cantidad = QSpinBox()
        self._f_cantidad.setMinimum(0); self._f_cantidad.setMaximum(99999)
        self._f_cantidad.setFixedHeight(30); self._f_cantidad.setFixedWidth(100)
        self._f_cantidad.setStyleSheet(
            "QSpinBox { border:1px solid #D1D5DB; border-radius:4px;"
            "padding:0 6px; background:white; }"
        )

        self._f_barras = _field("Código de barras", 180)

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
            "QPushButton { border:1px solid #D1D5DB; border-radius:4px;"
            "padding:0 14px; background:white; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_cancelar.clicked.connect(self._on_cancelar_form)

        for w, l in [
            (self._f_cantidad, "Cantidad:"),
            (self._f_barras,   "Código de barras:"),
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
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "Serial", "Producto", "Costo Unitario",
            "Cantidad", "Código de Barras", "Acciones"
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
        """)

        hh = self.tabla.horizontalHeader()
        hh.setSectionResizeMode(1, QHeaderView.Fixed);  self.tabla.setColumnWidth(1, 90)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.Fixed);  self.tabla.setColumnWidth(3, 130)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);  self.tabla.setColumnWidth(4, 90)
        hh.setSectionResizeMode(5, QHeaderView.Fixed);  self.tabla.setColumnWidth(5, 140)
        hh.setSectionResizeMode(6, QHeaderView.Fixed);  self.tabla.setColumnWidth(6, 120)

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

    def refresh(self) -> None:
        self._productos = obtener_todos_productos()
        self._campo_busqueda.clear()
        self._poblar_tabla(self._productos)
        self._actualizar_resumen(self._productos)

    def _filtrar(self, texto: str) -> None:
        if texto.strip():
            filtrados = [
                p for p in self._productos
                if texto.lower() in p.producto.lower()
                or texto.lower() in p.serial.lower()
                or texto.lower() in p.codigo_barras.lower()
            ]
        else:
            filtrados = self._productos
        self._poblar_tabla(filtrados)

    def _poblar_tabla(self, productos: list[Producto]) -> None:
        self.tabla.setRowCount(0)
        self.tabla.setRowCount(len(productos))

        for row, p in enumerate(productos):
            self.tabla.setRowHeight(row, 34)
            self.tabla.setItem(row, 0, QTableWidgetItem(str(p.id)))
            self._celda(row, 1, p.serial or "", Qt.AlignCenter)
            self._celda(row, 2, p.producto)
            self._celda(row, 3, cop(p.costo_unitario), Qt.AlignRight | Qt.AlignVCenter)

            # Cantidad con color
            item_cant = QTableWidgetItem(str(p.cantidad))
            item_cant.setTextAlignment(Qt.AlignCenter)
            if p.cantidad == 0:
                item_cant.setForeground(QColor("#DC2626"))
            elif p.cantidad <= 3:
                item_cant.setForeground(QColor("#D97706"))
            else:
                item_cant.setForeground(QColor("#15803D"))
            self.tabla.setItem(row, 4, item_cant)

            self._celda(row, 5, p.codigo_barras or "", Qt.AlignCenter)

            # Acciones
            self.tabla.setCellWidget(row, 6, self._widget_acciones(p.id))

    def _celda(self, row, col, texto, alin=Qt.AlignLeft | Qt.AlignVCenter):
        item = QTableWidgetItem(texto)
        item.setTextAlignment(alin)
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

        btn_editar = QPushButton("✎ Editar")
        btn_editar.setFixedHeight(26)
        btn_editar.setStyleSheet(
            "QPushButton { background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;"
            "border-radius:4px; font-size:11px; }"
            "QPushButton:hover { background:#DBEAFE; }"
        )
        btn_editar.clicked.connect(lambda _, pid=producto_id: self._on_editar(pid))

        btn_eliminar = QPushButton("🗑")
        btn_eliminar.setFixedHeight(26); btn_eliminar.setFixedWidth(30)
        btn_eliminar.setStyleSheet(
            "QPushButton { background:#FEF2F2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:13px; }"
            "QPushButton:hover { background:#FEE2E2; }"
        )
        btn_eliminar.clicked.connect(lambda _, pid=producto_id: self._on_eliminar(pid))

        lay.addWidget(btn_editar)
        lay.addWidget(btn_eliminar)
        return w

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_nuevo(self) -> None:
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
        p = next((x for x in self._productos if x.id == producto_id), None)
        if not p:
            return
        self._editando_id = producto_id
        self._lbl_form_titulo.setText("Editar Producto")
        self._btn_guardar_form.setText("Actualizar")
        self._f_serial.setText(p.serial)
        self._f_producto.setText(p.producto)
        self._f_costo.set_valor(int(p.costo_unitario))
        self._f_cantidad.setValue(p.cantidad)
        self._f_barras.setText(p.codigo_barras)
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

        try:
            p = Producto(
                serial=self._f_serial.text().strip(),
                producto=producto_nombre,
                costo_unitario=costo,
                cantidad=self._f_cantidad.value(),
                codigo_barras=self._f_barras.text().strip(),
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

    def _on_importar(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Excel de inventario", "", "Excel (*.xlsx)"
        )
        if not ruta:
            return

        resultado = importar_inventario_excel(Path(ruta))

        if resultado.errores and not resultado.productos:
            QMessageBox.critical(
                self, "Error al leer el archivo",
                "\n".join(resultado.errores)
            )
            return

        if not resultado.productos:
            QMessageBox.warning(self, "Sin datos",
                                "No se encontraron productos en el archivo.")
            return

        n = len(resultado.productos)
        existentes = len(self._productos)
        msg = (
            f"Se encontraron <b>{n} productos</b> en el archivo.<br><br>"
        )
        if existentes > 0:
            msg += (
                f"El inventario actual tiene <b>{existentes} productos</b> "
                f"que serán <b>reemplazados</b> completamente.<br><br>"
            )
        if resultado.errores:
            msg += f"<i>Advertencias: {'; '.join(resultado.errores[:3])}</i><br><br>"
        msg += "¿Continuar con la importación?"

        resp = QMessageBox.question(
            self, "Confirmar importación", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp != QMessageBox.Yes:
            return

        eliminar_todo_inventario()
        for p in resultado.productos:
            insertar_producto(p)

        QMessageBox.information(
            self, "Importación exitosa",
            f"Se importaron <b>{n} productos</b> al inventario correctamente."
        )
        self.refresh()
        self.inventario_actualizado.emit()

    def _limpiar_form(self) -> None:
        self._f_serial.clear()
        self._f_producto.clear()
        self._f_costo.clear()
        self._f_cantidad.setValue(0)
        self._f_barras.clear()
