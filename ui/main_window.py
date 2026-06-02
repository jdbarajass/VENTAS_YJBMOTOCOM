"""
ui/main_window.py
Ventana principal de YJBMOTOCOM.
Estructura: Sidebar de navegación (izquierda) + QStackedWidget (contenido).
Sin lógica de negocio.
"""

from datetime import date as _date

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStatusBar, QPushButton, QStackedWidget, QFrame,
    QInputDialog, QLineEdit, QMessageBox,
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QFont, QPixmap

from ui.busqueda_widget import BusquedaWidget
from ui.calculadora_panel import CalculadoraPanel
from ui.venta_form import VentaForm
from ui.ventas_dia_panel import VentasDiaPanel
from ui.dashboard_panel import DashboardPanel
from ui.historial_panel import HistorialPanel
from ui.config_panel import ConfigPanel
from ui.prestamos_panel import PrestamosPanel
from ui.inventario_panel import InventarioPanel
from ui.exportar_importar_panel import ExportarImportarPanel
from ui.facturas_panel import FacturasPanel
from ui.presupuesto_panel import PresupuestoPanel
from ui.notas_panel import NotasPanel


# Índices de página en el QStackedWidget
PAGE_REGISTRAR    = 0
PAGE_CALCULADORA  = 1
PAGE_VENTAS_DIA   = 2
PAGE_DASHBOARD    = 3
PAGE_HISTORIAL    = 4
PAGE_CONFIG       = 5
PAGE_PRESTAMOS    = 6
PAGE_INVENTARIO   = 7
PAGE_EXPORTAR     = 8
PAGE_FACTURAS     = 9
PAGE_PRESUPUESTO  = 10
PAGE_NOTAS        = 11


class MainWindow(QMainWindow):
    """Shell principal con sidebar + stacked content."""

    APP_TITLE = "YJBMOTOCOM — Control de Rentabilidad"
    MIN_SIZE = QSize(1100, 700)

    def __init__(self, usuario: str = "Admin", rol: str = "admin") -> None:
        super().__init__()
        self._usuario = usuario
        self._rol = rol
        from database.config_repo import obtener_configuracion
        self._timeout_minutos = obtener_configuracion().timeout_minutos
        self._paginas_desbloqueadas: set[int] = set()   # páginas ya autenticadas esta sesión
        # Admin ya tiene acceso a sus propias páginas protegidas desde login
        if rol == "admin":
            self._paginas_desbloqueadas.update({PAGE_CONFIG, PAGE_EXPORTAR})
        self._setup_window()
        self._build_ui()
        self._nav_buttons[PAGE_REGISTRAR].setChecked(True)
        self._actualizar_badge_stock()
        self._actualizar_badge_facturas()
        self._actualizar_badge_notas()
        self._iniciar_timeout_sesion()
        # Verificar facturas vencidas 800ms después de mostrar la ventana
        QTimer.singleShot(800, self._alertar_facturas_vencimiento)

    # ------------------------------------------------------------------
    # Configuración de ventana
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        self.setWindowTitle(self.APP_TITLE)
        self.setMinimumSize(self.MIN_SIZE)
        self.resize(1280, 800)
        self._status = QStatusBar()
        self._status.showMessage("YJBMOTOCOM v2.0  •  Sistema listo")
        self.setStatusBar(self._status)

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content())

        self.setCentralWidget(central)

    # ------------------------------------------------------------------
    # Sidebar
    # ------------------------------------------------------------------

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(210)
        sidebar.setStyleSheet("background-color: #1E293B;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(2)

        # Logo / nombre — busca cualquier PNG/JPG en assets/, si no muestra texto
        import sys
        from pathlib import Path as _Path
        _base = _Path(getattr(sys, "_MEIPASS", _Path(__file__).parent.parent))
        _assets = _base / "assets"
        _logo_path = None
        if _assets.exists():
            for _n in ("logo.png", "logo.jpg", "logo.jpeg"):
                if (_assets / _n).exists():
                    _logo_path = _assets / _n
                    break
            if _logo_path is None:
                _candidates = sorted(_assets.glob("*.png")) + sorted(_assets.glob("*.jpg"))
                _logo_path = next((p for p in _candidates if p.stem != "icon"), None)
        if _logo_path:
            logo = QLabel()
            logo.setAlignment(Qt.AlignCenter)
            logo.setContentsMargins(10, 16, 10, 4)
            _pix = QPixmap(str(_logo_path)).scaledToWidth(
                180, Qt.SmoothTransformation
            )
            logo.setPixmap(_pix)
            logo.setStyleSheet("background:transparent;")
        else:
            logo = QLabel("YJBMOTOCOM")
            logo.setAlignment(Qt.AlignCenter)
            logo.setContentsMargins(0, 24, 0, 8)
            font_logo = QFont()
            font_logo.setPointSize(13)
            font_logo.setBold(True)
            logo.setFont(font_logo)
            logo.setStyleSheet("color: #F8FAFC; letter-spacing: 1px;")
        layout.addWidget(logo)

        sub = QLabel("Control de Rentabilidad")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #94A3B8; font-size: 10px;")
        layout.addWidget(sub)

        # Fecha actual
        hoy = _date.today()
        DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        MESES_ES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
                    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        fecha_str = f"{DIAS_ES[hoy.weekday()]}  {hoy.day} {MESES_ES[hoy.month]} {hoy.year}"
        lbl_fecha = QLabel(fecha_str)
        lbl_fecha.setAlignment(Qt.AlignCenter)
        lbl_fecha.setStyleSheet(
            "color: #64748B; font-size: 11px; margin-top: 6px;"
        )
        layout.addWidget(lbl_fecha)

        layout.addSpacing(12)

        # Búsqueda global
        self._busqueda = BusquedaWidget({
            "INVENTARIO": PAGE_INVENTARIO,
            "FACTURAS":   PAGE_FACTURAS,
            "HISTORIAL":  PAGE_HISTORIAL,
        })
        self._busqueda.resultado_seleccionado.connect(self._navegar)
        layout.addWidget(self._busqueda)

        layout.addSpacing(8)
        layout.addWidget(self._separador_sidebar())
        layout.addSpacing(8)

        # Botones de navegación
        nav_items = [
            (PAGE_REGISTRAR,  "＋  Registrar Venta"),
            (PAGE_CALCULADORA, "🧮  Calculadora"),
            (PAGE_VENTAS_DIA, "📋  Ventas del Día"),
            (PAGE_DASHBOARD,  "📊  Dashboard"),
            (PAGE_HISTORIAL,  "📅  Historial Mensual"),
            (PAGE_INVENTARIO, "📦  Inventario"),
            (PAGE_PRESTAMOS,  "🤝  Préstamos"),
            (PAGE_FACTURAS,    "🧾  Facturas"),
            (PAGE_PRESUPUESTO, "💰  Presupuesto"),
            (PAGE_NOTAS,      "📝  Notas y Pendientes"),
            (PAGE_EXPORTAR,   "⬇⬆  Exportar / Importar"),
            (PAGE_CONFIG,     "⚙  Configuración"),
        ]

        # Páginas ocultas para vendedor
        _ocultas_vendedor = {PAGE_CONFIG, PAGE_EXPORTAR}

        self._nav_buttons: dict[int, QPushButton] = {}
        for page_idx, label in nav_items:
            btn = self._crear_nav_btn(label, page_idx)
            self._nav_buttons[page_idx] = btn
            if self._rol == "vendedor" and page_idx in _ocultas_vendedor:
                btn.setVisible(False)
            layout.addWidget(btn)

        layout.addStretch()

        # Usuario activo
        lbl_usuario = QLabel(f"{'👑' if self._rol == 'admin' else '👤'}  {self._usuario}")
        lbl_usuario.setAlignment(Qt.AlignCenter)
        lbl_usuario.setStyleSheet("color:#94A3B8; font-size:11px; padding:4px 0;")
        layout.addWidget(lbl_usuario)

        # Botón cerrar sesión
        btn_logout = QPushButton("↩  Cerrar sesión")
        btn_logout.setFixedHeight(34)
        btn_logout.setStyleSheet(
            "QPushButton { background:transparent; color:#64748B; border:none;"
            "font-size:11px; text-align:left; padding-left:20px; }"
            "QPushButton:hover { color:#F87171; }"
        )
        btn_logout.clicked.connect(self._on_cerrar_sesion)
        layout.addWidget(btn_logout)

        # Versión al pie
        version = QLabel("v2.0")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #475569; font-size: 10px;")
        layout.addWidget(version)

        return sidebar

    def _crear_nav_btn(self, label: str, page_idx: int) -> QPushButton:
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setFixedHeight(42)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #CBD5E1;
                border: none;
                text-align: left;
                padding-left: 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #F8FAFC;
            }
            QPushButton:checked {
                background-color: #2563EB;
                color: #FFFFFF;
                font-weight: bold;
            }
        """)
        btn.clicked.connect(lambda checked, idx=page_idx: self._navegar(idx))
        return btn

    def _separador_sidebar(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #334155;")
        return sep

    # ------------------------------------------------------------------
    # Área de contenido (stacked)
    # ------------------------------------------------------------------

    def _build_content(self) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stack = QStackedWidget()

        # Página 0 — Registrar Venta
        self._form_venta = VentaForm()
        self._stack.addWidget(self._form_venta)

        # Página 1 — Calculadora de Precios
        self._calculadora = CalculadoraPanel()
        self._stack.addWidget(self._calculadora)

        # Página 2 — Ventas del Día
        self._ventas_dia = VentasDiaPanel()
        self._stack.addWidget(self._ventas_dia)

        # Página 3 — Dashboard Diario
        self._dashboard = DashboardPanel()
        self._stack.addWidget(self._dashboard)

        # Página 4 — Historial Mensual
        self._historial = HistorialPanel()
        self._stack.addWidget(self._historial)

        # Página 5 — Configuración
        self._config = ConfigPanel()
        self._stack.addWidget(self._config)

        # Página 6 — Préstamos
        self._prestamos = PrestamosPanel()
        self._stack.addWidget(self._prestamos)

        # Página 7 — Inventario
        self._inventario = InventarioPanel()
        self._stack.addWidget(self._inventario)

        # Página 8 — Exportar / Importar
        self._exportar_importar = ExportarImportarPanel()
        self._stack.addWidget(self._exportar_importar)

        # Página 9 — Facturas y Recibos
        self._facturas = FacturasPanel()
        self._stack.addWidget(self._facturas)

        # Página 10 — Presupuesto Mensual
        self._presupuesto = PresupuestoPanel()
        self._stack.addWidget(self._presupuesto)

        # Página 11 — Notas y Pendientes
        self._notas = NotasPanel()
        self._stack.addWidget(self._notas)

        # Señales
        self._form_venta.venta_guardada.connect(self._on_venta_guardada)
        self._config.configuracion_guardada.connect(self._on_config_guardada)
        self._historial.venta_modificada.connect(self._on_venta_modificada_en_historial)
        self._inventario.inventario_actualizado.connect(self._form_venta.actualizar_inventario)
        self._inventario.inventario_actualizado.connect(self._actualizar_badge_stock)
        self._exportar_importar.datos_importados.connect(self._on_datos_importados)
        self._facturas._panel_cargue.inventario_actualizado.connect(self._inventario.refresh)
        self._facturas._panel_cargue.inventario_actualizado.connect(self._form_venta.actualizar_inventario)
        self._facturas._panel_cargue.inventario_actualizado.connect(self._actualizar_badge_stock)
        # Cuando cambian gastos operativos → refrescar dashboard e historial automáticamente
        self._ventas_dia.gastos_actualizados.connect(self._dashboard.refresh)
        self._ventas_dia.gastos_actualizados.connect(self._historial.refresh)

        layout.addWidget(self._stack)
        return wrapper

    def _placeholder(self, titulo: str, fase: str) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setAlignment(Qt.AlignCenter)
        lbl = QLabel(f"{titulo}\n({fase} — próximamente)")
        lbl.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(14)
        lbl.setFont(f)
        lbl.setStyleSheet("color: #94A3B8;")
        v.addWidget(lbl)
        return w

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------

    def _navegar(self, page_idx: int) -> None:
        """Cambia la página visible; pide contraseña para Configuración y Exportar/Importar."""
        _PAGINAS_PROTEGIDAS = {PAGE_CONFIG, PAGE_EXPORTAR}
        if page_idx in _PAGINAS_PROTEGIDAS and page_idx not in self._paginas_desbloqueadas:
            from database.config_repo import obtener_configuracion
            from utils.security import verificar_clave
            clave_guardada = obtener_configuracion().clave_inventario
            clave, ok = QInputDialog.getText(
                self, "Acceso restringido",
                "Ingresa la contraseña para continuar:",
                QLineEdit.Password,
            )
            if not ok or not verificar_clave(clave, clave_guardada):
                if ok:
                    QMessageBox.warning(self, "Acceso denegado", "Contraseña incorrecta.")
                # Restaurar el botón que estaba activo antes
                current = self._stack.currentIndex()
                for idx, btn in self._nav_buttons.items():
                    btn.setChecked(idx == current)
                return
            self._paginas_desbloqueadas.add(page_idx)
            import utils.auditoria as auditoria
            nombre_pagina = "Configuración" if page_idx == PAGE_CONFIG else "Exportar/Importar"
            auditoria.registrar(f"Acceso a {nombre_pagina}")

        self._stack.setCurrentIndex(page_idx)
        for idx, btn in self._nav_buttons.items():
            btn.setChecked(idx == page_idx)

    def set_page(self, page_idx: int) -> None:
        """API pública para cambiar de página desde controllers."""
        self._navegar(page_idx)

    # ------------------------------------------------------------------
    # Acceso a sub-vistas (para inyección en fases posteriores)
    # ------------------------------------------------------------------

    def replace_page(self, page_idx: int, widget: QWidget) -> None:
        """
        Reemplaza un placeholder por la vista real.
        Llamado por las fases 5–8 al completarse.
        """
        old = self._stack.widget(page_idx)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(page_idx, widget)

    def set_status(self, mensaje: str) -> None:
        self._status.showMessage(mensaje)

    # ------------------------------------------------------------------
    # Badge de stock bajo
    # ------------------------------------------------------------------

    def _actualizar_badge_stock(self) -> None:
        """Actualiza el texto del botón Inventario con alerta si hay stock bajo (≤ 2 ud.)."""
        from database.inventario_repo import obtener_todos_productos
        prods = obtener_todos_productos()
        bajo_stock = [p for p in prods if 0 < p.cantidad <= 2]
        btn = self._nav_buttons[PAGE_INVENTARIO]
        if bajo_stock:
            btn.setText(f"📦  Inventario  ⚠{len(bajo_stock)}")
            btn.setToolTip(
                f"{len(bajo_stock)} producto(s) con stock bajo (≤ 2 unidades):\n"
                + "\n".join(f"  • {p.producto}: {p.cantidad} ud." for p in bajo_stock[:10])
            )
        else:
            btn.setText("📦  Inventario")
            btn.setToolTip("")

    def _actualizar_badge_facturas(self) -> None:
        """Actualiza el botón Facturas con alerta si hay facturas próximas a vencer (≤ 7 días)."""
        from database.facturas_repo import obtener_facturas_proximas_a_vencer
        proximas = obtener_facturas_proximas_a_vencer(dias=7)
        btn = self._nav_buttons[PAGE_FACTURAS]
        if proximas:
            btn.setText(f"🧾  Facturas  ⚠{len(proximas)}")
            btn.setToolTip(
                f"{len(proximas)} factura(s) vencen en ≤ 7 días:\n"
                + "\n".join(
                    f"  • {f.descripcion} — vence {f.fecha_vencimiento}"
                    for f in proximas[:8]
                )
            )
        else:
            btn.setText("🧾  Facturas")
            btn.setToolTip("")

    def _actualizar_badge_notas(self) -> None:
        """Actualiza el botón Notas con alerta si hay pendientes vencidas."""
        from database.notas_repo import obtener_notas_vencidas
        vencidas = obtener_notas_vencidas()
        btn = self._nav_buttons[PAGE_NOTAS]
        if vencidas:
            btn.setText(f"📝  Notas y Pendientes  ⚠{len(vencidas)}")
            btn.setToolTip(
                f"{len(vencidas)} nota(s) con fecha límite vencida:\n"
                + "\n".join(f"  • {n.texto[:40]}" for n in vencidas[:6])
            )
        else:
            btn.setText("📝  Notas y Pendientes")
            btn.setToolTip("")

    def _alertar_facturas_vencimiento(self) -> None:
        """Muestra un aviso al arrancar si hay facturas con vencimiento inminente."""
        from database.facturas_repo import obtener_facturas_proximas_a_vencer
        from datetime import date as _date
        proximas = obtener_facturas_proximas_a_vencer(dias=7)
        if not proximas:
            return
        hoy = _date.today()
        lineas = []
        for f in proximas[:10]:
            dias_restantes = (f.fecha_vencimiento - hoy).days if f.fecha_vencimiento else 0
            if dias_restantes < 0:
                estado_txt = "VENCIDA"
            elif dias_restantes == 0:
                estado_txt = "vence HOY"
            else:
                estado_txt = f"vence en {dias_restantes} día(s)"
            lineas.append(f"  • {f.descripcion} ({f.proveedor}) — {estado_txt}")
        QMessageBox.warning(
            self,
            "Facturas próximas a vencer",
            f"Tienes {len(proximas)} factura(s) pendientes con vencimiento próximo:\n\n"
            + "\n".join(lineas)
            + "\n\nRevisa el panel de Facturas para gestionarlas.",
        )

    # ------------------------------------------------------------------
    # Callbacks de señales
    # ------------------------------------------------------------------

    def _on_cerrar_sesion(self) -> None:
        """Cierra la sesión actual y muestra el login para el siguiente usuario."""
        import utils.auditoria as auditoria
        auditoria.registrar("Cierre de sesión")
        from ui.login_dialog import LoginDialog
        login = LoginDialog(self)
        if login.exec() == LoginDialog.Accepted:
            self._usuario = login.usuario_nombre
            self._rol = login.usuario_rol
            self._paginas_desbloqueadas.clear()
            if self._rol == "admin":
                self._paginas_desbloqueadas.update({PAGE_CONFIG, PAGE_EXPORTAR})
            # Actualizar visibilidad de botones
            _ocultas_vendedor = {PAGE_CONFIG, PAGE_EXPORTAR}
            for idx, btn in self._nav_buttons.items():
                btn.setVisible(not (self._rol == "vendedor" and idx in _ocultas_vendedor))
            self._navegar(PAGE_REGISTRAR)
            self._status.showMessage(f"Sesión iniciada como {self._usuario}")
        else:
            import sys
            sys.exit(0)

    def _on_venta_guardada(self, venta) -> None:
        """Refresca todas las vistas al registrar una venta."""
        self._ventas_dia.refresh()
        self._dashboard.refresh()
        self._historial.refresh()
        self._inventario.refresh()
        self._actualizar_badge_stock()
        self._status.showMessage(
            f"Venta registrada: {venta.producto}  •  Ganancia neta: {venta.ganancia_neta:,.0f}"
        )

    def _on_config_guardada(self) -> None:
        """Al guardar config, recalcula dashboards e historial y actualiza el timeout."""
        self._dashboard.refresh()
        self._historial.refresh()
        self._presupuesto.refresh()
        from database.config_repo import obtener_configuracion
        self._timeout_minutos = obtener_configuracion().timeout_minutos
        self._timer_sesion.setInterval(self._timeout_minutos * 60 * 1000)
        self._timer_sesion.start()
        self._status.showMessage(
            "Configuración guardada  •  Cálculos actualizados automáticamente"
        )

    def _on_venta_modificada_en_historial(self) -> None:
        """Al editar o eliminar desde historial, refresca ventas del día y dashboard."""
        self._ventas_dia.refresh()
        self._dashboard.refresh()
        self._actualizar_badge_stock()

    def _on_datos_importados(self) -> None:
        """Al importar desde el panel unificado, refresca todas las vistas."""
        self._ventas_dia.refresh()
        self._dashboard.refresh()
        self._historial.refresh()
        self._inventario.refresh()
        self._facturas.refresh()
        self._config.reload()
        self._form_venta.actualizar_inventario()
        self._actualizar_badge_stock()
        self._actualizar_badge_facturas()
        self._actualizar_badge_notas()
        self._status.showMessage("Importación completada  •  Todos los datos actualizados")

    # ------------------------------------------------------------------
    # Timeout de sesión
    # ------------------------------------------------------------------

    def _iniciar_timeout_sesion(self) -> None:
        """Inicia el timer de inactividad. Al expirar, bloquea las páginas protegidas."""
        self._timer_sesion = QTimer(self)
        self._timer_sesion.setInterval(self._timeout_minutos * 60 * 1000)
        self._timer_sesion.setSingleShot(True)
        self._timer_sesion.timeout.connect(self._bloquear_sesion)
        self._timer_sesion.start()

    def _resetear_timeout(self) -> None:
        """Reinicia el contador de inactividad ante cualquier interacción."""
        if hasattr(self, "_timer_sesion"):
            self._timer_sesion.start()

    def _bloquear_sesion(self) -> None:
        """Bloquea las páginas protegidas y redirige al inicio si es necesario."""
        if not self._paginas_desbloqueadas:
            return
        self._paginas_desbloqueadas.clear()
        pagina_actual = self._stack.currentIndex()
        _PAGINAS_PROTEGIDAS = {PAGE_CONFIG, PAGE_EXPORTAR}
        if pagina_actual in _PAGINAS_PROTEGIDAS:
            self._stack.setCurrentIndex(PAGE_REGISTRAR)
            for idx, btn in self._nav_buttons.items():
                btn.setChecked(idx == PAGE_REGISTRAR)
        self._status.showMessage(
            f"Sesión bloqueada por inactividad ({self._timeout_minutos} min)  •  Vuelve a autenticarte para acceder"
        )

    def mousePressEvent(self, event) -> None:
        self._resetear_timeout()
        if hasattr(self, "_busqueda"):
            self._busqueda.cerrar_resultados()
        super().mousePressEvent(event)

    def keyPressEvent(self, event) -> None:
        self._resetear_timeout()
        super().keyPressEvent(event)
