"""
ui/exportar_importar_panel.py
Centro unificado de exportación e importación de datos.
Un solo archivo Excel con tres hojas: Ventas | Préstamos | Inventario.
"""

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont

from utils.formatters import nombre_mes


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
            "Un único archivo Excel con 4 pestañas: ventas, préstamos, inventario y facturas."
        )
        sub.setStyleSheet("color:#6B7280; font-size:12px;")
        root.addWidget(sub)

        root.addWidget(self._sep())

        # Bloque de contenido en dos columnas
        cols = QHBoxLayout()
        cols.setSpacing(24)
        cols.addWidget(self._bloque_exportar(), stretch=1)
        cols.addWidget(self._bloque_importar(), stretch=1)
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

        icon_titulo = QLabel("⬇  Exportar Todo")
        ft = QFont(); ft.setPointSize(13); ft.setBold(True)
        icon_titulo.setFont(ft)
        icon_titulo.setStyleSheet(
            "color:#15803D; background:transparent; border:none;"
        )
        lay.addWidget(icon_titulo)

        lay.addWidget(self._lbl_info(
            "Genera el archivo con todo el historial. Incluye:"
        ))

        for linea in (
            "  • Ventas — historial completo (con desglose de pagos combinados)",
            "  • Préstamos — todos los estados",
            "  • Inventario — snapshot de hoy",
            "  • Facturas y recibos — todos los estados",
            "  • Gastos operativos diarios",
            "  • Configuración (arriendo, sueldo, comisiones)",
        ):
            l = QLabel(linea)
            l.setStyleSheet("color:#374151; font-size:12px; background:transparent; border:none;")
            lay.addWidget(l)

        lay.addWidget(self._sep_interno())
        lay.addStretch()

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
            "Descarga un Excel vacío con las tres hojas para rellenar\n"
            "y luego importar con el botón Importar Todo"
        )
        btn_plantilla.clicked.connect(self._on_descargar_plantilla)

        btn = QPushButton("⬇  Exportar Todo")
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
                "El archivo tiene cuatro pestañas:\n"
                "  • Ventas — tus ventas (cualquier mes o año)\n"
                "  • Préstamos — préstamos a locales\n"
                "  • Inventario — productos en stock\n"
                "  • Facturas — facturas y recibos\n\n"
                "Borra las filas de ejemplo (en gris) antes de importar.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error al guardar", str(exc))

    def _on_exportar(self) -> None:
        nombre_sugerido = "YJBMOTOCOM_Historial.xlsx"

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar archivo de datos", nombre_sugerido, "Excel (*.xlsx)"
        )
        if not ruta:
            return

        try:
            from services.exportador import exportar_todo
            from database.ventas_repo import obtener_todas_las_ventas as obtener_todas_ventas
            from database.prestamos_repo import obtener_todos_prestamos
            from database.inventario_repo import obtener_todos_productos
            from database.facturas_repo import obtener_todas_facturas
            from database.gastos_dia_repo import obtener_todos_gastos
            from database.config_repo import obtener_configuracion

            ventas         = obtener_todas_ventas()
            prestamos      = obtener_todos_prestamos()
            productos      = obtener_todos_productos()
            facturas       = obtener_todas_facturas()
            gastos         = obtener_todos_gastos()
            configuracion  = obtener_configuracion()

            exportar_todo(Path(ruta), ventas, prestamos, productos,
                          facturas, gastos, configuracion)

            QMessageBox.information(
                self,
                "Exportación exitosa",
                f"Archivo guardado en:\n{ruta}\n\n"
                f"Contenido exportado:\n"
                f"  • {len(ventas)} venta(s) en total\n"
                f"  • {len(prestamos)} préstamo(s)\n"
                f"  • {len(productos)} producto(s) de inventario\n"
                f"  • {len(facturas)} factura(s)\n"
                f"  • {len(gastos)} gasto(s) operativo(s)\n"
                f"  • Configuración incluida",
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
        # Los valores de comision/ganancia_neta ya vienen calculados desde el archivo;
        # completar_venta() solo recalcula si pagos_combinados está presente (correcto)
        # o si el método no es "Combinado" (standard).
        for año_m, mes_m in res.meses_afectados:
            eliminar_ventas_por_mes(año_m, mes_m)
        cfg_para_calc = res.configuracion if res.configuracion else cfg_actual
        for v in res.ventas:
            # Solo recalcular si los valores no vienen pre-calculados (template manual)
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
