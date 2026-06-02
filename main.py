"""
main.py — Punto de entrada de YJBMOTOCOM.

Responsabilidades:
- Inicializar QApplication con configuración global.
- Instanciar MainWindow.
- Arrancar el event loop.

NO contiene lógica de negocio ni acceso a datos.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox
from database.schema import initialize_schema
from database.connection import DatabaseConnection
from ui.main_window import MainWindow
from ui.styles import GLOBAL_STYLESHEET
from utils.backup import hacer_backup
from utils.logger import log

# Directorio raíz del proyecto (funciona tanto en desarrollo como en .exe)
_BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))


def _migrar_clave_a_hash() -> None:
    """Si la contraseña guardada es plain-text, la convierte a SHA-256 al arrancar."""
    from database.config_repo import obtener_configuracion, guardar_configuracion
    from utils.security import es_hash, hashear_clave
    cfg = obtener_configuracion()
    if not es_hash(cfg.clave_inventario):
        cfg.clave_inventario = hashear_clave(cfg.clave_inventario)
        guardar_configuracion(cfg)


def _sembrar_admin_si_vacio() -> None:
    """Si la tabla usuarios está vacía, crea un usuario Admin con la contraseña existente."""
    from database.usuarios_repo import contar_usuarios, insertar_usuario, Usuario
    from database.config_repo import obtener_configuracion
    if contar_usuarios() == 0:
        cfg = obtener_configuracion()
        insertar_usuario(Usuario(
            nombre="Admin",
            rol="admin",
            clave_hash=cfg.clave_inventario,
        ))
        log.info("Usuario Admin creado con la contraseña existente")


def _instalar_manejador_excepciones() -> None:
    """Captura excepciones no manejadas y las escribe en errors.log antes de mostrarlas."""
    _orig = sys.excepthook

    def _manejador(tipo, valor, tb):
        log.critical("Excepción no capturada", exc_info=(tipo, valor, tb))
        _orig(tipo, valor, tb)

    sys.excepthook = _manejador


def main() -> None:
    """Punto de entrada principal."""
    _instalar_manejador_excepciones()
    log.info("=" * 60)
    log.info("YJBMOTOCOM v2.0 — iniciando")

    # Qt6 habilita DPI scaling automáticamente — no se necesitan atributos manuales.
    # Compatible con Windows 10 y Windows 11.
    app = QApplication(sys.argv)
    app.setApplicationName("YJBMOTOCOM")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("YJBMOTOCOM")

    # Estilo Fusion como base + hoja de estilos global del sistema de diseño
    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_STYLESHEET)

    # Icono de la ventana / taskbar
    # Busca icon.ico → icon.png → cualquier PNG/JPG en assets/ (fallback)
    from PySide6.QtGui import QIcon
    _assets_dir = _BASE_DIR / "assets"
    _icon_file = None
    for _n in ("icon.ico", "icon.png"):
        if (_assets_dir / _n).exists():
            _icon_file = _assets_dir / _n
            break
    if _icon_file is None and _assets_dir.exists():
        _icon_file = next(
            (p for p in sorted(_assets_dir.glob("*.png")) + sorted(_assets_dir.glob("*.ico"))
             if p.is_file()),
            None,
        )
    if _icon_file:
        app.setWindowIcon(QIcon(str(_icon_file)))

    # Inicializar base de datos antes de mostrar la ventana
    initialize_schema()

    # Migrar contraseña plain-text → SHA-256 si viene de versión anterior
    _migrar_clave_a_hash()

    # Aplicar tema guardado (puede ser oscuro desde sesión anterior)
    from database.config_repo import obtener_configuracion as _get_cfg
    from ui.styles import aplicar_tema
    aplicar_tema(_get_cfg().modo_oscuro)

    # Crear usuario Admin si la tabla está vacía (primera vez con multi-usuario)
    _sembrar_admin_si_vacio()

    # Backup automático al arrancar (guarda hasta 7 copias en backups/)
    hacer_backup()

    # Login multi-usuario
    from ui.login_dialog import LoginDialog
    login = LoginDialog()
    if login.exec() != LoginDialog.Accepted:
        sys.exit(0)

    window = MainWindow(usuario=login.usuario_nombre, rol=login.usuario_rol)
    window.showMaximized()

    # Cerrar BD limpiamente al salir
    app.aboutToQuit.connect(DatabaseConnection.close)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
