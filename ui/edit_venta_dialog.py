"""
ui/edit_venta_dialog.py
Diálogo modal para editar una venta existente.
Reutiliza los mismos campos de VentaForm pero en modo actualización.
"""

from datetime import date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit,
    QPushButton, QDateEdit, QFrame, QMessageBox,
    QWidget, QSpinBox,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont

from models.venta import Venta
from controllers.venta_controller import VentaController
from utils.formatters import cop, porcentaje
from ui.venta_form import MoneyLineEdit, METODOS_PAGO, TRANSFERENCIA_SUBTIPOS, _fmt


class EditVentaDialog(QDialog):
    """
    Modal de edición de venta.
    Emite venta_actualizada(Venta) cuando se guarda con éxito.
    """

    venta_actualizada = Signal(object)   # Venta

    def __init__(self, venta: Venta, parent=None) -> None:
        super().__init__(parent)
        self._venta_original = venta
        self._ctrl = VentaController()
        self._filas_pago: list[tuple] = []   # (QComboBox, MoneyLineEdit, QWidget)
        self.setWindowTitle(f"Editar venta — {venta.producto}")
        self.setMinimumWidth(700)
        self.setModal(True)
        self._build_ui()
        self._connect_signals()   # Conectar ANTES de precargar para que los signals funcionen
        self._precargar(venta)
        self._actualizar_preview()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        titulo = QLabel("Editar Venta")
        font = QFont(); font.setPointSize(14); font.setBold(True)
        titulo.setFont(font)
        root.addWidget(titulo)

        body = QHBoxLayout()
        body.setSpacing(20)
        body.addWidget(self._panel_campos(), stretch=3)
        body.addWidget(self._sep_v())
        body.addWidget(self._panel_preview(), stretch=2)
        root.addLayout(body)

        root.addWidget(self._sep_h())
        root.addLayout(self._botones())

    def _panel_campos(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.campo_fecha = QDateEdit()
        self.campo_fecha.setCalendarPopup(True)
        self.campo_fecha.setDisplayFormat("dd/MM/yyyy")
        self.campo_fecha.setFixedHeight(32)
        form.addRow("Fecha:", self.campo_fecha)

        self.campo_producto = QLineEdit()
        self.campo_producto.setFixedHeight(32)
        form.addRow("Producto:", self.campo_producto)

        self.campo_costo = MoneyLineEdit()
        self.campo_costo.setFixedHeight(32)
        form.addRow("Costo ($):", self.campo_costo)

        self.campo_precio = MoneyLineEdit()
        self.campo_precio.setFixedHeight(32)
        form.addRow("Precio venta ($):", self.campo_precio)

        self.campo_cantidad = QSpinBox()
        self.campo_cantidad.setMinimum(1)
        self.campo_cantidad.setMaximum(999)
        self.campo_cantidad.setValue(1)
        self.campo_cantidad.setFixedHeight(32)
        self.campo_cantidad.setPrefix("× ")
        form.addRow("Cantidad:", self.campo_cantidad)

        # Método de pago con toggle combinado
        fila_metodo = QHBoxLayout()
        fila_metodo.setSpacing(6)
        fila_metodo.setContentsMargins(0, 0, 0, 0)
        self.campo_metodo = QComboBox()
        self.campo_metodo.addItems(METODOS_PAGO)
        self.campo_metodo.setFixedHeight(32)
        self._btn_combinado = QPushButton("Combinado")
        self._btn_combinado.setCheckable(True)
        self._btn_combinado.setFixedHeight(32)
        self._btn_combinado.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 10px; font-size:12px; background:white; color:#374151; }"
            "QPushButton:hover { background:#F3F4F6; }"
            "QPushButton:checked { background:#DBEAFE; color:#1D4ED8;"
            "border-color:#93C5FD; font-weight:bold; }"
        )
        fila_metodo.addWidget(self.campo_metodo)
        fila_metodo.addWidget(self._btn_combinado)
        metodo_widget = QWidget()
        metodo_widget.setLayout(fila_metodo)
        metodo_widget.setFixedHeight(32)
        form.addRow("Método de pago:", metodo_widget)

        # Sub-tipo de transferencia (oculto por defecto)
        self.lbl_sub_transferencia = QLabel("Tipo transferencia:")
        self.campo_sub_transferencia = QComboBox()
        self.campo_sub_transferencia.addItems(TRANSFERENCIA_SUBTIPOS)
        self.campo_sub_transferencia.setFixedHeight(32)
        form.addRow(self.lbl_sub_transferencia, self.campo_sub_transferencia)
        self.lbl_sub_transferencia.setVisible(False)
        self.campo_sub_transferencia.setVisible(False)

        # Panel combinado
        self._panel_combinado = self._build_panel_combinado()
        form.addRow("", self._panel_combinado)
        self._panel_combinado.setVisible(False)

        self.campo_notas = QTextEdit()
        self.campo_notas.setFixedHeight(60)
        self.campo_notas.setTabChangesFocus(True)
        form.addRow("Notas:", self.campo_notas)

        return w

    def _panel_preview(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 0, 0, 0)
        lay.setSpacing(8)

        self.lbl_bruta_t = QLabel("Ganancia Bruta")
        self.lbl_bruta_t.setStyleSheet("color: #6B7280; font-size: 10px;")
        self.lbl_bruta = QLabel("$ 0")
        f = QFont(); f.setPointSize(13); f.setBold(True)
        self.lbl_bruta.setFont(f)
        lay.addWidget(self.lbl_bruta_t)
        lay.addWidget(self.lbl_bruta)
        lay.addWidget(self._sep_h())

        self.lbl_com_t = QLabel("Comisión (0.00 %)")
        self.lbl_com_t.setStyleSheet("color: #6B7280; font-size: 10px;")
        self.lbl_com = QLabel("$ 0")
        self.lbl_com.setFont(f)
        self.lbl_com.setStyleSheet("color: #EF4444;")
        lay.addWidget(self.lbl_com_t)
        lay.addWidget(self.lbl_com)
        lay.addWidget(self._sep_h())

        self.lbl_neta_t = QLabel("Ganancia Neta")
        self.lbl_neta_t.setStyleSheet("color: #6B7280; font-size: 10px;")
        self.lbl_neta = QLabel("$ 0")
        fn = QFont(); fn.setPointSize(18); fn.setBold(True)
        self.lbl_neta.setFont(fn)
        lay.addWidget(self.lbl_neta_t)
        lay.addWidget(self.lbl_neta)

        self.lbl_ind = QLabel("")
        self.lbl_ind.setAlignment(Qt.AlignCenter)
        self.lbl_ind.setFixedHeight(30)
        lay.addWidget(self.lbl_ind)
        lay.addStretch()
        return w

    def _build_panel_combinado(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(
            "QWidget#panelComb { background:#F0F9FF; border:1px solid #BAE6FD;"
            "border-radius:6px; }"
        )
        w.setObjectName("panelComb")
        outer = QVBoxLayout(w)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(5)

        self._pagos_container = QWidget()
        self._pagos_container.setStyleSheet("background:transparent;")
        self._pagos_layout = QVBoxLayout(self._pagos_container)
        self._pagos_layout.setContentsMargins(0, 0, 0, 0)
        self._pagos_layout.setSpacing(4)
        outer.addWidget(self._pagos_container)

        btn_add = QPushButton("+ Agregar método")
        btn_add.setFixedHeight(26)
        btn_add.setStyleSheet(
            "QPushButton { background:#E0F2FE; color:#0369A1; border:1px solid #7DD3FC;"
            "border-radius:4px; font-size:11px; font-weight:bold; padding:0 10px; }"
            "QPushButton:hover { background:#BAE6FD; }"
        )
        btn_add.clicked.connect(self._on_agregar_pago)
        outer.addWidget(btn_add)

        self._lbl_pagos_status = QLabel("Asignado: $ 0  /  Total: $ 0")
        self._lbl_pagos_status.setStyleSheet(
            "font-size:11px; color:#374151; background:transparent;"
        )
        outer.addWidget(self._lbl_pagos_status)
        return w

    def _agregar_fila_pago(self, metodo: str = "Efectivo", monto: int = 0) -> None:
        row_w = QWidget()
        row_w.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(row_w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        combo = QComboBox()
        combo.addItems(METODOS_PAGO)
        combo.setCurrentText(metodo)
        combo.setFixedHeight(28)
        combo.setStyleSheet("""
            QComboBox {
                background: white; color: #1E293B;
                border: 1px solid #D1D5DB; border-radius: 4px; padding: 0 8px;
            }
            QComboBox::drop-down { border: none; width: 18px; }
            QComboBox QAbstractItemView {
                background: white; color: #1E293B;
                selection-background-color: #DBEAFE; selection-color: #1E3A5F;
                border: 1px solid #BFDBFE;
            }
        """)

        monto_edit = MoneyLineEdit()
        monto_edit.setPlaceholderText("0")
        monto_edit.setFixedHeight(28)
        if monto:
            monto_edit.set_valor(monto)

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(26, 26)
        btn_del.setStyleSheet(
            "QPushButton { background:#FEE2E2; color:#DC2626; border:1px solid #FECACA;"
            "border-radius:4px; font-size:11px; }"
            "QPushButton:hover { background:#FECACA; }"
        )

        lay.addWidget(combo, stretch=2)
        lay.addWidget(monto_edit, stretch=2)
        lay.addWidget(btn_del)

        combo.currentTextChanged.connect(self._actualizar_preview)
        monto_edit.textChanged.connect(self._actualizar_status_combinado)
        monto_edit.textChanged.connect(self._actualizar_preview)
        btn_del.clicked.connect(lambda _=False, w=row_w: self._eliminar_fila_pago(w))

        self._pagos_layout.addWidget(row_w)
        self._filas_pago.append((combo, monto_edit, row_w))
        self._actualizar_status_combinado()

    def _eliminar_fila_pago(self, row_w: QWidget) -> None:
        self._filas_pago = [(c, m, w) for c, m, w in self._filas_pago if w is not row_w]
        row_w.setParent(None)
        row_w.deleteLater()
        self._actualizar_status_combinado()
        self._actualizar_preview()

    def _limpiar_filas_pago(self) -> None:
        for _, _, w in self._filas_pago:
            w.setParent(None)
            w.deleteLater()
        self._filas_pago = []

    def _on_agregar_pago(self) -> None:
        self._agregar_fila_pago()

    def _actualizar_status_combinado(self) -> None:
        asignado = sum(m.valor_int() for _, m, _ in self._filas_pago)
        precio = self._int(self.campo_precio.text())
        total = precio * self.campo_cantidad.value()
        color = "#15803D" if asignado == total and total > 0 else (
            "#DC2626" if asignado > total else "#374151"
        )
        self._lbl_pagos_status.setText(
            f"Asignado: {_fmt(asignado)}  /  Total: {_fmt(total)}"
        )
        self._lbl_pagos_status.setStyleSheet(
            f"font-size:11px; color:{color}; background:transparent;"
        )

    def _get_pagos_combinados(self) -> list | None:
        if not self._btn_combinado.isChecked():
            return None
        pagos = []
        for combo, monto_edit, _ in self._filas_pago:
            monto = monto_edit.valor_int()
            if monto > 0:
                pagos.append({"metodo": combo.currentText(), "monto": float(monto)})
        return pagos if pagos else None

    def _on_toggle_combinado(self, activo: bool) -> None:
        self.campo_metodo.setEnabled(not activo)
        self.lbl_sub_transferencia.setVisible(False)
        self.campo_sub_transferencia.setVisible(False)
        self._panel_combinado.setVisible(activo)
        if activo and not self._filas_pago:
            self._agregar_fila_pago("Efectivo", 0)
            self._agregar_fila_pago("Bold", 0)
        elif not activo:
            self._limpiar_filas_pago()
        self._actualizar_preview()

    def _botones(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.addStretch()

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setFixedHeight(36)
        self.btn_cancelar.setStyleSheet(
            "QPushButton { border: 1px solid #D1D5DB; border-radius: 5px; padding: 0 16px; }"
            "QPushButton:hover { background-color: #F3F4F6; }"
        )
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Actualizar Venta")
        self.btn_guardar.setFixedHeight(36)
        self.btn_guardar.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: white; border-radius: 5px; padding: 0 20px; font-weight: bold; }"
            "QPushButton:hover { background-color: #1D4ED8; }"
        )
        self.btn_guardar.clicked.connect(self._on_guardar)

        lay.addWidget(self.btn_cancelar)
        lay.addWidget(self.btn_guardar)
        return lay

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _sep_v(self) -> QFrame:
        s = QFrame(); s.setFrameShape(QFrame.VLine)
        s.setStyleSheet("color: #E5E7EB;")
        return s

    def _sep_h(self) -> QFrame:
        s = QFrame(); s.setFrameShape(QFrame.HLine)
        s.setStyleSheet("color: #E5E7EB;")
        return s

    # ------------------------------------------------------------------
    # Precarga y señales
    # ------------------------------------------------------------------

    def _precargar(self, v: Venta) -> None:
        self.campo_fecha.setDate(QDate(v.fecha.year, v.fecha.month, v.fecha.day))
        self.campo_producto.setText(v.producto)
        self.campo_costo.set_valor(int(v.costo))
        self.campo_precio.set_valor(int(v.precio))
        self.campo_cantidad.setValue(v.cantidad)
        self.campo_notas.setPlainText(v.notas)

        if v.pagos_combinados:
            # Activar modo combinado y poblar filas
            self._btn_combinado.setChecked(True)
            for pago in v.pagos_combinados:
                self._agregar_fila_pago(pago["metodo"], int(pago["monto"]))
        else:
            metodo_base, sub = self._split_metodo(v.metodo_pago)
            idx = self.campo_metodo.findText(metodo_base)
            if idx >= 0:
                self.campo_metodo.setCurrentIndex(idx)
            if sub:
                idx_sub = self.campo_sub_transferencia.findText(sub)
                if idx_sub >= 0:
                    self.campo_sub_transferencia.setCurrentIndex(idx_sub)

    def _connect_signals(self) -> None:
        self.campo_costo.textChanged.connect(self._actualizar_preview)
        self.campo_precio.textChanged.connect(self._actualizar_preview)
        self.campo_precio.textChanged.connect(self._actualizar_status_combinado)
        self.campo_cantidad.valueChanged.connect(self._actualizar_preview)
        self.campo_cantidad.valueChanged.connect(self._actualizar_status_combinado)
        self.campo_metodo.currentTextChanged.connect(self._on_metodo_changed)
        self.campo_sub_transferencia.currentTextChanged.connect(self._actualizar_preview)
        self._btn_combinado.toggled.connect(self._on_toggle_combinado)

    def _on_metodo_changed(self, metodo: str) -> None:
        es_transferencia = (metodo == "Transferencia")
        self.lbl_sub_transferencia.setVisible(es_transferencia)
        self.campo_sub_transferencia.setVisible(es_transferencia)
        self._actualizar_preview()

    def _metodo_completo(self) -> str:
        metodo = self.campo_metodo.currentText()
        if metodo == "Transferencia":
            return f"Transferencia {self.campo_sub_transferencia.currentText()}"
        return metodo

    def _actualizar_preview(self) -> None:
        costo = self._int(self.campo_costo.text())
        precio = self._int(self.campo_precio.text())
        metodo = self._metodo_completo()
        pagos = self._get_pagos_combinados()
        data = self._ctrl.calcular_preview(
            costo, precio, metodo, self.campo_cantidad.value(), pagos
        )

        self.lbl_bruta.setText(cop(data["ganancia_bruta"]))
        if data.get("es_combinado"):
            self.lbl_com_t.setText("Comisión (combinada)")
        else:
            self.lbl_com_t.setText(f"Comisión ({porcentaje(data['porcentaje'], 2)})")
        self.lbl_com.setText(f"- {cop(data['comision'])}" if data["comision"] > 0 else cop(0))

        neta = data["ganancia_neta"]
        self.lbl_neta.setText(cop(neta))
        if neta > 0:
            self.lbl_neta.setStyleSheet("color: #16A34A;")
            self.lbl_ind.setText("GANANCIA")
            self.lbl_ind.setStyleSheet(
                "border-radius:6px; font-weight:bold; background:#DCFCE7; color:#15803D;"
            )
        elif neta < 0:
            self.lbl_neta.setStyleSheet("color: #DC2626;")
            self.lbl_ind.setText("PÉRDIDA")
            self.lbl_ind.setStyleSheet(
                "border-radius:6px; font-weight:bold; background:#FEE2E2; color:#DC2626;"
            )
        else:
            self.lbl_neta.setStyleSheet("color: #374151;")
            self.lbl_ind.setText("")
            self.lbl_ind.setStyleSheet("")

    def _on_guardar(self) -> None:
        try:
            fq = self.campo_fecha.date()
            pagos = self._get_pagos_combinados()

            if pagos is not None:
                precio = float(self._int(self.campo_precio.text()))
                cantidad = self.campo_cantidad.value()
                total_esperado = int(precio) * cantidad
                total_asignado = sum(int(p["monto"]) for p in pagos)
                if total_asignado != total_esperado:
                    raise ValueError(
                        f"La suma de los pagos ({_fmt(total_asignado)}) debe ser igual "
                        f"al precio total ({_fmt(total_esperado)})."
                    )

            metodo = "Combinado" if pagos else self._metodo_completo()
            venta = Venta(
                id=self._venta_original.id,
                fecha=date(fq.year(), fq.month(), fq.day()),
                producto=self.campo_producto.text().strip(),
                costo=float(self._int(self.campo_costo.text())),
                precio=float(self._int(self.campo_precio.text())),
                metodo_pago=metodo,
                cantidad=self.campo_cantidad.value(),
                notas=self.campo_notas.toPlainText().strip(),
                pagos_combinados=pagos,
            )
            self._ctrl.actualizar_venta_existente(venta)
            self.venta_actualizada.emit(venta)
            self.accept()
        except ValueError as exc:
            QMessageBox.warning(self, "Dato inválido", str(exc))

    @staticmethod
    def _int(texto: str) -> int:
        """Convierte texto con o sin separadores de miles a entero."""
        try:
            limpio = "".join(c for c in texto if c.isdigit())
            return int(limpio) if limpio else 0
        except ValueError:
            return 0

    @staticmethod
    def _split_metodo(metodo_pago: str):
        """Descompone "Transferencia NEQUI" en ("Transferencia", "NEQUI")."""
        if metodo_pago.startswith("Transferencia "):
            sub = metodo_pago[len("Transferencia "):]
            return "Transferencia", sub
        return metodo_pago, ""
