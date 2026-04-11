"""
ui/exportar_importar_panel.py
Centro unificado de exportación e importación de datos.
Un solo archivo Excel con hasta 6 hojas: Ventas | Préstamos | Inventario |
Facturas | Gastos | Configuración.
"""

from datetime import date as _date
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QFileDialog, QCheckBox, QComboBox, QSpinBox,
    QGroupBox,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from utils.formatters import nombre_mes


_MESES_NOMBRES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


class ExportarImportarPanel(QWidget):
    """Panel central de exportación e importación unificada."""

    datos_importados = Signal()   # emitido tras importar con éxito

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        # Título
        titulo = QLabel("Exportar / Importar")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)
        root.addWidget(titulo)

        sub = QLabel(
            "Un único archivo Excel con hasta 6 pestañas: ventas, préstamos, inventario, "
            "facturas, gastos y configuración."
        )
        sub.setStyleSheet("color:#6B7280; font-size:12px;")
        root.addWidget(sub)

        root.addWidget(self._sep())

        # Bloque de contenido en dos columnas
        cols = QHBoxLayout()
        cols.setSpacing(24)
        cols.addWidget(self._bloque_exportar(), stretch=3)
        cols.addWidget(self._bloque_importar(), stretch=2)
        root.addLayout(cols)

        root.addStretch()

    # ---- Bloque exportar ----

    def _bloque_exportar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("bloqueExp")
        frame.setStyleSheet(
            "QFrame#bloqueExp { background:#F0FDF4; border:1px solid #BBF7D0;"
            "border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)

        icon_titulo = QLabel("⬇  Exportar")
        ft = QFont(); ft.setPointSize(13); ft.setBold(True)
        icon_titulo.setFont(ft)
        icon_titulo.setStyleSheet(
            "color:#15803D; background:transparent; border:none;"
        )
        lay.addWidget(icon_titulo)

        lay.addWidget(self._lbl_info(
            "Selecciona qué datos incluir en el archivo exportado:"
        ))

        # --- Filtros por hoja ---
        grupo = QGroupBox("Hojas a incluir")
        grupo.setStyleSheet(
            "QGroupBox { font-size:12px; font-weight:bold; color:#374151;"
            "border:1px solid #BBF7D0; border-radius:6px; margin-top:6px;"
            "background:transparent; }"
            "QGroupBox::title { subcontrol-origin:margin; left:10px; padding:0 4px; }"
        )
        g_lay = QVBoxLayout(grupo)
        g_lay.setSpacing(8)
        g_lay.setContentsMargins(12, 12, 12, 12)

        chk_style = (
            "QCheckBox { color:#374151; font-size:12px; background:transparent; border:none; }"
            "QCheckBox::indicator { width:16px; height:16px; }"
        )

        # Ventas + filtro de mes
        fila_ventas = QHBoxLayout()
        fila_ventas.setSpacing(8)
        self._chk_ventas = QCheckBox("Ventas")
        self._chk_ventas.setChecked(True)
        self._chk_ventas.setStyleSheet(chk_style)
        fila_ventas.addWidget(self._chk_ventas)

        # Combo mes
        self._combo_mes = QComboBox()
        self._combo_mes.addItem("Todos los meses", userData=0)
        for i, nombre in enumerate(_MESES_NOMBRES, start=1):
            self._combo_mes.addItem(nombre, userData=i)
        self._combo_mes.setCurrentIndex(0)
        self._combo_mes.setFixedWidth(150)
        self._combo_mes.setStyleSheet(
            "QComboBox { font-size:11px; padding:2px 6px; border:1px solid #BBF7D0;"
            "border-radius:4px; background:white; color:#374151; }"
        )
        fila_ventas.addWidget(self._combo_mes)

        # Spin año
        self._spin_año = QSpinBox()
        self._spin_año.setRange(2020, 2100)
        self._spin_año.setValue(_date.today().year)
        self._spin_año.setFixedWidth(70)
        self._spin_año.setStyleSheet(
            "QSpinBox { font-size:11px; padding:2px 4px; border:1px solid #BBF7D0;"
            "border-radius:4px; background:white; color:#374151; }"
        )
        fila_ventas.addWidget(self._spin_año)
        fila_ventas.addStretch()

        g_lay.addLayout(fila_ventas)

        # Resto de hojas
        self._chk_prestamos   = QCheckBox("Préstamos")
        self._chk_inventario  = QCheckBox("Inventario")
        self._chk_facturas    = QCheckBox("Facturas")
        self._chk_gastos      = QCheckBox("Gastos operativos")
        self._chk_config      = QCheckBox("Configuración")

        for chk in (self._chk_prestamos, self._chk_inventario,
                    self._chk_facturas, self._chk_gastos, self._chk_config):
            chk.setChecked(True)
            chk.setStyleSheet(chk_style)
            g_lay.addWidget(chk)

        lay.addWidget(grupo)

        # Conectar checkbox ventas → habilitar/deshabilitar filtros de mes
        self._chk_ventas.toggled.connect(self._on_ventas_toggle)
        self._combo_mes.currentIndexChanged.connect(self._on_mes_cambiado)

        lay.addWidget(self._sep_interno())

        # Botones
        fila_btns = QHBoxLayout()
        fila_btns.setSpacing(10)

        btn_plantilla = QPushButton("⬇  Descargar Plantilla")
        btn_plantilla.setFixedHeight(42)
        btn_plantilla.setStyleSheet(
            "QPushButton { background:#059669; color:white; border-radius:7px;"
            "font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#047857; }"
        )
        btn_plantilla.setToolTip(
            "Descarga un Excel vacío con las hojas para rellenar\n"
            "y luego importar con el botón Importar Todo"
        )
        btn_plantilla.clicked.connect(self._on_descargar_plantilla)

        btn = QPushButton("⬇  Exportar selección")
        btn.setFixedHeight(42)
        btn.setStyleSheet(
            "QPushButton { background:#16A34A; color:white; border-radius:7px;"
            "font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#15803D; }"
        )
        btn.clicked.connect(self._on_exportar)

        fila_btns.addWidget(btn_plantilla)
        fila_btns.addWidget(btn)
        lay.addLayout(fila_btns)

        return frame

    # ---- Bloque importar ----

    def _bloque_importar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("bloqueImp")
        frame.setStyleSheet(
            "QFrame#bloqueImp { background:#EFF6FF; border:1px solid #BFDBFE;"
            "border-radius:10px; }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)

        icon_titulo = QLabel("⬆  Importar Todo")
        ft = QFont(); ft.setPointSize(13); ft.setBold(True)
        icon_titulo.setFont(ft)
        icon_titulo.setStyleSheet(
            "color:#1D4ED8; background:transparent; border:none;"
        )
        lay.addWidget(icon_titulo)

        lay.addWidget(self._lbl_info(
            "Carga un archivo exportado desde esta sección. Al importar:"
        ))

        for linea in (
            "  • Las ventas de los meses del archivo se REEMPLAZARÁN",
            "  • Todos los préstamos se REEMPLAZARÁN",
            "  • Todo el inventario se REEMPLAZARÁ",
            "  • Todas las facturas se REEMPLAZARÁN",
            "  • Los gastos de los meses del archivo se REEMPLAZARÁN",
            "  • La configuración se ACTUALIZARÁ (si viene en el archivo)",
        ):
            l = QLabel(linea)
            l.setStyleSheet("color:#374151; font-size:12px; background:transparent; border:none;")
            lay.addWidget(l)

        advertencia = QLabel(
            "Esta operación no se puede deshacer. Haz una exportación previa\n"
            "como respaldo antes de importar."
        )
        advertencia.setStyleSheet(
            "color:#92400E; font-size:11px; background:#FEF3C7;"
            "border:1px solid #FDE68A; border-radius:5px; padding:6px 10px;"
        )
        advertencia.setWordWrap(True)
        lay.addWidget(advertencia)

        lay.addWidget(self._sep_interno())
        lay.addStretch()

        btn = QPushButton("⬆  Importar Todo")
        btn.setFixedHeight(42)
        btn.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:7px;"
            "font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btn.clicked.connect(self._on_importar)
        lay.addWidget(btn)

        return frame

    # ---- Helpers ----

    def _lbl_info(self, texto: str) -> QLabel:
        l = QLabel(texto)
        l.setStyleSheet("color:#374151; font-size:12px; background:transparent; border:none;")
        return l

    def _sep(self) -> QFrame:
        s = QFrame(); s.setFrameShape(QFrame.HLine)
        s.setStyleSheet("color:#E5E7EB;")
        return s

    def _sep_interno(self) -> QFrame:
        s = QFrame(); s.setFrameShape(QFrame.HLine)
        s.setStyleSheet("color:#D1FAE5;")
        return s

    # ------------------------------------------------------------------
    # Slots auxiliares
    # ------------------------------------------------------------------

    def _on_ventas_toggle(self, checked: bool) -> None:
        """Habilita/deshabilita los filtros de mes al marcar/desmarcar Ventas."""
        self._combo_mes.setEnabled(checked)
        self._spin_año.setEnabled(checked and self._combo_mes.currentData() != 0)

    def _on_mes_cambiado(self, index: int) -> None:
        """Habilita el spin de año solo cuando se elige un mes específico."""
        mes = self._combo_mes.currentData()
        self._spin_año.setEnabled(self._chk_ventas.isChecked() and mes != 0)

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

    def _on_descargar_plantilla(self) -> None:
        nombre_sugerido = "Plantilla_YJBMOTOCOM.xlsx"

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar plantilla", nombre_sugerido, "Excel (*.xlsx)"
        )
        if not ruta:
            return
        try:
            from services.exportador import generar_plantilla_todo
            generar_plantilla_todo(Path(ruta))
            QMessageBox.information(
                self,
                "Plantilla guardada",
                f"Plantilla guardada en:\n{ruta}\n\n"
                "El archivo tiene hojas:\n"
                "  • Ventas — tus ventas (cualquier mes o año)\n"
                "  • Préstamos — préstamos a locales\n"
                "  • Inventario — productos en stock\n"
                "  • Facturas — facturas y recibos\n"
                "  • Gastos — gastos operativos diarios\n"
                "  • Configuración — arriendo, sueldo, etc.\n\n"
                "Borra las filas de ejemplo (en gris) antes de importar.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error al guardar", str(exc))

    def _on_exportar(self) -> None:
        # Verificar que al menos una hoja esté seleccionada
        if not any([
            self._chk_ventas.isChecked(), self._chk_prestamos.isChecked(),
            self._chk_inventario.isChecked(), self._chk_facturas.isChecked(),
            self._chk_gastos.isChecked(), self._chk_config.isChecked(),
        ]):
            QMessageBox.warning(
                self, "Sin selección",
                "Selecciona al menos una hoja para exportar."
            )
            return

        nombre_sugerido = "YJBMOTOCOM_Historial.xlsx"
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar archivo de datos", nombre_sugerido, "Excel (*.xlsx)"
        )
        if not ruta:
            return

        try:
            from services.exportador import exportar_todo
            from database.ventas_repo import obtener_todas_las_ventas as obtener_todas_ventas
            from database.ventas_repo import obtener_ventas_por_mes
            from database.prestamos_repo import obtener_todos_prestamos
            from database.inventario_repo import obtener_todos_productos
            from database.facturas_repo import obtener_todas_facturas
            from database.gastos_dia_repo import obtener_todos_gastos, obtener_gastos_por_mes
            from database.config_repo import obtener_configuracion

            # --- Ventas ---
            ventas = None
            if self._chk_ventas.isChecked():
                mes_sel  = self._combo_mes.currentData()   # 0 = todos
                año_sel  = self._spin_año.value()
                if mes_sel == 0:
                    ventas = obtener_todas_ventas()
                else:
                    ventas = obtener_ventas_por_mes(año_sel, mes_sel)

            prestamos     = obtener_todos_prestamos()     if self._chk_prestamos.isChecked()  else None
            productos     = obtener_todos_productos()     if self._chk_inventario.isChecked() else None
            facturas      = obtener_todas_facturas()      if self._chk_facturas.isChecked()   else None
            gastos        = obtener_todos_gastos()        if self._chk_gastos.isChecked()     else None
            configuracion = obtener_configuracion()       if self._chk_config.isChecked()     else None

            exportar_todo(Path(ruta), ventas, prestamos, productos,
                          facturas, gastos, configuracion)

            # Construir resumen para el mensaje
            lineas = []
            if ventas is not None:
                mes_sel = self._combo_mes.currentData()
                if mes_sel == 0:
                    lineas.append(f"  • {len(ventas)} venta(s) — todos los meses")
                else:
                    nm = _MESES_NOMBRES[mes_sel - 1]
                    lineas.append(f"  • {len(ventas)} venta(s) — {nm} {self._spin_año.value()}")
            if prestamos  is not None: lineas.append(f"  • {len(prestamos)} préstamo(s)")
            if productos  is not None: lineas.append(f"  • {len(productos)} producto(s) de inventario")
            if facturas   is not None: lineas.append(f"  • {len(facturas)} factura(s)")
            if gastos     is not None: lineas.append(f"  • {len(gastos)} gasto(s) operativo(s)")
            if configuracion is not None: lineas.append("  • Configuración incluida")

            QMessageBox.information(
                self,
                "Exportación exitosa",
                f"Archivo guardado en:\n{ruta}\n\n"
                f"Contenido exportado:\n" + "\n".join(lineas),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error al exportar", str(exc))

    def _on_importar(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de datos", "", "Excel (*.xlsx)"
        )
        if not ruta:
            return

        try:
            from services.importador import importar_todo
            res = importar_todo(Path(ruta))
        except Exception as exc:
            QMessageBox.critical(self, "Error al leer el archivo", str(exc))
            return

        if res.errores and not res.ventas and not res.productos:
            QMessageBox.warning(
                self, "No se pudo leer el archivo",
                "Errores encontrados:\n" + "\n".join(res.errores[:5])
            )
            return

        # Construir descripción de los meses afectados
        if res.meses_afectados:
            meses_str = ", ".join(
                nombre_mes(m, a) for a, m in sorted(res.meses_afectados)
            )
        else:
            meses_str = "ningún mes detectado"

        cfg_str = "Sí" if res.configuracion else "No incluida"
        confirmacion = (
            f"¿Confirmar importación?\n\n"
            f"Ventas: meses afectados → {meses_str}\n\n"
            f"Resumen:\n"
            f"  • {len(res.ventas)} venta(s)\n"
            f"  • {len(res.prestamos)} préstamo(s)\n"
            f"  • {len(res.productos)} producto(s) de inventario\n"
            f"  • {len(res.facturas)} factura(s)\n"
            f"  • {len(res.gastos)} gasto(s) operativo(s)\n"
            f"  • Configuración: {cfg_str}\n\n"
            f"Esta acción no se puede deshacer."
        )
        if res.errores:
            confirmacion += f"\n\nAdvertencias ({len(res.errores)}):\n" + "\n".join(res.errores[:3])

        resp = QMessageBox.question(
            self, "Confirmar importación", confirmacion,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        try:
            self._ejecutar_importacion(res)
            QMessageBox.information(
                self, "Importación exitosa",
                f"Datos importados correctamente:\n"
                f"  • {len(res.ventas)} venta(s)\n"
                f"  • {len(res.prestamos)} préstamo(s)\n"
                f"  • {len(res.productos)} producto(s)\n"
                f"  • {len(res.facturas)} factura(s)\n"
                f"  • {len(res.gastos)} gasto(s) operativo(s)\n"
                + ("  • Configuración actualizada" if res.configuracion else ""),
            )
            self.datos_importados.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Error durante la importación", str(exc))

    def _ejecutar_importacion(self, res) -> None:
        """Reemplaza ventas, préstamos, inventario, facturas, gastos y config."""
        from database.ventas_repo import (
            eliminar_ventas_por_mes, insertar_venta,
        )
        from database.prestamos_repo import (
            eliminar_todos_prestamos, insertar_prestamo,
        )
        from database.inventario_repo import (
            eliminar_todo_inventario, insertar_producto,
        )
        from database.facturas_repo import (
            eliminar_todas_facturas, insertar_factura_directa,
        )
        from database.gastos_dia_repo import (
            eliminar_gastos_por_mes, insertar_gasto_directo,
        )
        from database.config_repo import guardar_configuracion, obtener_configuracion
        from services.calculator import completar_venta

        cfg_actual = obtener_configuracion()

        # Ventas: eliminar los meses del archivo y reinsertar
        for año_m, mes_m in res.meses_afectados:
            eliminar_ventas_por_mes(año_m, mes_m)
        cfg_para_calc = res.configuracion if res.configuracion else cfg_actual
        for v in res.ventas:
            if v.pagos_combinados or v.metodo_pago != "Combinado":
                completar_venta(v, cfg_para_calc)
            insertar_venta(v)

        # Préstamos
        eliminar_todos_prestamos()
        for p in res.prestamos:
            insertar_prestamo(p)

        # Inventario
        eliminar_todo_inventario()
        for prod in res.productos:
            insertar_producto(prod)

        # Facturas
        eliminar_todas_facturas()
        for f in res.facturas:
            insertar_factura_directa(f)

        # Gastos operativos
        for año_m, mes_m in res.meses_gastos_afectados:
            eliminar_gastos_por_mes(año_m, mes_m)
        for g in res.gastos:
            insertar_gasto_directo(g)

        # Configuración (si viene en el archivo)
        if res.configuracion:
            guardar_configuracion(res.configuracion)
