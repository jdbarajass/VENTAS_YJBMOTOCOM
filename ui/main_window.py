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
    QInputDialog, QLineEdit, QMessageBox, QScrollArea, QApplication,
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
from ui.cuentas_panel import CuentasPanel
from ui.fiado_panel import FiadoPanel
from ui.mi_cuadre_panel import MiCuadrePanel
from ui.rendimiento_vendedores_panel import RendimientoVendedoresPanel


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
PAGE_CUENTAS      = 12
PAGE_FIADO        = 13
PAGE_RESUMEN      = 14
PAGE_RENDIMIENTO  = 15


class MainWindow(QMainWindow):
    """Shell principal con sidebar + stacked content."""

    APP_TITLE = "YJBMOTOCOM — Control de Rentabilidad"
    MIN_SIZE = QSize(780, 520)

    def __init__(self, usuario: str = "Admin", rol: str = "admin") -> None:
        super().__init__()
        self._usuario = usuario
        self._rol = rol
        from database.config_repo import obtener_configuracion
        self._timeout_minutos = obtener_configuracion().timeout_minutos
        self._paginas_desbloqueadas: set[int] = set()   # páginas ya autenticadas esta sesión
        # Admin ya tiene acceso a sus propias páginas protegidas desde login
        if rol == "admin":
            self._paginas_desbloqueadas.update({PAGE_CONFIG, PAGE_EXPORTAR, PAGE_CUENTAS})
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
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #1E293B;")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(2)

        # ── Header / Logo ─────────────────────────────────────────────────
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

        header_frame = QFrame()
        header_frame.setStyleSheet(
            "QFrame { background-color: #162032; border-bottom: 1px solid #2D3F55; }"
        )
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(12, 14, 12, 10)
        h_layout.setSpacing(5)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        if _logo_path:
            lbl_icon = QLabel()
            _icon_size = 52
            lbl_icon.setFixedSize(_icon_size, _icon_size)
            lbl_icon.setAlignment(Qt.AlignCenter)
            _dpr = QApplication.primaryScreen().devicePixelRatio()
            _phys = int(_icon_size * _dpr)
            _pix = QPixmap(str(_logo_path)).scaled(
                _phys, _phys, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            _pix.setDevicePixelRatio(_dpr)
            lbl_icon.setPixmap(_pix)
            lbl_icon.setStyleSheet("background: transparent;")
            top_row.addWidget(lbl_icon)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        lbl_nombre = QLabel("YJBMOTOCOM")
        _fn = QFont()
        _fn.setPointSize(11)
        _fn.setBold(True)
        lbl_nombre.setFont(_fn)
        lbl_nombre.setStyleSheet(
            "color: #F8FAFC; letter-spacing: 1px; background: transparent;"
        )
        info_col.addWidget(lbl_nombre)

        lbl_sub = QLabel("Control de Rentabilidad")
        lbl_sub.setStyleSheet("color: #94A3B8; font-size: 9px; background: transparent;")
        info_col.addWidget(lbl_sub)
        info_col.addStretch()

        top_row.addLayout(info_col)
        top_row.addStretch()
        h_layout.addLayout(top_row)

        hoy = _date.today()
        DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        MESES_ES = ["", "Ene", "Feb", "Mar", "Abr", "May", "Jun",
                    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        fecha_str = f"{DIAS_ES[hoy.weekday()]}  {hoy.day} {MESES_ES[hoy.month]} {hoy.year}"
        lbl_fecha = QLabel(fecha_str)
        lbl_fecha.setAlignment(Qt.AlignRight)
        lbl_fecha.setStyleSheet(
            "color: #64748B; font-size: 10px; background: transparent;"
        )
        h_layout.addWidget(lbl_fecha)

        layout.addWidget(header_frame)

        # ── Sección scrolleable: búsqueda + nav ────────────────────────────
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setFrameShape(QFrame.NoFrame)
        nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        nav_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        nav_scroll.setStyleSheet("background: transparent; border: none;")

        nav_content = QWidget()
        nav_content.setStyleSheet("background: transparent;")
        nav_inner = QVBoxLayout(nav_content)
        nav_inner.setContentsMargins(0, 8, 0, 8)
        nav_inner.setSpacing(2)

        # Búsqueda global
        self._busqueda = BusquedaWidget({
            "INVENTARIO": PAGE_INVENTARIO,
            "FACTURAS":   PAGE_FACTURAS,
            "HISTORIAL":  PAGE_HISTORIAL,
        })
        self._busqueda.resultado_seleccionado.connect(self._navegar)
        nav_inner.addWidget(self._busqueda)

        nav_inner.addSpacing(8)
        nav_inner.addWidget(self._separador_sidebar())
        nav_inner.addSpacing(8)

        # Botones de navegación
        nav_items = [
            (PAGE_REGISTRAR,   "＋  Registrar Venta"),
            (PAGE_CALCULADORA, "🧮  Calculadora"),
            (PAGE_VENTAS_DIA,  "📋  Ventas del Día"),
            (PAGE_RESUMEN,     "💰  Mi Cuadre"),
            (PAGE_DASHBOARD,   "📊  Dashboard"),
            (PAGE_HISTORIAL,   "📅  Historial Mensual"),
            (PAGE_INVENTARIO,  "📦  Inventario"),
            (PAGE_PRESTAMOS,   "🤝  Préstamos"),
            (PAGE_FIADO,       "💸  Clientes Deudores"),
            (PAGE_FACTURAS,    "🧾  Facturas"),
            (PAGE_PRESUPUESTO, "💰  Presupuesto"),
            (PAGE_NOTAS,       "📝  Notas y Pendientes"),
            (PAGE_EXPORTAR,    "⬇⬆  Exportar / Importar"),
            (PAGE_CONFIG,      "⚙  Configuración"),
            (PAGE_CUENTAS,     "💳  Cuentas"),
            (PAGE_RENDIMIENTO, "📈  Rendimiento Vendedores"),
        ]

        _ocultas_vendedor = {PAGE_CONFIG, PAGE_EXPORTAR, PAGE_CUENTAS, PAGE_RENDIMIENTO}

        self._nav_buttons: dict[int, QPushButton] = {}
        for page_idx, label in nav_items:
            btn = self._crear_nav_btn(label, page_idx)
            self._nav_buttons[page_idx] = btn
            if self._rol == "vendedor" and page_idx in _ocultas_vendedor:
                btn.setVisible(False)
            nav_inner.addWidget(btn)

        nav_inner.addStretch()
        nav_scroll.setWidget(nav_content)
        layout.addWidget(nav_scroll, stretch=1)

        # ── Sección fija inferior ───────────────────────────────────────────
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet(
            "QFrame { border-top: 1px solid #2D3F55; background: transparent; }"
        )
        bottom_layout = QVBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 6, 0, 0)
        bottom_layout.setSpacing(0)

        self._lbl_usuario = QLabel(f"{'👑' if self._rol == 'admin' else '👤'}  {self._usuario}")
        self._lbl_usuario.setAlignment(Qt.AlignCenter)
        self._lbl_usuario.setStyleSheet("color:#94A3B8; font-size:11px; padding:4px 0;")
        bottom_layout.addWidget(self._lbl_usuario)

        btn_logout = QPushButton("↩  Cerrar sesión")
        btn_logout.setFixedHeight(34)
        btn_logout.setStyleSheet(
            "QPushButton { background:transparent; color:#64748B; border:none;"
            "font-size:11px; text-align:left; padding-left:20px; }"
            "QPushButton:hover { color:#F87171; }"
        )
        btn_logout.clicked.connect(self._on_cerrar_sesion)
        bottom_layout.addWidget(btn_logout)

        version = QLabel("v2.0")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("color: #475569; font-size: 10px; padding-bottom: 4px;")
        bottom_layout.addWidget(version)

        layout.addWidget(bottom_frame)

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
        self._inventario = InventarioPanel(rol=self._rol)
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

        # Página 12 — Cuentas (solo Admin)
        self._cuentas = CuentasPanel()
        self._stack.addWidget(self._cuentas)

        # Página 13 — Clientes Deudores (Fiado)
        self._fiado = FiadoPanel()
        self._stack.addWidget(self._fiado)

        # Página 14 — Mi Cuadre
        self._mi_cuadre = MiCuadrePanel()
        self._stack.addWidget(self._mi_cuadre)

        # Página 15 — Rendimiento por Vendedor
        self._rendimiento = RendimientoVendedoresPanel()
        self._stack.addWidget(self._rendimiento)

        # Señales
        self._form_venta.venta_guardada.connect(self._on_venta_guardada)
        self._form_venta.venta_guardada.connect(self._mi_cuadre.refresh)
        self._form_venta.venta_guardada.connect(lambda _: self._rendimiento.refresh())
        self._config.configuracion_guardada.connect(self._on_config_guardada)
        self._config.usuarios_cambiados.connect(self._form_venta.recargar_vendedores)
        self._config.usuarios_cambiados.connect(self._rendimiento.refresh)
        self._dashboard.navegar_a.connect(self._navegar)
        self._historial.venta_modificada.connect(self._on_venta_modificada_en_historial)
        self._inventario.inventario_actualizado.connect(self._form_venta.actualizar_inventario)
        self._inventario.inventario_actualizado.connect(self._actualizar_badge_stock)
        self._exportar_importar.datos_importados.connect(self._on_datos_importados)
        self._facturas._panel_cargue.inventario_actualizado.connect(self._inventario.refresh)
        self._facturas._panel_cargue.inventario_actualizado.connect(self._form_venta.actualizar_inventario)
        self._facturas._panel_cargue.inventario_actualizado.connect(self._actualizar_badge_stock)
        # Cuando cambian gastos operativos → refrescar dashboard, historial y presupuesto
        self._ventas_dia.gastos_actualizados.connect(self._dashboard.refresh)
        self._ventas_dia.gastos_actualizados.connect(self._historial.refresh)
        self._ventas_dia.gastos_actualizados.connect(self._presupuesto.refresh)
        self._ventas_dia.gastos_actualizados.connect(self._cuentas.refresh)

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
        """Cambia la página visible; pide contraseña para Configuración, Exportar/Importar y Cuentas."""
        _PAGINAS_PROTEGIDAS = {PAGE_CONFIG, PAGE_EXPORTAR, PAGE_CUENTAS}
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
            nombre_pagina = {PAGE_CONFIG: "Configuración",
                             PAGE_EXPORTAR: "Exportar/Importar",
                             PAGE_CUENTAS: "Cuentas"}.get(page_idx, "Página protegida")
            auditoria.registrar(f"Acceso a {nombre_pagina}")

        self._stack.setCurrentIndex(page_idx)
        for idx, btn in self._nav_buttons.items():
            btn.setChecked(idx == page_idx)
        if page_idx == PAGE_RESUMEN:
            self._mi_cuadre.refresh()
        if page_idx == PAGE_RENDIMIENTO:
            self._rendimiento.refresh()

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
        """Alerta de stock bajo: usa stock_minimo por producto; fallback ≤ 2 si no hay mínimo."""
        from database.inventario_repo import obtener_todos_productos
        prods = obtener_todos_productos()
        bajo_stock = [
            p for p in prods
            if p.stock_minimo > 0 and p.cantidad < p.stock_minimo
            or p.stock_minimo == 0 and 0 < p.cantidad <= 2
        ]
        btn = self._nav_buttons[PAGE_INVENTARIO]
        if bajo_stock:
            btn.setText(f"📦  Inventario  ⚠{len(bajo_stock)}")
            lines = []
            for p in bajo_stock[:10]:
                if p.stock_minimo > 0:
                    lines.append(f"  • {p.producto}: {p.cantidad}/{p.stock_minimo} ud.")
                else:
                    lines.append(f"  • {p.producto}: {p.cantidad} ud.")
            btn.setToolTip(
                f"{len(bajo_stock)} producto(s) con stock bajo:\n" + "\n".join(lines)
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
        """Muestra recordatorios al arrancar: facturas, notas y fiados urgentes."""
        from datetime import date as _date
        hoy = _date.today()
        secciones: list[str] = []

        # 1. Facturas próximas a vencer o vencidas
        try:
            from database.facturas_repo import obtener_facturas_proximas_a_vencer
            proximas = obtener_facturas_proximas_a_vencer(dias=7)
            if proximas:
                lineas_f = []
                for f in proximas[:8]:
                    d = (f.fecha_vencimiento - hoy).days if f.fecha_vencimiento else 0
                    estado = "VENCIDA" if d < 0 else ("hoy" if d == 0 else f"{d}d")
                    lineas_f.append(f"  • {f.descripcion[:40]} — {estado}")
                secciones.append(
                    f"📋 FACTURAS ({len(proximas)} próximas a vencer):\n" + "\n".join(lineas_f)
                )
        except Exception:
            pass

        # 2. Notas con fecha_limite en los próximos 3 días
        try:
            from database.notas_repo import obtener_notas_proximas
            urgentes_notas = obtener_notas_proximas(dias=3)
            if urgentes_notas:
                lineas_n = [
                    f"  • {n.texto[:40]} — {n.fecha_limite}"
                    for n in urgentes_notas[:6]
                ]
                secciones.append(
                    f"📝 NOTAS ({len(urgentes_notas)} con fecha límite próxima):\n"
                    + "\n".join(lineas_n)
                )
        except Exception:
            pass

        # 3. Fiados pendientes con más de 30 días
        try:
            from database.fiado_repo import obtener_fiados_pendientes
            fiados = obtener_fiados_pendientes()
            viejos = [f for f in fiados if f.dias_transcurridos > 30]
            if viejos:
                lineas_fiad = [
                    f"  • {f.cliente_nombre[:30]} — {f.dias_transcurridos}d sin saldar"
                    for f in sorted(viejos, key=lambda x: -x.dias_transcurridos)[:6]
                ]
                secciones.append(
                    f"💸 FIADOS ({len(viejos)} con más de 30 días pendientes):\n"
                    + "\n".join(lineas_fiad)
                )
        except Exception:
            pass

        if not secciones:
            return

        QMessageBox.warning(
            self,
            "Recordatorios — YJBMOTOCOM",
            "Hay elementos que requieren atención:\n\n"
            + "\n\n".join(secciones),
        )

    # ------------------------------------------------------------------
    # Callbacks de señales
    # ------------------------------------------------------------------

    def _on_cerrar_sesion(self) -> None:
        """Cierra la sesión actual y muestra el login para el siguiente usuario."""
        import utils.auditoria as auditoria
        auditoria.registrar("Cierre de sesión")
        from ui.login_dialog import LoginDialog
        self.hide()
        login = LoginDialog()
        if login.exec() == LoginDialog.Accepted:
            self._usuario = login.usuario_nombre
            self._rol = login.usuario_rol
            self._lbl_usuario.setText(f"{'👑' if self._rol == 'admin' else '👤'}  {self._usuario}")
            self._paginas_desbloqueadas.clear()
            if self._rol == "admin":
                self._paginas_desbloqueadas.update({PAGE_CONFIG, PAGE_EXPORTAR, PAGE_CUENTAS})
            # Actualizar inventario según nuevo rol
            self._inventario._rol = self._rol
            self._inventario._edicion_desbloqueada = self._rol == "admin"
            # Actualizar visibilidad de botones
            _ocultas_vendedor = {PAGE_CONFIG, PAGE_EXPORTAR, PAGE_CUENTAS, PAGE_RENDIMIENTO}
            for idx, btn in self._nav_buttons.items():
                btn.setVisible(not (self._rol == "vendedor" and idx in _ocultas_vendedor))
            self.showMaximized()
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
        self._cuentas.refresh()
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
        """Al importar desde el panel unificado, refresca TODAS las vistas."""
        self._ventas_dia.refresh()
        self._dashboard.refresh()
        self._historial.refresh()
        self._inventario.refresh()
        self._facturas.refresh()
        self._prestamos.refresh()     # importación puede traer préstamos nuevos
        self._notas.refresh()         # importación puede traer notas nuevas
        self._presupuesto.refresh()   # importación puede traer presupuesto nuevo
        self._config.reload()
        self._form_venta.actualizar_inventario()
        self._actualizar_badge_stock()
        self._actualizar_badge_facturas()
        self._actualizar_badge_notas()
        self._cuentas.refresh()
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
        _PAGINAS_PROTEGIDAS = {PAGE_CONFIG, PAGE_EXPORTAR, PAGE_CUENTAS}
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
