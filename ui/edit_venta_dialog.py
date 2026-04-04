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
from ui.venta_form import MoneyLineEdit, METODOS_PAGO, TRANSFERENCIA_SUBTIPOS


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

        self.campo_metodo = QComboBox()
        self.campo_metodo.addItems(METODOS_PAGO)
        self.campo_metodo.setFixedHeight(32)
        form.addRow("Método de pago:", self.campo_metodo)

        # Sub-tipo de transferencia (oculto por defecto)
        self.lbl_sub_transferencia = QLabel("Tipo transferencia:")
        self.campo_sub_transferencia = QComboBox()
        self.campo_sub_transferencia.addItems(TRANSFERENCIA_SUBTIPOS)
        self.campo_sub_transferencia.setFixedHeight(32)
        form.addRow(self.lbl_sub_transferencia, self.campo_sub_transferencia)
        self.lbl_sub_transferencia.setVisible(False)
        self.campo_sub_transferencia.setVisible(False)

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

        metodo_base, sub = self._split_metodo(v.metodo_pago)
        idx = self.campo_metodo.findText(metodo_base)
        if idx >= 0:
            self.campo_metodo.setCurrentIndex(idx)
        if sub:
            idx_sub = self.campo_sub_transferencia.findText(sub)
            if idx_sub >= 0:
                self.campo_sub_transferencia.setCurrentIndex(idx_sub)

        self.campo_notas.setPlainText(v.notas)

    def _connect_signals(self) -> None:
        self.campo_costo.textChanged.connect(self._actualizar_preview)
        self.campo_precio.textChanged.connect(self._actualizar_preview)
        self.campo_cantidad.valueChanged.connect(self._actualizar_preview)
        self.campo_metodo.currentTextChanged.connect(self._on_metodo_changed)
        self.campo_sub_transferencia.currentTextChanged.connect(self._actualizar_preview)

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
        data = self._ctrl.calcular_preview(costo, precio, metodo, self.campo_cantidad.value())

        self.lbl_bruta.setText(cop(data["ganancia_bruta"]))
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
            venta = Venta(
                id=self._venta_original.id,
                fecha=date(fq.year(), fq.month(), fq.day()),
                producto=self.campo_producto.text().strip(),
                costo=float(self._int(self.campo_costo.text())),
                precio=float(self._int(self.campo_precio.text())),
                metodo_pago=self._metodo_completo(),
                cantidad=self.campo_cantidad.value(),
                notas=self.campo_notas.toPlainText().strip(),
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
