"""
ui/exportar_importar_panel.py
Centro unificado de exportación e importación de datos.
Un solo archivo Excel con tres hojas: Ventas | Préstamos | Inventario.
"""

from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QFrame, QMessageBox, QFileDialog,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from utils.formatters import MESES_ES, nombre_mes, cop


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
            "Un único archivo Excel con todo el contenido: ventas del mes, préstamos e inventario."
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
            "Elige el mes y genera el archivo. Incluye:"
        ))

        for linea in (
            "  • Ventas del mes seleccionado",
            "  • Todos los préstamos (todos los estados)",
            "  • Inventario completo (snapshot de hoy)",
        ):
            l = QLabel(linea)
            l.setStyleSheet("color:#374151; font-size:12px; background:transparent; border:none;")
            lay.addWidget(l)

        lay.addWidget(self._sep_interno())

        # Selector mes / año
        fila_mes = QHBoxLayout()
        fila_mes.setSpacing(8)
        lbl_mes = QLabel("Mes:")
        lbl_mes.setStyleSheet("color:#374151; font-size:12px; background:transparent; border:none;")

        self.combo_mes = QComboBox()
        self.combo_mes.setFixedHeight(32)
        self.combo_mes.setFixedWidth(120)
        self.combo_mes.setStyleSheet(
            "QComboBox { background:white; color:#1E293B; border:1px solid #D1D5DB;"
            "border-radius:5px; padding:0 8px; }"
            "QComboBox QAbstractItemView { background:white; color:#1E293B;"
            "selection-background-color:#DBEAFE; }"
        )
        for num, nombre in MESES_ES.items():
            self.combo_mes.addItem(nombre, num)
        self.combo_mes.setCurrentIndex(date.today().month - 1)

        self.spin_año = QSpinBox()
        self.spin_año.setRange(2020, 2040)
        self.spin_año.setValue(date.today().year)
        self.spin_año.setFixedHeight(32)
        self.spin_año.setFixedWidth(75)
        self.spin_año.setButtonSymbols(QSpinBox.NoButtons)
        self.spin_año.setStyleSheet(
            "QSpinBox { background:white; color:#1E293B; border:1px solid #D1D5DB;"
            "border-radius:5px; padding:0 8px; }"
        )

        fila_mes.addWidget(lbl_mes)
        fila_mes.addWidget(self.combo_mes)
        fila_mes.addWidget(self.spin_año)
        fila_mes.addStretch()
        lay.addLayout(fila_mes)

        btn = QPushButton("⬇  Exportar Todo")
        btn.setFixedHeight(42)
        btn.setStyleSheet(
            "QPushButton { background:#16A34A; color:white; border-radius:7px;"
            "font-size:13px; font-weight:bold; }"
            "QPushButton:hover { background:#15803D; }"
        )
        btn.clicked.connect(self._on_exportar)
        lay.addWidget(btn)

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
            "  • Las ventas del mes del archivo se REEMPLAZARÁN",
            "  • Todos los préstamos se REEMPLAZARÁN",
            "  • Todo el inventario se REEMPLAZARÁ",
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

    def _on_exportar(self) -> None:
        mes = self.combo_mes.currentData()
        año = self.spin_año.value()
        nombre_sugerido = f"YJBMOTOCOM_{año}-{mes:02d}.xlsx"

        ruta, _ = QFileDialog.getSaveFileName(
            self, "Guardar archivo de datos", nombre_sugerido, "Excel (*.xlsx)"
        )
        if not ruta:
            return

        try:
            from services.exportador import exportar_todo
            from database.ventas_repo import obtener_ventas_por_mes
            from database.prestamos_repo import obtener_todos_prestamos
            from database.inventario_repo import obtener_todos_productos

            ventas    = obtener_ventas_por_mes(año, mes)
            prestamos = obtener_todos_prestamos()
            productos = obtener_todos_productos()

            exportar_todo(Path(ruta), año, mes, ventas, prestamos, productos)

            QMessageBox.information(
                self,
                "Exportación exitosa",
                f"Archivo guardado en:\n{ruta}\n\n"
                f"Contenido exportado:\n"
                f"  • {len(ventas)} venta(s) de {nombre_mes(mes, año)}\n"
                f"  • {len(prestamos)} préstamo(s)\n"
                f"  • {len(productos)} producto(s) de inventario",
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

        # Construir descripción del período
        periodo = nombre_mes(res.mes, res.año) if res.mes and res.año else "período desconocido"

        confirmacion = (
            f"¿Confirmar importación?\n\n"
            f"Se REEMPLAZARÁ el siguiente contenido:\n"
            f"  • {len(res.ventas)} venta(s) del mes {periodo}\n"
            f"  • {len(res.prestamos)} préstamo(s) (todos los existentes)\n"
            f"  • {len(res.productos)} producto(s) de inventario (todo el inventario)\n\n"
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
                f"  • {len(res.productos)} producto(s)",
            )
            self.datos_importados.emit()
        except Exception as exc:
            QMessageBox.critical(self, "Error durante la importación", str(exc))

    def _ejecutar_importacion(self, res) -> None:
        """Reemplaza ventas del mes, préstamos e inventario con los datos del archivo."""
        from database.ventas_repo import (
            eliminar_ventas_por_mes, insertar_venta,
        )
        from database.prestamos_repo import (
            eliminar_todos_prestamos, insertar_prestamo,
        )
        from database.inventario_repo import (
            eliminar_todo_inventario, insertar_producto,
        )
        from services.calculator import completar_venta
        from database.config_repo import obtener_configuracion

        cfg = obtener_configuracion()

        # Ventas del mes
        if res.mes and res.año:
            eliminar_ventas_por_mes(res.año, res.mes)
            for v in res.ventas:
                completar_venta(v, cfg)
                insertar_venta(v)

        # Préstamos
        eliminar_todos_prestamos()
        for p in res.prestamos:
            insertar_prestamo(p)

        # Inventario
        eliminar_todo_inventario()
        for prod in res.productos:
            insertar_producto(prod)
