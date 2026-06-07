"""
ui/config_panel.py
Panel de configuración del sistema: gastos fijos y comisiones.
Emite configuracion_guardada() al guardar para que MainWindow refresque todo.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QDoubleSpinBox, QSpinBox, QLineEdit,
    QPushButton, QFrame, QMessageBox, QScrollArea,
    QGroupBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from models.configuracion import Configuracion
from controllers.config_controller import ConfigController
from ui.venta_form import MoneyLineEdit
from utils.formatters import cop
from utils.logger import log


class ConfigPanel(QWidget):
    """
    Vista de configuración. Emite configuracion_guardada() al guardar.
    MainWindow conecta esta señal para refrescar dashboard e historial.
    """

    configuracion_guardada = Signal()
    tema_cambiado = Signal(bool)  # emitida al toggle dark mode (True = oscuro)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ctrl = ConfigController()
        self._build_ui()
        self._cargar_datos()
        self._connect_signals()

    # ------------------------------------------------------------------
    # Construcción de UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Scroll por si la ventana es pequeña
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        contenido = QWidget()
        root = QVBoxLayout(contenido)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        # Título
        titulo = QLabel("Configuración del Sistema")
        f = QFont(); f.setPointSize(16); f.setBold(True)
        titulo.setFont(f)
        root.addWidget(titulo)

        desc = QLabel(
            "Define los gastos fijos mensuales y las comisiones por método de pago. "
            "Estos valores afectan los cálculos de utilidad real en todas las vistas."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6B7280; font-size: 12px;")
        root.addWidget(desc)

        # Dos columnas
        cols = QHBoxLayout()
        cols.setSpacing(20)
        cols.addWidget(self._seccion_gastos(), stretch=1)
        cols.addWidget(self._seccion_comisiones(), stretch=1)
        root.addLayout(cols)

        # Preview de cálculos
        root.addWidget(self._panel_preview())

        # Botón guardar
        root.addLayout(self._fila_guardar())

        # Sección impresora térmica POS
        root.addWidget(self._seccion_impresora())

        # Apariencia y sesión (modo oscuro + timeout)
        root.addWidget(self._seccion_apariencia())

        # Sección de seguridad (cambio de contraseña)
        root.addWidget(self._seccion_seguridad())

        # Gestión de usuarios
        root.addWidget(self._seccion_usuarios())

        # Registro de auditoría
        root.addWidget(self._seccion_auditoria())
        root.addStretch()

        scroll.setWidget(contenido)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ---- Sección gastos fijos ----

    def _seccion_gastos(self) -> QGroupBox:
        box = QGroupBox("Gastos Fijos Mensuales")
        box.setStyleSheet(self._estilo_groupbox())
        form = QFormLayout(box)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.campo_arriendo    = self._campo_cop("1.200.000")
        self.campo_sueldo      = self._campo_cop("1.300.000")
        self.campo_servicios   = self._campo_cop("200.000")
        self.campo_otros       = self._campo_cop("0")

        self.campo_dias = QSpinBox()
        self.campo_dias.setRange(1, 31)
        self.campo_dias.setValue(30)
        self.campo_dias.setFixedHeight(34)
        self.campo_dias.setSuffix(" días")
        self.campo_dias.setStyleSheet(self._estilo_campo())

        form.addRow("Arriendo ($):", self.campo_arriendo)
        form.addRow("Sueldo ($):", self.campo_sueldo)
        form.addRow("Servicios ($):", self.campo_servicios)
        form.addRow("Otros gastos ($):", self.campo_otros)
        form.addRow("Días del mes:", self.campo_dias)

        return box

    # ---- Sección comisiones ----

    def _seccion_comisiones(self) -> QGroupBox:
        box = QGroupBox("Comisiones por Método de Pago")
        box.setStyleSheet(self._estilo_groupbox())
        form = QFormLayout(box)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.campo_addi          = self._campo_pct(5.0)
        self.campo_transferencia = self._campo_pct(0.0)

        form.addRow("Addi (%):", self.campo_addi)
        form.addRow("Transferencia (%):", self.campo_transferencia)

        # Info efectivo
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #E5E7EB; margin-top: 4px;")

        info = QLabel("Efectivo / Otro: 0 % (sin comisión)")
        info.setStyleSheet("color: #9CA3AF; font-size: 11px; padding-top: 4px;")

        form.addRow(sep)
        form.addRow(info)

        return box

    # ---- Panel preview ----

    def _panel_preview(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet(
            "QFrame { background:#F0FDF4; border:1px solid #BBF7D0; border-radius:10px; }"
        )
        lay = QHBoxLayout(frame)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(32)

        lay.addWidget(self._chip_preview("Total gastos / mes", "$ 0",  "total_mes"))
        lay.addWidget(self._vsep())
        lay.addWidget(self._chip_preview("Gasto operativo diario", "$ 0", "gasto_dia"))
        lay.addWidget(self._vsep())
        lay.addWidget(self._chip_preview("Días configurados", "30 días", "dias"))
        lay.addStretch()
        return frame

    def _chip_preview(self, etiqueta: str, valor: str, clave: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        lbl_e = QLabel(etiqueta)
        lbl_e.setStyleSheet("color:#15803D; font-size:10px; font-weight:bold;")
        lbl_v = QLabel(valor)
        f = QFont(); f.setPointSize(15); f.setBold(True)
        lbl_v.setFont(f)
        lbl_v.setStyleSheet("color:#166534;")
        v.addWidget(lbl_e)
        v.addWidget(lbl_v)
        setattr(self, f"_preview_{clave}", lbl_v)
        return w

    def _vsep(self) -> QFrame:
        s = QFrame(); s.setFrameShape(QFrame.VLine)
        s.setFixedHeight(40); s.setStyleSheet("color:#86EFAC;")
        return s

    # ---- Sección impresora ----

    def _seccion_impresora(self) -> QGroupBox:
        box = QGroupBox("Impresora Termica POS (ESC/POS)")
        box.setStyleSheet(self._estilo_groupbox())
        lay = QVBoxLayout(box)
        lay.setSpacing(10)

        desc = QLabel(
            "Selecciona la impresora termica conectada por USB. "
            "Con ESC/POS no habra papel en blanco ni texto cortado. "
            "Si no aparece, conecta la impresora y presiona Detectar."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#6B7280; font-size:11px;")
        lay.addWidget(desc)

        fila = QHBoxLayout()
        fila.setSpacing(8)

        self._combo_impresora = QComboBox()
        self._combo_impresora.setFixedHeight(34)
        self._combo_impresora.setEditable(True)
        fila.addWidget(self._combo_impresora, stretch=1)

        btn_detectar = QPushButton("Detectar")
        btn_detectar.setFixedHeight(34)
        btn_detectar.setFixedWidth(90)
        btn_detectar.setCursor(Qt.PointingHandCursor)
        btn_detectar.setStyleSheet(
            "QPushButton { background:#E5E7EB; color:#374151; border-radius:6px; font-size:11px; }"
            "QPushButton:hover { background:#D1D5DB; }"
        )
        btn_detectar.clicked.connect(self._detectar_impresoras)
        fila.addWidget(btn_detectar)

        lay.addLayout(fila)

        lbl_hint = QLabel(
            "Deja el campo vacio para usar el metodo PDF (visor del sistema)."
        )
        lbl_hint.setStyleSheet("color:#9CA3AF; font-size:10px;")
        lay.addWidget(lbl_hint)

        self._detectar_impresoras()
        return box

    def _detectar_impresoras(self) -> None:
        """Detecta impresoras disponibles y actualiza el ComboBox."""
        try:
            from services.escpos_printer import listar_impresoras_windows
            impresoras = listar_impresoras_windows()
        except Exception:
            impresoras = []

        actual = self._combo_impresora.currentText()
        self._combo_impresora.clear()
        self._combo_impresora.addItem("")  # opción vacía = sin ESC/POS
        for imp in impresoras:
            self._combo_impresora.addItem(imp)

        # Restaurar selección previa si sigue disponible
        idx = self._combo_impresora.findText(actual)
        if idx >= 0:
            self._combo_impresora.setCurrentIndex(idx)
        elif actual:
            self._combo_impresora.setEditText(actual)

    # ---- Sección apariencia ----

    def _seccion_apariencia(self) -> QGroupBox:
        box = QGroupBox("Apariencia y Sesión")
        box.setStyleSheet(self._estilo_groupbox())
        lay = QVBoxLayout(box)
        lay.setSpacing(14)

        # Modo oscuro
        fila_tema = QHBoxLayout()
        fila_tema.setSpacing(12)
        lbl_tema = QLabel("Tema de la aplicación:")
        lbl_tema.setStyleSheet("font-size:12px;")
        lbl_tema.setFixedWidth(180)

        self._btn_modo_oscuro = QPushButton("☀  Modo Claro")
        self._btn_modo_oscuro.setCheckable(True)
        self._btn_modo_oscuro.setFixedHeight(34)
        self._btn_modo_oscuro.setFixedWidth(160)
        self._btn_modo_oscuro.setCursor(Qt.PointingHandCursor)
        self._btn_modo_oscuro.setStyleSheet(
            "QPushButton { background:#F1F5F9; color:#374151; border:1px solid #D1D5DB;"
            "  border-radius:6px; font-size:12px; }"
            "QPushButton:hover { background:#E2E8F0; }"
            "QPushButton:checked { background:#1E293B; color:#F8FAFC; border-color:#0F172A; }"
            "QPushButton:checked:hover { background:#334155; }"
        )
        self._btn_modo_oscuro.clicked.connect(self._on_toggle_modo_oscuro)

        fila_tema.addWidget(lbl_tema)
        fila_tema.addWidget(self._btn_modo_oscuro)
        fila_tema.addStretch()
        lay.addLayout(fila_tema)

        # Timeout de sesión
        fila_timeout = QHBoxLayout()
        fila_timeout.setSpacing(12)
        lbl_timeout = QLabel("Bloquear sesión tras:")
        lbl_timeout.setStyleSheet("font-size:12px;")
        lbl_timeout.setFixedWidth(180)

        self._spin_timeout = QSpinBox()
        self._spin_timeout.setRange(1, 60)
        self._spin_timeout.setValue(10)
        self._spin_timeout.setSuffix(" min")
        self._spin_timeout.setFixedHeight(34)
        self._spin_timeout.setFixedWidth(100)
        self._spin_timeout.setStyleSheet(self._estilo_campo())

        lbl_hint = QLabel("de inactividad (1-60 min)")
        lbl_hint.setStyleSheet("color:#6B7280; font-size:11px;")

        fila_timeout.addWidget(lbl_timeout)
        fila_timeout.addWidget(self._spin_timeout)
        fila_timeout.addWidget(lbl_hint)
        fila_timeout.addStretch()
        lay.addLayout(fila_timeout)

        return box

    def _on_toggle_modo_oscuro(self, checked: bool) -> None:
        from ui.styles import aplicar_tema
        aplicar_tema(checked)
        self._btn_modo_oscuro.setText("☾  Modo Oscuro" if checked else "☀  Modo Claro")
        self.tema_cambiado.emit(checked)

    # ---- Sección seguridad ----

    def _seccion_seguridad(self) -> QGroupBox:
        box = QGroupBox("Seguridad — Contraseña de acceso")
        box.setStyleSheet(self._estilo_groupbox())
        form = QFormLayout(box)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        _style = self._estilo_campo()

        self._campo_clave_actual = QLineEdit()
        self._campo_clave_actual.setEchoMode(QLineEdit.Password)
        self._campo_clave_actual.setPlaceholderText("Contraseña actual")
        self._campo_clave_actual.setFixedHeight(34)
        self._campo_clave_actual.setStyleSheet(_style)

        self._campo_clave_nueva = QLineEdit()
        self._campo_clave_nueva.setEchoMode(QLineEdit.Password)
        self._campo_clave_nueva.setPlaceholderText("Nueva contraseña")
        self._campo_clave_nueva.setFixedHeight(34)
        self._campo_clave_nueva.setStyleSheet(_style)

        self._campo_clave_confirmar = QLineEdit()
        self._campo_clave_confirmar.setEchoMode(QLineEdit.Password)
        self._campo_clave_confirmar.setPlaceholderText("Confirmar nueva contraseña")
        self._campo_clave_confirmar.setFixedHeight(34)
        self._campo_clave_confirmar.setStyleSheet(_style)

        self._lbl_clave_feedback = QLabel("")
        self._lbl_clave_feedback.setStyleSheet("font-size:12px;")

        btn_cambiar = QPushButton("Cambiar contraseña")
        btn_cambiar.setFixedHeight(36)
        btn_cambiar.setFixedWidth(180)
        btn_cambiar.setCursor(Qt.PointingHandCursor)
        btn_cambiar.setStyleSheet(
            "QPushButton { background:#374151; color:white; border-radius:6px; font-size:11px; }"
            "QPushButton:hover { background:#1F2937; }"
        )
        btn_cambiar.clicked.connect(self._on_cambiar_clave)

        form.addRow("Contraseña actual:", self._campo_clave_actual)
        form.addRow("Nueva contraseña:", self._campo_clave_nueva)
        form.addRow("Confirmar:", self._campo_clave_confirmar)
        form.addRow("", self._lbl_clave_feedback)
        form.addRow("", btn_cambiar)

        info = QLabel(
            "Esta contraseña protege el acceso a Inventario y Configuración. "
            "Por defecto: YJB2026_*"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#9CA3AF; font-size:10px; padding-top:4px;")
        form.addRow(info)

        return box

    # ---- Sección gestión de usuarios ----

    def _seccion_usuarios(self) -> QGroupBox:
        box = QGroupBox("Gestión de Usuarios")
        box.setStyleSheet(self._estilo_groupbox())
        lay = QVBoxLayout(box)
        lay.setSpacing(10)

        desc = QLabel(
            "Administra los usuarios que pueden iniciar sesión. "
            "El usuario Admin siempre existe. Los vendedores no tienen acceso a Configuración ni Exportar."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#6B7280; font-size:11px;")
        lay.addWidget(desc)

        # Tabla de usuarios
        self._tabla_usuarios = QTableWidget()
        self._tabla_usuarios.setColumnCount(3)
        self._tabla_usuarios.setHorizontalHeaderLabels(["Nombre", "Rol", "Acciones"])
        self._tabla_usuarios.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla_usuarios.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_usuarios.verticalHeader().setVisible(False)
        self._tabla_usuarios.setShowGrid(False)
        self._tabla_usuarios.setAlternatingRowColors(True)
        self._tabla_usuarios.setMaximumHeight(140)
        self._tabla_usuarios.setStyleSheet(
            "QTableWidget { border:1px solid #E5E7EB; border-radius:6px; font-size:11px; }"
            "QHeaderView::section { font-weight:bold; border:none; padding:5px; font-size:10px; }"
        )
        hh = self._tabla_usuarios.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        self._tabla_usuarios.setColumnWidth(1, 90)
        hh.setSectionResizeMode(2, QHeaderView.Fixed)
        self._tabla_usuarios.setColumnWidth(2, 80)
        lay.addWidget(self._tabla_usuarios)

        # Formulario para nuevo usuario
        fila_nuevo = QHBoxLayout()
        fila_nuevo.setSpacing(8)

        self._campo_nuevo_usuario = QLineEdit()
        self._campo_nuevo_usuario.setPlaceholderText("Nombre del nuevo usuario")
        self._campo_nuevo_usuario.setFixedHeight(32)
        self._campo_nuevo_usuario.setStyleSheet(self._estilo_campo())

        self._combo_rol_nuevo = QComboBox()
        self._combo_rol_nuevo.addItems(["vendedor", "admin"])
        self._combo_rol_nuevo.setFixedHeight(32)
        self._combo_rol_nuevo.setFixedWidth(100)

        self._campo_clave_nuevo = QLineEdit()
        self._campo_clave_nuevo.setEchoMode(QLineEdit.Password)
        self._campo_clave_nuevo.setPlaceholderText("Contraseña")
        self._campo_clave_nuevo.setFixedHeight(32)
        self._campo_clave_nuevo.setStyleSheet(self._estilo_campo())

        btn_crear = QPushButton("+ Crear")
        btn_crear.setFixedHeight(32)
        btn_crear.setFixedWidth(75)
        btn_crear.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:5px; font-size:11px; }"
            "QPushButton:hover { background:#1D4ED8; }"
        )
        btn_crear.clicked.connect(self._on_crear_usuario)

        fila_nuevo.addWidget(self._campo_nuevo_usuario, stretch=2)
        fila_nuevo.addWidget(self._combo_rol_nuevo)
        fila_nuevo.addWidget(self._campo_clave_nuevo, stretch=1)
        fila_nuevo.addWidget(btn_crear)
        lay.addLayout(fila_nuevo)

        self._lbl_usuarios_feedback = QLabel("")
        self._lbl_usuarios_feedback.setStyleSheet("font-size:11px;")
        lay.addWidget(self._lbl_usuarios_feedback)

        # Subsección: cambiar contraseña de cualquier usuario
        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color:#E5E7EB; margin:4px 0;")
        lay.addWidget(sep2)

        lbl_cambiar = QLabel("Cambiar contraseña de usuario:")
        lbl_cambiar.setStyleSheet("font-size:11px; font-weight:bold; color:#374151;")
        lay.addWidget(lbl_cambiar)

        fila_cambiar = QHBoxLayout()
        fila_cambiar.setSpacing(8)

        self._combo_usuario_clave = QComboBox()
        self._combo_usuario_clave.setFixedHeight(32)
        self._combo_usuario_clave.setMinimumWidth(130)

        self._campo_clave_user_nueva = QLineEdit()
        self._campo_clave_user_nueva.setEchoMode(QLineEdit.Password)
        self._campo_clave_user_nueva.setPlaceholderText("Nueva contraseña")
        self._campo_clave_user_nueva.setFixedHeight(32)
        self._campo_clave_user_nueva.setStyleSheet(self._estilo_campo())

        self._campo_clave_user_confirmar = QLineEdit()
        self._campo_clave_user_confirmar.setEchoMode(QLineEdit.Password)
        self._campo_clave_user_confirmar.setPlaceholderText("Confirmar")
        self._campo_clave_user_confirmar.setFixedHeight(32)
        self._campo_clave_user_confirmar.setStyleSheet(self._estilo_campo())

        btn_cambiar_user = QPushButton("Actualizar")
        btn_cambiar_user.setFixedHeight(32)
        btn_cambiar_user.setFixedWidth(90)
        btn_cambiar_user.setStyleSheet(
            "QPushButton { background:#374151; color:white; border-radius:5px; font-size:11px; }"
            "QPushButton:hover { background:#1F2937; }"
        )
        btn_cambiar_user.clicked.connect(self._on_cambiar_clave_usuario)

        fila_cambiar.addWidget(self._combo_usuario_clave)
        fila_cambiar.addWidget(self._campo_clave_user_nueva, stretch=1)
        fila_cambiar.addWidget(self._campo_clave_user_confirmar, stretch=1)
        fila_cambiar.addWidget(btn_cambiar_user)
        lay.addLayout(fila_cambiar)

        self._lbl_clave_user_feedback = QLabel("")
        self._lbl_clave_user_feedback.setStyleSheet("font-size:11px;")
        lay.addWidget(self._lbl_clave_user_feedback)

        self._cargar_tabla_usuarios()
        return box

    def _cargar_tabla_usuarios(self) -> None:
        from database.usuarios_repo import obtener_todos_usuarios
        usuarios = obtener_todos_usuarios()
        self._tabla_usuarios.setRowCount(len(usuarios))
        for row, u in enumerate(usuarios):
            self._tabla_usuarios.setRowHeight(row, 28)
            self._tabla_usuarios.setItem(row, 0, QTableWidgetItem(u.nombre))
            item_rol = QTableWidgetItem("Admin" if u.rol == "admin" else "Vendedor")
            item_rol.setForeground(QColor("#1D4ED8") if u.rol == "admin" else QColor("#374151"))
            self._tabla_usuarios.setItem(row, 1, item_rol)
            if u.nombre != "Admin":
                btn_del = QPushButton("Borrar")
                btn_del.setFixedHeight(22)
                btn_del.setStyleSheet(
                    "QPushButton { background:#FEE2E2; color:#DC2626; border:none;"
                    "border-radius:3px; font-size:10px; }"
                    "QPushButton:hover { background:#FECACA; }"
                )
                btn_del.clicked.connect(lambda _, uid=u.id: self._on_eliminar_usuario(uid))
                self._tabla_usuarios.setCellWidget(row, 2, btn_del)
        # Refrescar combo de cambio de clave
        if hasattr(self, "_combo_usuario_clave"):
            sel_actual = self._combo_usuario_clave.currentText()
            self._combo_usuario_clave.clear()
            for u in usuarios:
                self._combo_usuario_clave.addItem(u.nombre, userData=u.id)
            idx = self._combo_usuario_clave.findText(sel_actual)
            if idx >= 0:
                self._combo_usuario_clave.setCurrentIndex(idx)

    def _on_crear_usuario(self) -> None:
        nombre = self._campo_nuevo_usuario.text().strip()
        rol = self._combo_rol_nuevo.currentText()
        clave = self._campo_clave_nuevo.text()
        if not nombre or not clave:
            self._lbl_usuarios_feedback.setText("Completa nombre y contraseña.")
            self._lbl_usuarios_feedback.setStyleSheet("font-size:11px; color:#DC2626;")
            return
        if len(clave) < 4:
            self._lbl_usuarios_feedback.setText("La contraseña debe tener mínimo 4 caracteres.")
            self._lbl_usuarios_feedback.setStyleSheet("font-size:11px; color:#DC2626;")
            return
        try:
            from database.usuarios_repo import insertar_usuario, Usuario
            from utils.security import hashear_clave
            insertar_usuario(Usuario(nombre=nombre, rol=rol, clave_hash=hashear_clave(clave)))
            self._campo_nuevo_usuario.clear()
            self._campo_clave_nuevo.clear()
            self._lbl_usuarios_feedback.setText(f"✔ Usuario '{nombre}' creado.")
            self._lbl_usuarios_feedback.setStyleSheet("font-size:11px; color:#15803D;")
            self._cargar_tabla_usuarios()
            import utils.auditoria as auditoria
            auditoria.registrar("Usuario creado", f"{nombre} ({rol})")
        except Exception as exc:
            self._lbl_usuarios_feedback.setText(f"Error: {exc}")
            self._lbl_usuarios_feedback.setStyleSheet("font-size:11px; color:#DC2626;")

    def _on_eliminar_usuario(self, usuario_id: int) -> None:
        resp = QMessageBox.question(
            self, "Eliminar usuario", "¿Eliminar este usuario?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resp == QMessageBox.Yes:
            from database.usuarios_repo import eliminar_usuario
            eliminar_usuario(usuario_id)
            self._cargar_tabla_usuarios()
            import utils.auditoria as auditoria
            auditoria.registrar("Usuario eliminado", f"id={usuario_id}")

    def _on_cambiar_clave_usuario(self) -> None:
        self._lbl_clave_user_feedback.setText("")
        nombre = self._combo_usuario_clave.currentText()
        uid = self._combo_usuario_clave.currentData()
        nueva = self._campo_clave_user_nueva.text()
        confirmar = self._campo_clave_user_confirmar.text()

        if not nombre or uid is None:
            self._lbl_clave_user_feedback.setText("Selecciona un usuario.")
            self._lbl_clave_user_feedback.setStyleSheet("font-size:11px; color:#DC2626;")
            return
        if not nueva or not confirmar:
            self._lbl_clave_user_feedback.setText("Completa los dos campos de contraseña.")
            self._lbl_clave_user_feedback.setStyleSheet("font-size:11px; color:#DC2626;")
            return
        if nueva != confirmar:
            self._lbl_clave_user_feedback.setText("Las contraseñas no coinciden.")
            self._lbl_clave_user_feedback.setStyleSheet("font-size:11px; color:#DC2626;")
            return
        if len(nueva) < 4:
            self._lbl_clave_user_feedback.setText("Mínimo 4 caracteres.")
            self._lbl_clave_user_feedback.setStyleSheet("font-size:11px; color:#DC2626;")
            return

        from database.usuarios_repo import actualizar_clave_usuario
        from utils.security import hashear_clave
        actualizar_clave_usuario(uid, hashear_clave(nueva))
        self._campo_clave_user_nueva.clear()
        self._campo_clave_user_confirmar.clear()
        self._lbl_clave_user_feedback.setText(f"✔  Contraseña de '{nombre}' actualizada.")
        self._lbl_clave_user_feedback.setStyleSheet("font-size:11px; color:#15803D;")
        import utils.auditoria as auditoria
        auditoria.registrar("Contraseña de usuario cambiada", f"{nombre} (id={uid})")

    # ---- Sección auditoría ----

    def _seccion_auditoria(self) -> QGroupBox:
        box = QGroupBox("Registro de Auditoría")
        box.setStyleSheet(self._estilo_groupbox())
        lay = QVBoxLayout(box)
        lay.setSpacing(8)

        desc = QLabel("Últimas 50 acciones registradas en el sistema.")
        desc.setStyleSheet("color:#6B7280; font-size:11px;")
        lay.addWidget(desc)

        fila_btn = QHBoxLayout()
        btn_refrescar = QPushButton("↻ Actualizar")
        btn_refrescar.setFixedHeight(28)
        btn_refrescar.setFixedWidth(110)
        btn_refrescar.setStyleSheet(
            "QPushButton { background:#F1F5F9; color:#374151; border:1px solid #D1D5DB;"
            "border-radius:5px; font-size:11px; }"
            "QPushButton:hover { background:#E2E8F0; }"
        )
        btn_refrescar.clicked.connect(self._cargar_tabla_auditoria)
        fila_btn.addWidget(btn_refrescar)
        fila_btn.addStretch()
        lay.addLayout(fila_btn)

        self._tabla_auditoria = QTableWidget()
        self._tabla_auditoria.setColumnCount(5)
        self._tabla_auditoria.setHorizontalHeaderLabels(["Fecha", "Hora", "Usuario", "Acción", "Detalle"])
        self._tabla_auditoria.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tabla_auditoria.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tabla_auditoria.verticalHeader().setVisible(False)
        self._tabla_auditoria.setShowGrid(False)
        self._tabla_auditoria.setAlternatingRowColors(True)
        self._tabla_auditoria.setMaximumHeight(220)
        self._tabla_auditoria.setStyleSheet(
            "QTableWidget { border:1px solid #E5E7EB; border-radius:6px; font-size:11px; }"
            "QHeaderView::section { background:#1E293B; color:white; font-weight:bold;"
            "  border:none; padding:5px; font-size:10px; }"
            "QTableWidget::item:selected { background:#DBEAFE; color:#1E3A5F; }"
        )
        hh = self._tabla_auditoria.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Interactive); self._tabla_auditoria.setColumnWidth(0, 90)
        hh.setSectionResizeMode(1, QHeaderView.Interactive); self._tabla_auditoria.setColumnWidth(1, 70)
        hh.setSectionResizeMode(2, QHeaderView.Interactive); self._tabla_auditoria.setColumnWidth(2, 100)
        hh.setSectionResizeMode(3, QHeaderView.Interactive); self._tabla_auditoria.setColumnWidth(3, 160)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        lay.addWidget(self._tabla_auditoria)

        self._cargar_tabla_auditoria()
        return box

    def _cargar_tabla_auditoria(self) -> None:
        from utils.auditoria import obtener_log
        registros = obtener_log(50)
        self._tabla_auditoria.setRowCount(len(registros))
        for row, r in enumerate(registros):
            self._tabla_auditoria.setRowHeight(row, 24)
            for col, campo in enumerate(["fecha", "hora", "usuario", "accion", "detalle"]):
                self._tabla_auditoria.setItem(row, col, QTableWidgetItem(r.get(campo, "")))

    # ---- Fila guardar ----

    def _fila_guardar(self) -> QHBoxLayout:
        lay = QHBoxLayout()

        self._lbl_feedback = QLabel("")
        self._lbl_feedback.setStyleSheet("font-size:12px; color:#15803D;")

        self.btn_guardar = QPushButton("Guardar Configuración")
        self.btn_guardar.setFixedHeight(42)
        self.btn_guardar.setFixedWidth(220)
        f = QFont(); f.setPointSize(11); f.setBold(True)
        self.btn_guardar.setFont(f)
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:7px; }"
            "QPushButton:hover { background:#1D4ED8; }"
            "QPushButton:pressed { background:#1E40AF; }"
        )
        self.btn_guardar.clicked.connect(self._on_guardar)

        lay.addWidget(self._lbl_feedback)
        lay.addStretch()
        lay.addWidget(self.btn_guardar)
        return lay

    # ------------------------------------------------------------------
    # Helpers de construcción
    # ------------------------------------------------------------------

    def _campo_cop(self, placeholder: str = "") -> MoneyLineEdit:
        campo = MoneyLineEdit()
        campo.setPlaceholderText("0")
        campo.setFixedHeight(34)
        campo.setStyleSheet(self._estilo_campo())
        return campo

    def _campo_pct(self, valor: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 100.0)
        spin.setDecimals(2)
        spin.setSingleStep(0.5)
        spin.setValue(valor)
        spin.setSuffix(" %")
        spin.setFixedHeight(34)
        spin.setStyleSheet(self._estilo_campo())
        return spin

    @staticmethod
    def _estilo_campo() -> str:
        return ""

    @staticmethod
    def _estilo_groupbox() -> str:
        return ""

    # ------------------------------------------------------------------
    # Carga y guardado
    # ------------------------------------------------------------------

    def _cargar_datos(self) -> None:
        """Precarga los campos con la configuración actual de la BD."""
        cfg = self._ctrl.cargar()

        self.campo_arriendo.set_valor(int(cfg.arriendo))
        self.campo_sueldo.set_valor(int(cfg.sueldo))
        self.campo_servicios.set_valor(int(cfg.servicios))
        self.campo_otros.set_valor(int(cfg.otros_gastos))
        self.campo_dias.setValue(cfg.dias_mes)

        self.campo_addi.setValue(cfg.comision_addi)
        self.campo_transferencia.setValue(cfg.comision_transferencia)

        # Apariencia
        self._btn_modo_oscuro.setChecked(cfg.modo_oscuro)
        self._btn_modo_oscuro.setText("☾  Modo Oscuro" if cfg.modo_oscuro else "☀  Modo Claro")
        self._spin_timeout.setValue(cfg.timeout_minutos)

        # Impresora guardada
        idx = self._combo_impresora.findText(cfg.nombre_impresora)
        if idx >= 0:
            self._combo_impresora.setCurrentIndex(idx)
        elif cfg.nombre_impresora:
            self._combo_impresora.setEditText(cfg.nombre_impresora)

        self._actualizar_preview()

    def _connect_signals(self) -> None:
        for campo in (self.campo_arriendo, self.campo_sueldo,
                      self.campo_servicios, self.campo_otros):
            campo.textChanged.connect(self._actualizar_preview)
        self.campo_dias.valueChanged.connect(self._actualizar_preview)

    def _actualizar_preview(self) -> None:
        """Actualiza los chips de totales en tiempo real mientras el usuario escribe."""
        total = (
            self._parse_int(self.campo_arriendo.text()) +
            self._parse_int(self.campo_sueldo.text()) +
            self._parse_int(self.campo_servicios.text()) +
            self._parse_int(self.campo_otros.text())
        )
        dias = self.campo_dias.value() or 30
        diario = round(total / dias, 2)

        self._preview_total_mes.setText(cop(total))
        self._preview_gasto_dia.setText(cop(diario))
        self._preview_dias.setText(f"{dias} días")

    def _on_guardar(self) -> None:
        try:
            from database.config_repo import obtener_configuracion
            cfg_actual = obtener_configuracion()
            cfg = Configuracion(
                arriendo=float(self._parse_int(self.campo_arriendo.text())),
                sueldo=float(self._parse_int(self.campo_sueldo.text())),
                servicios=float(self._parse_int(self.campo_servicios.text())),
                otros_gastos=float(self._parse_int(self.campo_otros.text())),
                dias_mes=self.campo_dias.value(),
                comision_bold=cfg_actual.comision_bold,
                comision_addi=self.campo_addi.value(),
                comision_transferencia=self.campo_transferencia.value(),
                clave_inventario=cfg_actual.clave_inventario,
                nombre_impresora=self._combo_impresora.currentText().strip(),
                modo_oscuro=self._btn_modo_oscuro.isChecked(),
                timeout_minutos=self._spin_timeout.value(),
            )
            self._ctrl.guardar(cfg)
            self._lbl_feedback.setText("✔  Configuración guardada correctamente.")
            self._lbl_feedback.setStyleSheet("font-size:12px; color:#15803D;")
            self.configuracion_guardada.emit()
            import utils.auditoria as auditoria
            auditoria.registrar("Configuración actualizada")
        except ValueError as exc:
            log.warning("Error de validación al guardar configuración: %s", exc)
            self._lbl_feedback.setText("")
            QMessageBox.warning(self, "Error de validación", str(exc))

    def _on_cambiar_clave(self) -> None:
        self._lbl_clave_feedback.setText("")
        actual = self._campo_clave_actual.text()
        nueva = self._campo_clave_nueva.text()
        confirmar = self._campo_clave_confirmar.text()

        if not actual or not nueva or not confirmar:
            self._lbl_clave_feedback.setText("Completa los tres campos.")
            self._lbl_clave_feedback.setStyleSheet("font-size:12px; color:#DC2626;")
            return

        from database.config_repo import obtener_configuracion, guardar_configuracion
        from utils.security import verificar_clave, hashear_clave
        cfg_actual = obtener_configuracion()

        if not verificar_clave(actual, cfg_actual.clave_inventario):
            self._lbl_clave_feedback.setText("Contraseña actual incorrecta.")
            self._lbl_clave_feedback.setStyleSheet("font-size:12px; color:#DC2626;")
            return

        if nueva != confirmar:
            self._lbl_clave_feedback.setText("Las contraseñas nuevas no coinciden.")
            self._lbl_clave_feedback.setStyleSheet("font-size:12px; color:#DC2626;")
            return

        if len(nueva) < 4:
            self._lbl_clave_feedback.setText("La nueva contraseña debe tener al menos 4 caracteres.")
            self._lbl_clave_feedback.setStyleSheet("font-size:12px; color:#DC2626;")
            return

        cfg_actual.clave_inventario = hashear_clave(nueva)
        guardar_configuracion(cfg_actual)

        self._campo_clave_actual.clear()
        self._campo_clave_nueva.clear()
        self._campo_clave_confirmar.clear()
        self._lbl_clave_feedback.setText("✔  Contraseña actualizada correctamente.")
        self._lbl_clave_feedback.setStyleSheet("font-size:12px; color:#15803D;")
        import utils.auditoria as auditoria
        auditoria.registrar("Contraseña cambiada")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def reload(self) -> None:
        """Recarga los valores desde la BD (por si cambiaron externamente)."""
        self._cargar_datos()
        self._lbl_feedback.setText("")

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_int(texto: str) -> int:
        try:
            limpio = "".join(c for c in texto if c.isdigit())
            return int(limpio) if limpio else 0
        except ValueError:
            return 0
