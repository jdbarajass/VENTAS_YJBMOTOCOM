"""
ui/exportar_importar_panel.py
Centro unificado de exportación e importación de datos.
Un solo archivo Excel con hasta 8 hojas: Ventas | Préstamos | Inventario |
Facturas | Abonos | Gastos | Notas | Configuración.
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
from utils.logger import log


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
            "Un único archivo Excel con hasta 8 pestañas: ventas, préstamos, inventario, "
            "facturas, abonos, gastos, notas y configuración."
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

        root.addWidget(self._sep())
        root.addWidget(self._bloque_peligro())

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
            "QComboBox { font-size:11px; padding:2px 6px; border:1px solid #BBF7D0; border-radius:4px; }"
        )
        fila_ventas.addWidget(self._combo_mes)

        # Spin año
        self._spin_año = QSpinBox()
        self._spin_año.setRange(2020, 2100)
        self._spin_año.setValue(_date.today().year)
        self._spin_año.setFixedWidth(70)
        self._spin_año.setStyleSheet(
            "QSpinBox { font-size:11px; padding:2px 4px; border:1px solid #BBF7D0; border-radius:4px; }"
        )
        fila_ventas.addWidget(self._spin_año)
        fila_ventas.addStretch()

        g_lay.addLayout(fila_ventas)

        # Resto de hojas
        self._chk_prestamos   = QCheckBox("Préstamos")
        self._chk_inventario  = QCheckBox("Inventario")
        self._chk_facturas    = QCheckBox("Facturas")
        self._chk_gastos      = QCheckBox("Gastos operativos")
        self._chk_notas       = QCheckBox("Notas y Pendientes")
        self._chk_abonos      = QCheckBox("Abonos de facturas")
        self._chk_config      = QCheckBox("Configuración")

        for chk in (self._chk_prestamos, self._chk_inventario,
                    self._chk_facturas, self._chk_gastos,
                    self._chk_notas, self._chk_abonos, self._chk_config):
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
            "  • Todas las facturas y abonos se REEMPLAZARÁN",
            "  • Los gastos de los meses del archivo se REEMPLAZARÁN",
            "  • Todas las notas y pendientes se REEMPLAZARÁN",
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
                "El archivo tiene 8 hojas:\n"
                "  • Ventas — historial de ventas\n"
                "  • Préstamos — préstamos a locales\n"
                "  • Inventario — productos en stock\n"
                "  • Facturas — facturas a proveedores\n"
                "  • Abonos — pagos parciales a facturas\n"
                "  • Gastos — gastos operativos diarios\n"
                "  • Notas — Por Pedir / Resurtido y Tareas\n"
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
            self._chk_gastos.isChecked(), self._chk_notas.isChecked(),
            self._chk_abonos.isChecked(), self._chk_config.isChecked(),
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
            from database.gastos_dia_repo import obtener_todos_gastos
            from database.config_repo import obtener_configuracion
            from database.notas_repo import obtener_notas

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
            notas = (
                obtener_notas("resurtido") + obtener_notas("tarea")
                if self._chk_notas.isChecked() else None
            )

            abonos = None
            if self._chk_abonos.isChecked():
                from database.abonos_factura_repo import obtener_todos_abonos_con_factura
                abonos = obtener_todos_abonos_con_factura()

            exportar_todo(Path(ruta), ventas, prestamos, productos,
                          facturas, gastos, configuracion, notas, abonos)

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
            if notas      is not None: lineas.append(f"  • {len(notas)} nota(s) y pendiente(s)")
            if abonos     is not None: lineas.append(f"  • {len(abonos)} abono(s) de facturas")
            if configuracion is not None: lineas.append("  • Configuración incluida")

            QMessageBox.information(
                self,
                "Exportación exitosa",
                f"Archivo guardado en:\n{ruta}\n\n"
                f"Contenido exportado:\n" + "\n".join(lineas),
            )
        except Exception as exc:
            log.error("Error al exportar", exc_info=True)
            QMessageBox.critical(self, "Error al exportar", str(exc))

    def _on_importar(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de datos", "", "Excel (*.xlsx)"
        )
        if not ruta:
            return

        # 1. Parsear el archivo Excel
        try:
            from services.importador import importar_todo, validar_resultado
            res = importar_todo(Path(ruta))
        except Exception as exc:
            log.error("Error al leer archivo de importación: %s", ruta, exc_info=True)
            QMessageBox.critical(self, "Error al leer el archivo", str(exc))
            return

        if res.errores and not res.ventas and not res.productos:
            QMessageBox.warning(
                self, "No se pudo leer el archivo",
                "Errores encontrados:\n" + "\n".join(res.errores[:5])
            )
            return

        # 2. Validar coherencia antes de tocar la BD
        errores_criticos, advertencias_val = validar_resultado(res)
        if errores_criticos:
            QMessageBox.critical(
                self,
                "Datos incoherentes — importación cancelada",
                "Se detectaron datos que parecen incorrectos o transpuestos.\n"
                "La importación fue cancelada para proteger tu base de datos.\n\n"
                + "\n".join(errores_criticos),
            )
            return

        # 3. Backup de seguridad — exportar todo como Excel antes de importar
        from datetime import datetime as _datetime

        ts = _datetime.now().strftime("%Y-%m-%d_%H-%M")
        nombre_bk = f"backup_antes_importar_{ts}.xlsx"

        QMessageBox.information(
            self,
            "Respaldo de seguridad",
            "Antes de importar se exportará una copia completa de tu base de datos actual.\n\n"
            "Elige dónde quieres guardar el respaldo.\n"
            "Si algo sale mal, podrás importar ese archivo para recuperar todo.",
        )
        ruta_bk, _ = QFileDialog.getSaveFileName(
            self, "Guardar respaldo como Excel", nombre_bk, "Excel (*.xlsx)"
        )
        if not ruta_bk:
            resp = QMessageBox.question(
                self,
                "Sin respaldo",
                "No guardaste ningún respaldo.\n"
                "¿Deseas continuar la importación de todas formas?\n"
                "(no recomendado — si algo falla no podrás recuperar los datos)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return
        else:
            try:
                from services.exportador import exportar_todo as _exportar_todo
                from database.ventas_repo import obtener_todas_las_ventas as _get_ventas
                from database.prestamos_repo import obtener_todos_prestamos as _get_prestamos
                from database.inventario_repo import obtener_todos_productos as _get_productos
                from database.facturas_repo import obtener_todas_facturas as _get_facturas
                from database.gastos_dia_repo import obtener_todos_gastos as _get_gastos
                from database.config_repo import obtener_configuracion as _get_cfg
                from database.notas_repo import obtener_notas as _get_notas
                from database.abonos_factura_repo import obtener_todos_abonos_con_factura as _get_abonos

                _exportar_todo(
                    Path(ruta_bk),
                    ventas=_get_ventas(),
                    prestamos=_get_prestamos(),
                    productos=_get_productos(),
                    facturas=_get_facturas(),
                    gastos=_get_gastos(),
                    configuracion=_get_cfg(),
                    notas=_get_notas("resurtido") + _get_notas("tarea"),
                    abonos=_get_abonos(),
                )
                QMessageBox.information(
                    self,
                    "Respaldo guardado",
                    f"Respaldo guardado en:\n{ruta_bk}\n\n"
                    "Si algo sale mal, importa ese archivo para recuperar todo.",
                )
            except Exception as exc:
                log.error("Error al guardar respaldo previo a importación", exc_info=True)
                QMessageBox.critical(self, "Error al guardar respaldo", str(exc))
                return

        # Construir descripción de los meses afectados
        if res.meses_afectados:
            meses_str = ", ".join(
                nombre_mes(m, a) for a, m in sorted(res.meses_afectados)
            )
        else:
            meses_str = "ningún mes detectado"

        def _conteo(lst, singular, plural=None):
            if lst is None:
                return f"  • {singular}: no incluido(a) en el archivo"
            n = len(lst)
            label = plural or singular
            return f"  • {n} {label}"

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
            + _conteo(res.notas, "nota(s) y pendiente(s)") + "\n"
            + _conteo(res.abonos_raw, "abono(s) de facturas") + "\n"
            + f"  • Configuración: {cfg_str}\n\n"
            f"Esta acción no se puede deshacer."
        )
        # Advertencias de validación de coherencia
        todas_adv = list(advertencias_val) + res.errores[:3]
        if todas_adv:
            confirmacion += (
                f"\n\n⚠ Advertencias ({len(todas_adv)}):\n"
                + "\n".join(f"  • {a}" for a in todas_adv)
            )

        resp = QMessageBox.question(
            self, "Confirmar importación", confirmacion,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if resp != QMessageBox.Yes:
            return

        try:
            advertencias_import = self._ejecutar_importacion(res)
            msg = (
                f"Datos importados correctamente:\n"
                f"  • {len(res.ventas)} venta(s)\n"
                f"  • {len(res.prestamos)} préstamo(s)\n"
                f"  • {len(res.productos)} producto(s)\n"
                f"  • {len(res.facturas)} factura(s)\n"
                f"  • {len(res.gastos)} gasto(s) operativo(s)\n"
                + (f"  • {len(res.notas)} nota(s) y pendiente(s)\n" if res.notas is not None else "")
                + (f"  • {len(res.abonos_raw)} abono(s) de facturas\n" if res.abonos_raw is not None else "")
                + ("  • Configuración actualizada" if res.configuracion else "")
            )
            if advertencias_import:
                msg += "\n\n⚠ Advertencias:\n" + "\n".join(f"  • {a}" for a in advertencias_import)
            QMessageBox.information(self, "Importación exitosa", msg)
            self.datos_importados.emit()
        except Exception as exc:
            log.error("Error durante la importación", exc_info=True)
            QMessageBox.critical(self, "Error durante la importación", str(exc))

    def _ejecutar_importacion(self, res) -> list[str]:
        """Reemplaza ventas, préstamos, inventario, facturas, abonos, gastos, notas y config.
        Retorna lista de advertencias (puede estar vacía)."""
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

        advertencias: list[str] = []
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

        # Abonos primero (antes de borrar facturas para evitar FK issues)
        from database.abonos_factura_repo import eliminar_todos_abonos, insertar_abono
        eliminar_todos_abonos()

        # Facturas
        eliminar_todas_facturas()
        factura_id_map: dict[tuple, int] = {}
        for f in res.facturas:
            new_id = insertar_factura_directa(f)
            key = (f.descripcion.strip().lower(), f.proveedor.strip().lower())
            factura_id_map[key] = new_id

        # Abonos — vincular a las facturas recién insertadas
        if res.abonos_raw:
            from models.abono_factura import AbonoFactura
            abonos_omitidos = 0
            for ab in res.abonos_raw:
                key = (ab["factura_desc"].strip().lower(), ab["factura_prov"].strip().lower())
                factura_id = factura_id_map.get(key)
                if factura_id is None:
                    abonos_omitidos += 1
                    log.warning("Abono omitido: factura '%s' / '%s' no encontrada",
                                ab["factura_desc"], ab["factura_prov"])
                    continue
                try:
                    insertar_abono(AbonoFactura(
                        factura_id=factura_id,
                        monto=ab["monto"],
                        fecha=ab["fecha"],
                        notas=ab["notas"],
                    ))
                except (ValueError, Exception) as exc:
                    abonos_omitidos += 1
                    log.warning("Abono omitido por error: %s", exc)
            if abonos_omitidos:
                advertencias.append(
                    f"{abonos_omitidos} abono(s) no se importaron porque su factura "
                    "no coincide exactamente con ninguna factura del archivo."
                )

        # Gastos operativos
        for año_m, mes_m in res.meses_gastos_afectados:
            eliminar_gastos_por_mes(año_m, mes_m)
        for g in res.gastos:
            insertar_gasto_directo(g)

        # Configuración (si viene en el archivo)
        if res.configuracion:
            guardar_configuracion(res.configuracion)

        # Notas y Pendientes (solo si la hoja vino en el archivo)
        if res.notas is not None:
            from database.notas_repo import eliminar_todas_notas, insertar_nota
            eliminar_todas_notas()
            for n in res.notas:
                insertar_nota(n)

        return advertencias

    # ---- Zona de peligro ----

    def _bloque_peligro(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("bloquePeligro")
        frame.setStyleSheet(
            "QFrame#bloquePeligro { background:#FFF5F5; border:1px solid #FECACA;"
            "border-radius:10px; }"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(20)

        # Texto explicativo
        col_txt = QVBoxLayout(); col_txt.setSpacing(4)
        titulo_peligro = QLabel("⚠  Zona de peligro")
        ft = QFont(); ft.setPointSize(12); ft.setBold(True)
        titulo_peligro.setFont(ft)
        titulo_peligro.setStyleSheet(
            "color:#B91C1C; background:transparent; border:none;"
        )
        desc_peligro = QLabel(
            "Borra TODA la información de la base de datos: ventas, préstamos, "
            "inventario, facturas, gastos y configuración.\n"
            "Esta acción es permanente e irreversible. Exporta un respaldo antes de continuar."
        )
        desc_peligro.setWordWrap(True)
        desc_peligro.setStyleSheet(
            "color:#374151; font-size:11px; background:transparent; border:none;"
        )
        col_txt.addWidget(titulo_peligro)
        col_txt.addWidget(desc_peligro)
        lay.addLayout(col_txt, stretch=1)

        btn_borrar_bd = QPushButton("🗑  Borrar base de datos")
        btn_borrar_bd.setFixedHeight(42)
        btn_borrar_bd.setFixedWidth(220)
        btn_borrar_bd.setStyleSheet(
            "QPushButton { background:#DC2626; color:white; border-radius:7px;"
            "font-size:13px; font-weight:bold; border:none; }"
            "QPushButton:hover { background:#B91C1C; }"
        )
        btn_borrar_bd.clicked.connect(self._on_borrar_bd)
        lay.addWidget(btn_borrar_bd)
        return frame

    def _on_borrar_bd(self) -> None:
        """Doble confirmación antes de borrar toda la base de datos."""
        resp1 = QMessageBox.warning(
            self,
            "Borrar base de datos",
            "⚠  ¿Estás seguro de que deseas borrar TODA la información?\n\n"
            "Se eliminarán permanentemente:\n"
            "  • Todas las ventas\n"
            "  • Todos los préstamos\n"
            "  • Todo el inventario\n"
            "  • Todas las facturas y abonos\n"
            "  • Todos los gastos operativos\n"
            "  • La configuración (arriendo, sueldo, etc.)\n\n"
            "Esta acción NO se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp1 != QMessageBox.Yes:
            return

        resp2 = QMessageBox.critical(
            self,
            "Confirmación final",
            "ÚLTIMA ADVERTENCIA\n\n"
            "Se borrarán TODOS los datos de forma permanente.\n"
            "¿Confirmas el borrado total?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if resp2 != QMessageBox.Yes:
            return

        try:
            from database.schema import resetear_base_datos
            resetear_base_datos()
            QMessageBox.information(
                self,
                "Base de datos borrada",
                "La base de datos ha sido borrada exitosamente.\n"
                "Todos los datos han sido eliminados.",
            )
            self.datos_importados.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Error al borrar", str(exc))
