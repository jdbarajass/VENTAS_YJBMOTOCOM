"""
ui/login_dialog.py
Diálogo de inicio de sesión con selección de usuario por tarjeta.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from database.usuarios_repo import obtener_todos_usuarios, Usuario
from utils.security import verificar_clave
from ui.styles import es_modo_oscuro
import utils.auditoria as auditoria


class LoginDialog(QDialog):
    """
    Diálogo de login.
    Tras aceptar, expone `usuario_nombre` y `usuario_rol`.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("YJBMOTOCOM — Inicio de sesión")
        self.setFixedSize(440, 480)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setStyleSheet("background:#F8FAFC;")

        self.usuario_nombre: str = ""
        self.usuario_rol: str = ""
        self._usuario_sel: Usuario | None = None

        self._build_ui()
        self._cargar_usuarios()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 30, 36, 30)
        root.setSpacing(14)

        # Cabecera
        titulo = QLabel("YJBMOTOCOM")
        f = QFont(); f.setPointSize(22); f.setBold(True)
        titulo.setFont(f)
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("color:#1E293B;")
        root.addWidget(titulo)

        sub = QLabel("Selecciona tu usuario para continuar")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color:#6B7280; font-size:12px;")
        root.addWidget(sub)

        root.addSpacing(4)

        # Área de tarjetas
        self._lay_usuarios = QHBoxLayout()
        self._lay_usuarios.setSpacing(12)
        self._lay_usuarios.setAlignment(Qt.AlignCenter)
        root.addLayout(self._lay_usuarios)

        # Separador
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#E5E7EB; margin:4px 0;")
        root.addWidget(sep)

        # Indicador de usuario seleccionado
        self._lbl_sel = QLabel("← Haz clic en un usuario")
        self._lbl_sel.setAlignment(Qt.AlignCenter)
        self._lbl_sel.setStyleSheet("color:#9CA3AF; font-size:11px;")
        root.addWidget(self._lbl_sel)

        # Campo contraseña
        self._campo_clave = QLineEdit()
        self._campo_clave.setEchoMode(QLineEdit.Password)
        self._campo_clave.setPlaceholderText("Contraseña")
        self._campo_clave.setFixedHeight(42)
        self._campo_clave.setStyleSheet(
            "QLineEdit { border-radius:8px; padding:0 14px; font-size:14px; }"
            "QLineEdit:focus { border:2px solid #2563EB; }"
            "QLineEdit:disabled { color:#9CA3AF; }"
        )
        self._campo_clave.setEnabled(False)
        self._campo_clave.returnPressed.connect(self._on_ingresar)
        root.addWidget(self._campo_clave)

        # Error
        self._lbl_error = QLabel("")
        self._lbl_error.setStyleSheet("color:#DC2626; font-size:11px;")
        self._lbl_error.setAlignment(Qt.AlignCenter)
        self._lbl_error.setFixedHeight(18)
        root.addWidget(self._lbl_error)

        # Botón ingresar
        self._btn_ingresar = QPushButton("Ingresar")
        self._btn_ingresar.setFixedHeight(46)
        f2 = QFont(); f2.setPointSize(12); f2.setBold(True)
        self._btn_ingresar.setFont(f2)
        self._btn_ingresar.setEnabled(False)
        self._btn_ingresar.setStyleSheet(
            "QPushButton { background:#2563EB; color:white; border-radius:8px; border:none; }"
            "QPushButton:hover { background:#1D4ED8; }"
            "QPushButton:pressed { background:#1E40AF; }"
            "QPushButton:disabled { background:#93C5FD; color:white; }"
        )
        self._btn_ingresar.clicked.connect(self._on_ingresar)
        root.addWidget(self._btn_ingresar)

        root.addStretch()

    def _cargar_usuarios(self) -> None:
        usuarios = obtener_todos_usuarios()
        for u in usuarios:
            self._lay_usuarios.addWidget(self._tarjeta_usuario(u))

    def _tarjeta_usuario(self, u: Usuario) -> QFrame:
        frame = QFrame()
        frame.setFixedSize(110, 100)
        frame.setCursor(Qt.PointingHandCursor)
        frame.setObjectName(f"tarjeta_{u.nombre}")
        frame._usuario = u
        frame._seleccionada = False
        _bg = "#1E293B" if es_modo_oscuro() else "#FFFFFF"
        _border = "#475569" if es_modo_oscuro() else "#E5E7EB"
        frame.setStyleSheet(
            f"QFrame {{ background:{_bg}; border:2px solid {_border}; border-radius:12px; }}"
        )

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(8, 10, 8, 8)
        lay.setSpacing(3)
        lay.setAlignment(Qt.AlignCenter)

        icono = QLabel("👑" if u.rol == "admin" else "👤")
        icono.setAlignment(Qt.AlignCenter)
        icono.setStyleSheet("font-size:30px; background:transparent;")
        lay.addWidget(icono)

        nombre = QLabel(u.nombre)
        nombre.setAlignment(Qt.AlignCenter)
        nombre.setStyleSheet(
            "font-size:11px; font-weight:bold; color:#1E293B; background:transparent;"
        )
        nombre.setWordWrap(True)
        lay.addWidget(nombre)

        rol_txt = "Admin" if u.rol == "admin" else "Vendedor"
        color_rol = "#1D4ED8" if u.rol == "admin" else "#6B7280"
        rol_lbl = QLabel(rol_txt)
        rol_lbl.setAlignment(Qt.AlignCenter)
        rol_lbl.setStyleSheet(
            f"font-size:9px; color:{color_rol}; background:transparent;"
        )
        lay.addWidget(rol_lbl)

        frame.mousePressEvent = lambda _evt, f=frame, user=u: self._seleccionar(f, user)
        return frame

    def _seleccionar(self, frame: QFrame, usuario: Usuario) -> None:
        # Des-seleccionar cualquier tarjeta previa
        _bg = "#1E293B" if es_modo_oscuro() else "#FFFFFF"
        _border = "#475569" if es_modo_oscuro() else "#E5E7EB"
        for child in self.findChildren(QFrame):
            if hasattr(child, "_usuario"):
                child.setStyleSheet(
                    f"QFrame {{ background:{_bg}; border:2px solid {_border}; border-radius:12px; }}"
                )

        frame.setStyleSheet(
            "QFrame { background:#EFF6FF; border:2px solid #2563EB; border-radius:12px; }"
        )
        self._usuario_sel = usuario
        self._lbl_sel.setText(f"Usuario seleccionado: {usuario.nombre}")
        self._lbl_sel.setStyleSheet(
            "color:#1D4ED8; font-size:11px; font-weight:bold;"
        )
        self._lbl_error.setText("")
        self._campo_clave.setEnabled(True)
        self._btn_ingresar.setEnabled(True)
        self._campo_clave.clear()
        self._campo_clave.setFocus()

    # ------------------------------------------------------------------
    # Acción
    # ------------------------------------------------------------------

    def _on_ingresar(self) -> None:
        if self._usuario_sel is None:
            self._lbl_error.setText("Selecciona un usuario primero.")
            return

        clave = self._campo_clave.text()
        if not clave:
            self._lbl_error.setText("Ingresa la contraseña.")
            return

        if not verificar_clave(clave, self._usuario_sel.clave_hash):
            self._lbl_error.setText("Contraseña incorrecta.")
            self._campo_clave.clear()
            self._campo_clave.setFocus()
            return

        self.usuario_nombre = self._usuario_sel.nombre
        self.usuario_rol = self._usuario_sel.rol
        auditoria.set_usuario(self.usuario_nombre)
        auditoria.registrar("Inicio de sesión", f"Rol: {self.usuario_rol}")
        self.accept()
