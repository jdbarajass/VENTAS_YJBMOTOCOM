"""
ui/busqueda_widget.py
Campo de búsqueda global para el sidebar.
Busca en tiempo real sobre ventas, facturas e inventario.
Emite resultado_seleccionado(page_idx) para que MainWindow navegue.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLineEdit, QFrame, QLabel,
    QScrollArea, QPushButton, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont


class BusquedaWidget(QWidget):
    """Barra de búsqueda global con resultados desplegables en el sidebar."""

    resultado_seleccionado = Signal(int)   # page_idx de la página destino

    def __init__(self, page_map: dict, parent=None):
        """
        page_map: {"VENTAS": int, "FACTURAS": int, "INVENTARIO": int, ...}
        """
        super().__init__(parent)
        self._page_map = page_map
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)   # debounce 250 ms
        self._timer.timeout.connect(self._ejecutar_busqueda)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 0)
        root.setSpacing(0)

        self._campo = QLineEdit()
        self._campo.setPlaceholderText("🔍  Buscar…")
        self._campo.setFixedHeight(32)
        self._campo.setStyleSheet(
            "QLineEdit {"
            "  background:#334155; color:#F1F5F9;"
            "  border:1px solid #475569; border-radius:6px;"
            "  padding:0 10px; font-size:11px;"
            "}"
            "QLineEdit:focus { border:1px solid #60A5FA; }"
            "QLineEdit::placeholder { color:#64748B; }"
        )
        self._campo.textChanged.connect(self._on_texto_cambiado)
        self._campo.returnPressed.connect(self._ejecutar_busqueda)
        root.addWidget(self._campo)

        # Panel de resultados (oculto por defecto)
        self._panel = QFrame()
        self._panel.setObjectName("panelBusqueda")
        self._panel.setStyleSheet(
            "QFrame#panelBusqueda {"
            "  background:#1E293B; border:1px solid #334155;"
            "  border-top:none; border-radius:0 0 6px 6px;"
            "}"
        )
        self._panel.setVisible(False)
        panel_lay = QVBoxLayout(self._panel)
        panel_lay.setContentsMargins(0, 4, 0, 4)
        panel_lay.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setStyleSheet("background:transparent;")
        self._scroll.setMaximumHeight(280)

        self._contenedor = QWidget()
        self._contenedor.setStyleSheet("background:transparent;")
        self._lista_lay = QVBoxLayout(self._contenedor)
        self._lista_lay.setContentsMargins(0, 0, 0, 0)
        self._lista_lay.setSpacing(0)

        self._scroll.setWidget(self._contenedor)
        panel_lay.addWidget(self._scroll)

        root.addWidget(self._panel)

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------

    def _on_texto_cambiado(self, texto: str) -> None:
        if len(texto.strip()) < 2:
            self._panel.setVisible(False)
            return
        self._timer.start()

    def _ejecutar_busqueda(self) -> None:
        texto = self._campo.text().strip()
        if len(texto) < 2:
            self._panel.setVisible(False)
            return

        resultados = self._buscar(texto)
        self._mostrar_resultados(resultados)

    def _buscar(self, texto: str) -> list[tuple[str, str, str, int]]:
        """Retorna lista de (categoria, titulo, subtitulo, page_idx)."""
        q = texto.lower()
        resultados = []

        # ── Inventario ────────────────────────────────────────────────
        try:
            from database.inventario_repo import obtener_todos_productos
            for p in obtener_todos_productos():
                if q in p.producto.lower() or q in (p.serial or "").lower() \
                        or q in (p.codigo_barras or "").lower():
                    sub = f"Stock: {p.cantidad} ud.  •  ${p.costo_unitario:,.0f}"
                    resultados.append(("Inventario", p.producto, sub,
                                       self._page_map["INVENTARIO"]))
                    if len(resultados) >= 5:
                        break
        except Exception:
            pass

        # ── Facturas ──────────────────────────────────────────────────
        try:
            from database.facturas_repo import obtener_todas_facturas
            for f in obtener_todas_facturas():
                if q in f.descripcion.lower() or q in f.proveedor.lower():
                    sub = f"{f.proveedor}  •  ${f.monto:,.0f}  •  {f.estado}"
                    resultados.append(("Facturas", f.descripcion, sub,
                                       self._page_map["FACTURAS"]))
                    if len([r for r in resultados if r[0] == "Facturas"]) >= 4:
                        break
        except Exception:
            pass

        # ── Ventas (historial) ────────────────────────────────────────
        try:
            from database.ventas_repo import obtener_todas_las_ventas
            encontradas = 0
            for v in obtener_todas_las_ventas():
                if q in v.producto.lower():
                    sub = f"{v.fecha}  •  ${v.precio:,.0f}  •  {v.metodo_pago}"
                    resultados.append(("Ventas", v.producto, sub,
                                       self._page_map["HISTORIAL"]))
                    encontradas += 1
                    if encontradas >= 4:
                        break
        except Exception:
            pass

        return resultados

    def _mostrar_resultados(self, resultados: list) -> None:
        # Limpiar
        while self._lista_lay.count():
            item = self._lista_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not resultados:
            lbl = QLabel("  Sin resultados")
            lbl.setStyleSheet("color:#64748B; font-size:11px; padding:8px;")
            self._lista_lay.addWidget(lbl)
        else:
            categoria_actual = None
            for categoria, titulo, subtitulo, page_idx in resultados:
                if categoria != categoria_actual:
                    categoria_actual = categoria
                    lbl_cat = QLabel(f"  {categoria.upper()}")
                    lbl_cat.setStyleSheet(
                        "color:#60A5FA; font-size:9px; font-weight:bold;"
                        "letter-spacing:0.5px; padding:6px 10px 2px 10px;"
                        "background:transparent;"
                    )
                    self._lista_lay.addWidget(lbl_cat)

                btn = self._crear_fila_resultado(titulo, subtitulo, page_idx)
                self._lista_lay.addWidget(btn)

        self._panel.setVisible(True)

    def _crear_fila_resultado(self, titulo: str, subtitulo: str, page_idx: int) -> QWidget:
        btn = QPushButton()
        btn.setFlat(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; text-align:left;"
            "  padding:4px 10px; }"
            "QPushButton:hover { background:#334155; }"
        )

        inner = QVBoxLayout(btn)
        inner.setContentsMargins(0, 2, 0, 2)
        inner.setSpacing(0)

        lbl_t = QLabel(titulo[:45] + ("…" if len(titulo) > 45 else ""))
        lbl_t.setStyleSheet("color:#F1F5F9; font-size:11px; background:transparent;")
        lbl_s = QLabel(subtitulo[:50] + ("…" if len(subtitulo) > 50 else ""))
        lbl_s.setStyleSheet("color:#94A3B8; font-size:9px; background:transparent;")

        inner.addWidget(lbl_t)
        inner.addWidget(lbl_s)

        btn.clicked.connect(lambda: self._on_seleccionar(page_idx))
        return btn

    def _on_seleccionar(self, page_idx: int) -> None:
        self._campo.clear()
        self._panel.setVisible(False)
        self.resultado_seleccionado.emit(page_idx)

    def cerrar_resultados(self) -> None:
        self._panel.setVisible(False)
