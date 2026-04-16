"""
ui/presupuesto_panel.py
Comparativo mensual: presupuesto planificado vs. gasto real por categoría.

Layout:
  ─ Barra superior (título + selector mes/año + botones Guardar / Copiar mes ant.)
  ─ Info de contexto (gastos fijos de configuración)
  ─ Tabla comparativa (una fila por categoría + fila de totales)
"""

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QFrame,
    QScrollArea, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from database.presupuesto_repo import (
    obtener_presupuesto_mes,
    guardar_presupuesto_categoria,
    copiar_presupuesto_mes,
)
from database.gastos_dia_repo import obtener_totales_por_categoria
from database.config_repo import obtener_configuracion
from models.gasto_dia import CATEGORIAS_GASTO
from ui.venta_form import MoneyLineEdit
from utils.formatters import cop, MESES_ES


class PresupuestoPanel(QWidget):
    """
    Vista de presupuesto mensual vs. gasto real.
    El usuario asigna un monto por categoría de gasto; el panel calcula
    cuánto se gastó realmente en esa categoría ese mes.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._campos: dict[str, MoneyLineEdit] = {}   # categoria → campo editable
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background:#F1F5F9; border:none; }")

        contenido = QWidget()
        contenido.setStyleSheet("background:#F1F5F9;")
        root = QVBoxLayout(contenido)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(16)

        root.addLayout(self._barra_superior())
        root.addWidget(self._panel_gastos_fijos())
        root.addWidget(self._panel_tabla())
        root.addStretch()

        scroll.setWidget(contenido)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ---- Barra superior ----

    def _barra_superior(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        titulo = QLabel("Presupuesto Mensual")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)

        self._combo_mes = QComboBox()
        self._combo_mes.setFixedHeight(34)
        self._combo_mes.setFixedWidth(115)
        for num, nombre in MESES_ES.items():
            self._combo_mes.addItem(nombre, num)
        self._combo_mes.setCurrentIndex(date.today().month - 1)

        self._spin_anio = QSpinBox()
        self._spin_anio.setRange(2020, 2040)
        self._spin_anio.setValue(date.today().year)
        self._spin_anio.setFixedHeight(34)
        self._spin_anio.setFixedWidth(75)
        self._spin_anio.setButtonSymbols(QSpinBox.NoButtons)

        for w in (self._combo_mes, self._spin_anio):
            w.setStyleSheet(
                "QComboBox, QSpinBox { border:1px solid #D1D5DB; border-radius:5px;"
                "background:white; padding:0 8px; }"
            )

        self._combo_mes.currentIndexChanged.connect(lambda _: self.refresh())
        self._spin_anio.valueChanged.connect(lambda _: self.refresh())

        btn_guardar = QPushButton("Guardar presupuesto")
        btn_guardar.setFixedHeight(34)
        btn_guardar.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:5px;"
            "padding:0 14px; font-weight:bold; font-size:12px; border:none; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btn_guardar.clicked.connect(self._on_guardar)

        btn_copiar = QPushButton("Copiar mes anterior")
        btn_copiar.setFixedHeight(34)
        btn_copiar.setStyleSheet(
            "QPushButton { border:1px solid #D1D5DB; border-radius:5px; background:white;"
            "padding:0 12px; font-size:12px; color:#374151; }"
            "QPushButton:hover { background:#F3F4F6; }"
        )
        btn_copiar.setToolTip(
            "Copia los valores presupuestados del mes anterior a este mes"
        )
        btn_copiar.clicked.connect(self._on_copiar_mes_anterior)

        lay.addWidget(titulo)
        lay.addSpacing(16)
        lay.addWidget(QLabel("Mes:"))
        lay.addWidget(self._combo_mes)
        lay.addWidget(self._spin_anio)
        lay.addSpacing(12)
        lay.addWidget(btn_guardar)
        lay.addWidget(btn_copiar)
        lay.addStretch()
        return lay

    # ---- Panel gastos fijos (info de configuración) ----

    def _panel_gastos_fijos(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#EFF6FF; border:1px solid #BFDBFE; border-radius:8px; }"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(24)

        lbl_titulo = QLabel("Gastos fijos proyectados (de Configuración):")
        lbl_titulo.setStyleSheet(
            "color:#1D4ED8; font-size:11px; font-weight:bold; background:transparent; border:none;"
        )
        lay.addWidget(lbl_titulo)

        self._lbl_arriendo   = self._chip_fijo("Arriendo", "$ 0")
        self._lbl_sueldo     = self._chip_fijo("Sueldo", "$ 0")
        self._lbl_servicios  = self._chip_fijo("Servicios", "$ 0")
        self._lbl_otros      = self._chip_fijo("Otros fijos", "$ 0")
        self._lbl_total_fijo = self._chip_fijo("Total fijo/mes", "$ 0", bold=True)

        for w in (self._lbl_arriendo, self._lbl_sueldo,
                  self._lbl_servicios, self._lbl_otros, self._lbl_total_fijo):
            lay.addWidget(w)

        lay.addStretch()
        return frame

    def _chip_fijo(self, etiqueta: str, valor: str, bold: bool = False) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(1)

        l_e = QLabel(etiqueta)
        l_e.setStyleSheet("color:#6B7280; font-size:9px; background:transparent; border:none;")

        l_v = QLabel(valor)
        f = QFont()
        f.setPointSize(11 if not bold else 12)
        f.setBold(bold)
        l_v.setFont(f)
        l_v.setStyleSheet("color:#1D4ED8; background:transparent; border:none;")

        v.addWidget(l_e)
        v.addWidget(l_v)
        w._lbl = l_v
        return w

    # ---- Tabla comparativa ----

    def _panel_tabla(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#FFFFFF; border:1px solid #E5E7EB; border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 14, 20, 18)
        lay.setSpacing(12)

        lbl = QLabel("PRESUPUESTO POR CATEGORÍA")
        lbl.setStyleSheet(
            "color:#6B7280; font-size:10px; font-weight:bold; letter-spacing:0.5px;"
        )
        lay.addWidget(lbl)

        # Encabezado de columnas
        lay.addLayout(self._fila_encabezado())

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#E5E7EB;")
        lay.addWidget(sep)

        # Una fila por cada categoría
        self._filas: dict[str, dict] = {}  # categoria → {campo, lbl_real, lbl_dif, lbl_pct}
        for cat in CATEGORIAS_GASTO:
            fila_lay, fila_refs = self._fila_categoria(cat)
            self._filas[cat] = fila_refs
            lay.addLayout(fila_lay)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color:#E5E7EB;")
        lay.addWidget(sep2)

        # Fila de totales
        lay.addLayout(self._fila_totales())

        # Nota explicativa
        nota = QLabel(
            "* El gasto real se calcula sumando todos los gastos del día de esa categoría en el mes."
        )
        nota.setStyleSheet("color:#9CA3AF; font-size:10px;")
        nota.setWordWrap(True)
        lay.addWidget(nota)

        return frame

    def _fila_encabezado(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        for texto, stretch, alin in [
            ("Categoría",      3, Qt.AlignLeft),
            ("Presupuestado",  2, Qt.AlignCenter),
            ("Gasto Real",     2, Qt.AlignRight),
            ("Diferencia",     2, Qt.AlignRight),
            ("% Ejecutado",    2, Qt.AlignCenter),
        ]:
            l = QLabel(texto)
            l.setStyleSheet("color:#6B7280; font-size:10px; font-weight:bold;")
            l.setAlignment(alin)
            lay.addWidget(l, stretch=stretch)
        return lay

    def _fila_categoria(self, categoria: str):
        """Crea la fila UI para una categoría. Retorna (layout, refs_dict)."""
        lay = QHBoxLayout()
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(8)

        # Nombre
        lbl_cat = QLabel(categoria)
        lbl_cat.setStyleSheet("font-size:13px; font-weight:bold; color:#374151;")
        lay.addWidget(lbl_cat, stretch=3)

        # Presupuestado (editable)
        campo = MoneyLineEdit()
        campo.setPlaceholderText("0")
        campo.setFixedHeight(32)
        campo.setStyleSheet(
            "QLineEdit { border:1px solid #D1D5DB; border-radius:5px;"
            "padding:0 8px; background:#F8FAFC; font-size:12px; }"
            "QLineEdit:focus { border:2px solid #2563EB; background:white; }"
        )
        campo.textChanged.connect(self._actualizar_totales)
        lay.addWidget(campo, stretch=2)

        # Gasto real
        lbl_real = QLabel("$ 0")
        lbl_real.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_real.setStyleSheet("font-size:12px; color:#374151;")
        lay.addWidget(lbl_real, stretch=2)

        # Diferencia
        lbl_dif = QLabel("—")
        lbl_dif.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_dif.setStyleSheet("font-size:12px; font-weight:bold; color:#6B7280;")
        lay.addWidget(lbl_dif, stretch=2)

        # % ejecutado
        lbl_pct = QLabel("—")
        lbl_pct.setAlignment(Qt.AlignCenter)
        lbl_pct.setStyleSheet("font-size:12px; font-weight:bold; color:#6B7280;")
        lay.addWidget(lbl_pct, stretch=2)

        refs = {
            "campo": campo,
            "lbl_real": lbl_real,
            "lbl_dif":  lbl_dif,
            "lbl_pct":  lbl_pct,
        }
        return lay, refs

    def _fila_totales(self) -> QHBoxLayout:
        lay = QHBoxLayout()
        lay.setContentsMargins(0, 2, 0, 2)

        lbl = QLabel("TOTAL")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        lbl.setFont(f)
        lbl.setStyleSheet("color:#374151;")
        lay.addWidget(lbl, stretch=3)

        self._lbl_total_presup = QLabel("$ 0")
        self._lbl_total_presup.setAlignment(Qt.AlignCenter)
        self._lbl_total_presup.setStyleSheet("font-size:13px; font-weight:bold; color:#374151;")
        lay.addWidget(self._lbl_total_presup, stretch=2)

        self._lbl_total_real = QLabel("$ 0")
        self._lbl_total_real.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._lbl_total_real.setStyleSheet("font-size:13px; font-weight:bold; color:#374151;")
        lay.addWidget(self._lbl_total_real, stretch=2)

        self._lbl_total_dif = QLabel("—")
        self._lbl_total_dif.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._lbl_total_dif.setStyleSheet("font-size:13px; font-weight:bold; color:#6B7280;")
        lay.addWidget(self._lbl_total_dif, stretch=2)

        self._lbl_total_pct = QLabel("—")
        self._lbl_total_pct.setAlignment(Qt.AlignCenter)
        self._lbl_total_pct.setStyleSheet("font-size:13px; font-weight:bold; color:#6B7280;")
        lay.addWidget(self._lbl_total_pct, stretch=2)

        return lay

    # ------------------------------------------------------------------
    # Carga y cálculo
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Recarga presupuesto guardado y gastos reales del mes seleccionado."""
        anio = self._spin_anio.value()
        mes  = self._combo_mes.currentData()

        presupuesto = obtener_presupuesto_mes(anio, mes)
        reales      = obtener_totales_por_categoria(anio, mes)

        # Cargar campos presupuestados (bloquear señal textChanged para no disparar _actualizar_totales durante carga)
        for cat, refs in self._filas.items():
            campo = refs["campo"]
            campo.blockSignals(True)
            monto = presupuesto.get(cat, 0.0)
            campo.set_valor(int(monto)) if monto else campo.clear()
            campo.blockSignals(False)
            refs["_real"] = reales.get(cat, 0.0)

        # Actualizar labels reales
        for cat, refs in self._filas.items():
            refs["lbl_real"].setText(cop(refs["_real"]))

        # Calcular diferencias y colores
        self._actualizar_totales()

        # Panel gastos fijos
        cfg = obtener_configuracion()
        self._lbl_arriendo._lbl.setText(cop(cfg.arriendo))
        self._lbl_sueldo._lbl.setText(cop(cfg.sueldo))
        self._lbl_servicios._lbl.setText(cop(cfg.servicios))
        self._lbl_otros._lbl.setText(cop(cfg.otros_gastos))
        self._lbl_total_fijo._lbl.setText(cop(cfg.total_gastos_mes))

    def _actualizar_totales(self) -> None:
        """Recalcula diferencias, porcentajes y totales a partir de los campos."""
        total_presup = 0.0
        total_real   = 0.0

        for cat, refs in self._filas.items():
            presup = self._parse_campo(refs["campo"])
            real   = refs.get("_real", 0.0)
            dif    = presup - real

            total_presup += presup
            total_real   += real

            # Diferencia
            if presup > 0 or real > 0:
                signo = "+" if dif >= 0 else ""
                refs["lbl_dif"].setText(f"{signo}{cop(dif)}")
                color_dif = "#15803D" if dif >= 0 else "#DC2626"
                refs["lbl_dif"].setStyleSheet(
                    f"font-size:12px; font-weight:bold; color:{color_dif};"
                )
            else:
                refs["lbl_dif"].setText("—")
                refs["lbl_dif"].setStyleSheet("font-size:12px; color:#9CA3AF;")

            # % ejecutado
            if presup > 0:
                pct = real / presup * 100
                pct_txt = f"{pct:.1f}%"
                if pct <= 80:
                    color_pct = "#15803D"; bg = "#DCFCE7"
                elif pct <= 100:
                    color_pct = "#D97706"; bg = "#FEF3C7"
                else:
                    color_pct = "#DC2626"; bg = "#FEE2E2"
                refs["lbl_pct"].setText(pct_txt)
                refs["lbl_pct"].setStyleSheet(
                    f"font-size:11px; font-weight:bold; color:{color_pct};"
                    f"background:{bg}; border-radius:4px; padding:1px 6px;"
                )
            elif real > 0:
                refs["lbl_pct"].setText("Sin presup.")
                refs["lbl_pct"].setStyleSheet(
                    "font-size:10px; color:#DC2626; background:#FEE2E2;"
                    "border-radius:4px; padding:1px 6px;"
                )
            else:
                refs["lbl_pct"].setText("—")
                refs["lbl_pct"].setStyleSheet("font-size:12px; color:#9CA3AF;")

        # Totales
        dif_total = total_presup - total_real
        self._lbl_total_presup.setText(cop(total_presup))
        self._lbl_total_real.setText(cop(total_real))

        signo = "+" if dif_total >= 0 else ""
        self._lbl_total_dif.setText(f"{signo}{cop(dif_total)}")
        color_tot = "#15803D" if dif_total >= 0 else "#DC2626"
        self._lbl_total_dif.setStyleSheet(
            f"font-size:13px; font-weight:bold; color:{color_tot};"
        )

        if total_presup > 0:
            pct_tot = total_real / total_presup * 100
            self._lbl_total_pct.setText(f"{pct_tot:.1f}%")
            if pct_tot <= 80:
                color_pt = "#15803D"
            elif pct_tot <= 100:
                color_pt = "#D97706"
            else:
                color_pt = "#DC2626"
            self._lbl_total_pct.setStyleSheet(
                f"font-size:13px; font-weight:bold; color:{color_pt};"
            )
        else:
            self._lbl_total_pct.setText("—")
            self._lbl_total_pct.setStyleSheet("font-size:13px; color:#6B7280;")

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_guardar(self) -> None:
        """Persiste el presupuesto del mes seleccionado."""
        anio = self._spin_anio.value()
        mes  = self._combo_mes.currentData()
        for cat, refs in self._filas.items():
            monto = float(self._parse_campo(refs["campo"]))
            guardar_presupuesto_categoria(anio, mes, cat, monto)
        QMessageBox.information(
            self, "Guardado",
            f"Presupuesto de {MESES_ES[mes]} {anio} guardado correctamente."
        )

    def _on_copiar_mes_anterior(self) -> None:
        """Copia los montos del mes anterior al mes actualmente seleccionado."""
        anio = self._spin_anio.value()
        mes  = self._combo_mes.currentData()

        if mes == 1:
            anio_orig, mes_orig = anio - 1, 12
        else:
            anio_orig, mes_orig = anio, mes - 1

        n = copiar_presupuesto_mes(anio_orig, mes_orig, anio, mes)
        if n == 0:
            QMessageBox.information(
                self, "Sin datos",
                f"No hay presupuesto guardado en {MESES_ES[mes_orig]} {anio_orig}."
            )
        else:
            self.refresh()
            QMessageBox.information(
                self, "Copiado",
                f"Presupuesto copiado de {MESES_ES[mes_orig]} {anio_orig} "
                f"a {MESES_ES[mes]} {anio}."
            )

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_campo(campo: MoneyLineEdit) -> int:
        return campo.valor_int()
