"""
services/recibo_generator.py
Genera un comprobante de venta POS (80 mm ancho) en PDF con altura dinámica.
Acepta una sola Venta o una lista (carrito multi-producto).

Dependencia: reportlab
"""

import os
import tempfile
from datetime import datetime

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

from models.venta import Venta
from utils.formatters import cop

# ---------------------------------------------------------------------------
# Datos del negocio
# ---------------------------------------------------------------------------
NEGOCIO_NOMBRE  = "YJB MOTOCOM"
NEGOCIO_NIT     = "NIT 1032464724-2"
NEGOCIO_DIR     = "AK 14 # 17-21 LOCAL 127, Bogota D.C."
NEGOCIO_TEL     = "Tel: +57 314 406 5520"
NEGOCIO_EMAIL   = "yjbmotocom@gmail.com"
NEGOCIO_REGIMEN = "No responsable de IVA"

# ---------------------------------------------------------------------------
# Dimensiones del papel (80 mm ancho, alto dinámico)
# ---------------------------------------------------------------------------
PAGE_W   = 80 * mm
MARGIN_X = 4 * mm
MARGIN_R = 8 * mm   # margen derecho mayor: cabezal térmico no imprime hasta el borde
COL_W    = PAGE_W - MARGIN_X - MARGIN_R   # ~193 pt de ancho útil (≈68mm)

# ---------------------------------------------------------------------------
# Tipografía
# ---------------------------------------------------------------------------
FONT_BOLD   = "Helvetica-Bold"
FONT_NORMAL = "Helvetica"
FONT_TITLE  = 10
FONT_BODY   = 7.5
FONT_SMALL  = 6.5
LINE_H      = 9.5    # interlineado normal (pt)
LINE_H_SM   = 8.5    # interlineado pequeño

# ---------------------------------------------------------------------------
# Escudo vectorial
# ---------------------------------------------------------------------------
ESCUDO_W = 11 * mm          # ancho del escudo (pequeño, lado izquierdo)
ESCUDO_H = ESCUDO_W * 1.38  # alto del escudo (proporción heráldica)

# Texto de garantía y políticas (sin tildes para latin-1)
_GARANTIA = (
    "Para cambios o garantias, presenta este comprobante. "
    "Plazo maximo: 30 dias calendario. Aplican condiciones."
)
_LEGAL = (
    "Este documento es un comprobante interno de venta. "
    "No reemplaza la factura electronica oficial."
)


def _safe(t: str) -> str:
    """Reemplaza caracteres no-latin1 para ReportLab."""
    return t.encode("latin-1", errors="replace").decode("latin-1")


def _dibujar_escudo(c, cx: float, y_top: float) -> None:
    """
    Dibuja el escudo vectorial YJB MOTOCOM centrado en cx, con borde superior en y_top.
    Solo contorno (sin relleno), con YJB y MOTOCOM dentro.
    """
    W = ESCUDO_W
    H = ESCUDO_H
    x0 = cx - W / 2

    # Fracción donde la parte rectangular termina y empieza la punta inferior
    split = 0.52

    # ── Contorno del escudo ──────────────────────────────────────────────
    p = c.beginPath()
    p.moveTo(x0, y_top)                              # esquina sup-izq
    p.lineTo(x0 + W, y_top)                          # borde superior
    p.lineTo(x0 + W, y_top - H * split)              # lado derecho recto
    p.curveTo(                                        # curva der → punta
        x0 + W,         y_top - H * 0.83,
        cx + W * 0.05,  y_top - H,
        cx,             y_top - H,
    )
    p.curveTo(                                        # curva punta → lado izq
        cx - W * 0.05,  y_top - H,
        x0,             y_top - H * 0.83,
        x0,             y_top - H * split,
    )
    p.lineTo(x0, y_top)                              # lado izquierdo recto
    p.close()

    c.setStrokeColorRGB(0.08, 0.08, 0.10)
    c.setLineWidth(1.1)
    c.drawPath(p, stroke=1, fill=0)

    # ── "YJB" ────────────────────────────────────────────────────────────
    c.setFillColorRGB(0.05, 0.05, 0.05)
    c.setFont(FONT_BOLD, W * 0.315)
    c.drawCentredString(cx, y_top - H * 0.355, "YJB")

    # ── Línea divisoria interior ─────────────────────────────────────────
    c.setStrokeColorRGB(0.18, 0.18, 0.18)
    c.setLineWidth(0.35)
    c.line(x0 + W * 0.14, y_top - H * 0.50,
           x0 + W * 0.86, y_top - H * 0.50)

    # ── "MOTOCOM" ────────────────────────────────────────────────────────
    c.setFont(FONT_BOLD, W * 0.158)
    c.setFillColorRGB(0.05, 0.05, 0.05)
    c.drawCentredString(cx, y_top - H * 0.655, "MOTOCOM")


# ---------------------------------------------------------------------------
# Clase constructora del PDF
# ---------------------------------------------------------------------------

class _Recibo:
    """
    Construye el PDF con altura exactamente igual al contenido.
    Layout por producto (sin columnas apretadas):
      Línea 1: "N. Nombre del producto"       (nombre completo, wrapping)
      Línea 2:  [SKU: XXXXX]                  (si hay sku, pequeño)
      Línea 3:          cant × $ precio_unit = $ total   (alineado a la derecha)
    """

    def __init__(self, ventas: list[Venta]) -> None:
        self._ventas = ventas
        self._v0 = ventas[0]   # primera venta: metodo pago, fecha, datos globales del carrito

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def generar(self) -> str:
        altura = self._calcular_altura()
        fd, path = tempfile.mkstemp(suffix=".pdf", prefix="recibo_")
        os.close(fd)
        c = canvas.Canvas(path, pagesize=(PAGE_W, altura))
        self._dibujar(c, altura)
        c.save()
        return path

    # ------------------------------------------------------------------
    # Cálculo de altura (debe coincidir EXACTAMENTE con _dibujar)
    # ------------------------------------------------------------------

    def _calcular_altura(self) -> float:
        cur = [0.0]

        def av(n: float) -> None:
            cur[0] += n

        v0 = self._v0

        # ── Cabecera empresa ─────────────────────────────────────────────
        av(4 * mm)
        av(LINE_H * 1.4)                              # título YJBMOTOCOM
        av(2 * mm)                                    # gap
        av(max(ESCUDO_H, LINE_H_SM * 4) + 3 * mm)    # escudo izq + info centrada (4 líneas)
        av(2 * mm); av(1); av(2 * mm)                 # gap + sep + gap

        # ── Régimen IVA + Cliente ────────────────────────────────────────
        av(LINE_H_SM)   # "No responsable de IVA..."
        if getattr(v0, "cliente_nombre", ""):
            av(LINE_H_SM)   # nombre
            if getattr(v0, "cliente_cedula", ""):
                av(LINE_H_SM)
            if getattr(v0, "cliente_tel", ""):
                av(LINE_H_SM)
        else:
            av(LINE_H_SM)   # "Cliente: Consumidor Final"
        av(2 * mm); av(1); av(2 * mm)

        # ── Datos de la transacción ──────────────────────────────────────
        av(LINE_H_SM * 3)         # Comprobante N°, Fecha, Hora
        if v0.pagos_combinados:
            av(LINE_H_SM)         # "Metodo pago: Combinado"
            av(LINE_H_SM * len(v0.pagos_combinados))
        else:
            av(LINE_H_SM)         # metodo pago simple
        av(LINE_H_SM)             # Vendedor
        av(2 * mm); av(1); av(2 * mm)

        # ── Cabecera tabla ───────────────────────────────────────────────
        av(LINE_H)

        # ── Filas de productos ───────────────────────────────────────────
        for v in self._ventas:
            av(self._altura_fila(v))

        av(1); av(2 * mm)          # sep punteada + gap

        # ── Totales ──────────────────────────────────────────────────────
        av(LINE_H)                 # Subtotal / Precio al cliente
        ahorro = self._ahorro_total()
        desc = getattr(v0, "descuento", 0) or 0
        if ahorro > 0 or desc > 0:
            av(LINE_H_SM)          # Ahorro / Descuento
        total_com = sum(v.comision for v in self._ventas)
        if total_com > 0:
            av(LINE_H_SM)          # Comision
        av(LINE_H * 1.2)           # TOTAL COP
        av(2 * mm); av(1); av(2 * mm)

        # ── Resumen forma de pago + items ────────────────────────────────
        av(LINE_H_SM * 2)

        # ── Observaciones (si hay notas) ─────────────────────────────────
        notas = getattr(v0, "notas", "") or ""
        if notas:
            obs_lines = simpleSplit(_safe(notas), FONT_BOLD, FONT_SMALL, COL_W)
            av(LINE_H_SM)                         # "Observaciones:" label
            av(len(obs_lines) * LINE_H_SM)

        av(2 * mm); av(1); av(2 * mm)

        # ── Texto garantía ───────────────────────────────────────────────
        av(len(simpleSplit(_safe(_GARANTIA), FONT_BOLD, FONT_SMALL, COL_W)) * LINE_H_SM + 1)

        # ── Texto legal ──────────────────────────────────────────────────
        av(len(simpleSplit(_safe(_LEGAL), FONT_BOLD, FONT_SMALL, COL_W)) * LINE_H_SM + 1)

        av(LINE_H)                 # "!Gracias por su compra!"
        av(4 * mm)                 # margen inferior

        return cur[0]

    def _ahorro_total(self) -> float:
        """Ahorro total del carrito para el modelo por-producto (precio = precio real)."""
        return sum(
            max(0.0, getattr(v, "precio_ofertado", 0.0) - v.precio) * v.cantidad
            for v in self._ventas
        )

    def _altura_fila(self, v: Venta) -> float:
        """Altura de la fila de un producto (nombre + opcional SKU + detalle precio)."""
        _talla = (getattr(v, "talla", "") or "").strip()
        _nombre_display = f"{v.producto}  ·  Talla {_talla}" if _talla and _talla not in ("N/A", "—") else v.producto
        nombre = _safe(_nombre_display)
        lineas = simpleSplit(nombre, FONT_BOLD, FONT_BODY, COL_W - 6 * mm)
        height = max(len(lineas), 1) * LINE_H + LINE_H_SM + 3
        if getattr(v, "sku", ""):
            height += LINE_H_SM
        return height

    # ------------------------------------------------------------------
    # Dibujo real
    # ------------------------------------------------------------------

    def _dibujar(self, c: canvas.Canvas, altura: float) -> None:
        cur = [0.0]

        def y() -> float:
            return altura - cur[0]

        def nl(n: float = LINE_H) -> None:
            cur[0] += n

        def sep(estilo: str = "solid") -> None:
            c.setDash(3, 3) if estilo == "dashed" else c.setDash(1, 0)
            c.setLineWidth(0.4)
            c.line(MARGIN_X, y(), PAGE_W - MARGIN_R, y())
            c.setDash(1, 0)
            cur[0] += 1

        def kv(llave: str, valor: str) -> None:
            """Dibuja par clave:valor ambos en negrita, valor alineado a la derecha."""
            c.setFont(FONT_BOLD, FONT_BODY)
            c.drawString(MARGIN_X, y(), _safe(llave))
            c.drawRightString(PAGE_W - MARGIN_R, y(), _safe(valor))
            nl(LINE_H_SM)

        v0 = self._v0
        # Usar la hora guardada en la venta; fallback a la hora actual (ventas antiguas sin campo)
        hora_venta = getattr(v0, "hora", "") or ""

        # ── Cabecera del negocio ──────────────────────────────────────────
        nl(4 * mm)

        c.setFont(FONT_BOLD, FONT_TITLE * 1.3)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(PAGE_W / 2, y(), "YJBMOTOCOM")
        nl(LINE_H * 1.4)

        nl(2 * mm)

        header_h = max(ESCUDO_H, LINE_H_SM * 4)

        v_off_s = (header_h - ESCUDO_H) / 2
        _dibujar_escudo(c, MARGIN_X + ESCUDO_W / 2, y() - v_off_s)

        area_left  = MARGIN_X + ESCUDO_W + 2 * mm
        area_right = PAGE_W - MARGIN_R
        text_cx    = (area_left + area_right) / 2

        v_off_t = (header_h - LINE_H_SM * 4) / 2
        text_y  = y() - v_off_t - FONT_SMALL * 0.85
        c.setFont(FONT_BOLD, FONT_SMALL)
        c.setFillColorRGB(0, 0, 0)
        for linea in (NEGOCIO_NIT, NEGOCIO_DIR, NEGOCIO_TEL, NEGOCIO_EMAIL):
            c.drawCentredString(text_cx, text_y, _safe(linea))
            text_y -= LINE_H_SM

        nl(header_h + 3 * mm)

        nl(2 * mm); sep(); nl(2 * mm)

        # ── Régimen IVA ───────────────────────────────────────────────────
        c.setFont(FONT_BOLD, FONT_SMALL)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(PAGE_W / 2, y(), _safe(NEGOCIO_REGIMEN))
        nl(LINE_H_SM)

        # ── Cliente ───────────────────────────────────────────────────────
        cli_nombre = getattr(v0, "cliente_nombre", "") or ""
        cli_cedula = getattr(v0, "cliente_cedula", "") or ""
        cli_tel    = getattr(v0, "cliente_tel", "") or ""

        if cli_nombre:
            kv("Cliente:", cli_nombre)
            if cli_cedula:
                kv("Cedula:", cli_cedula)
            if cli_tel:
                kv("Tel.:", cli_tel)
        else:
            c.setFont(FONT_BOLD, FONT_BODY)
            c.drawCentredString(PAGE_W / 2, y(), "Cliente: Consumidor Final")
            nl(LINE_H_SM)

        nl(2 * mm); sep(); nl(2 * mm)

        # ── Datos de la transacción ────────────────────────────────────────
        num_factura = getattr(v0, "numero_factura", None) or v0.id
        num = str(num_factura) if num_factura else "---"
        kv("Comprobante N\xb0:", f"#{num}")

        fecha_str = (v0.fecha.strftime("%d/%m/%Y")
                     if hasattr(v0.fecha, "strftime") else str(v0.fecha))
        kv("Fecha:", fecha_str)
        kv("Hora:", hora_venta if hora_venta else datetime.now().strftime("%I:%M %p"))

        if v0.pagos_combinados:
            kv("Metodo pago:", "Combinado")
            for p in v0.pagos_combinados:
                c.setFont(FONT_NORMAL, FONT_BODY)
                c.drawString(MARGIN_X + 4 * mm, y(),
                             _safe(f"  {p['metodo']}:"))
                c.drawRightString(PAGE_W - MARGIN_R, y(),
                                  _safe(cop(p["monto"])))
                nl(LINE_H_SM)
        else:
            kv("Metodo pago:", v0.metodo_pago)

        vendedor = getattr(v0, "vendedor", "") or "YJB Motocom"
        kv("Vendedor:", vendedor)
        nl(2 * mm); sep(); nl(2 * mm)

        # ── Tabla de productos ─────────────────────────────────────────────
        c.setFont(FONT_BOLD, FONT_SMALL + 0.5)
        c.drawString(MARGIN_X, y(), "#  Descripcion")
        c.drawRightString(PAGE_W - MARGIN_R, y(), "Total")
        nl(LINE_H)

        for idx, v in enumerate(self._ventas, start=1):
            _talla_v = (getattr(v, "talla", "") or "").strip()
            _nombre_v = f"{v.producto}  ·  Talla {_talla_v}" if _talla_v and _talla_v not in ("N/A", "—") else v.producto
            nombre = _safe(_nombre_v)
            lineas_nombre = simpleSplit(nombre, FONT_NORMAL, FONT_BODY, COL_W - 6 * mm)

            # Línea 1: número + nombre del producto (puede wrappear)
            c.setFont(FONT_BOLD, FONT_BODY)
            c.drawString(MARGIN_X, y(), f"{idx}.")
            base_y = y()
            for i, linea in enumerate(lineas_nombre):
                c.drawString(MARGIN_X + 6 * mm, base_y - i * LINE_H, linea)
            nl(max(len(lineas_nombre), 1) * LINE_H)

            # Línea SKU (si existe)
            sku = getattr(v, "sku", "") or ""
            if sku:
                c.setFont(FONT_BOLD, FONT_SMALL)
                c.setFillColorRGB(0, 0, 0)
                c.drawString(MARGIN_X + 6 * mm, y(), _safe(f"SKU: {sku}"))
                nl(LINE_H_SM)

            # Línea 2: cant × precio_unit = total  (precio anunciado si hay descuento)
            _po = getattr(v, "precio_ofertado", 0.0) or 0.0
            precio_mostrar = _po if _po > v.precio else v.precio
            total_linea = precio_mostrar * v.cantidad
            detalle = f"{v.cantidad}u x {cop(precio_mostrar)} = {cop(total_linea)}"
            c.setFont(FONT_BOLD, FONT_SMALL)
            c.drawRightString(PAGE_W - MARGIN_R, y(), _safe(detalle))
            nl(LINE_H_SM + 3)

        sep("dashed"); nl(2 * mm)

        # ── Totales ────────────────────────────────────────────────────────
        subtotal = sum(v.precio * v.cantidad for v in self._ventas)
        ahorro   = self._ahorro_total()
        desc     = getattr(v0, "descuento", 0) or 0
        total_com = sum(v.comision for v in self._ventas)

        c.setFont(FONT_BOLD, FONT_BODY)
        c.setFillColorRGB(0, 0, 0)

        if ahorro > 0:
            # Nuevo modelo: precio = precio real, precio_ofertado = precio anunciado
            precio_anunciado = subtotal + ahorro
            total_final = subtotal
            c.drawString(MARGIN_X, y(), "Subtotal:")
            c.drawRightString(PAGE_W - MARGIN_R, y(), _safe(cop(precio_anunciado)))
            nl(LINE_H)
            pct = ahorro / precio_anunciado * 100 if precio_anunciado > 0 else 0
            c.drawString(MARGIN_X, y(), _safe(f"Descuento ({pct:.0f}%):"))
            c.drawRightString(PAGE_W - MARGIN_R, y(), _safe(f"- {cop(ahorro)}"))
            nl(LINE_H_SM)
        else:
            # Modelo anterior: precio = precio anunciado, descuento = ahorro en pesos
            total_final = subtotal - desc
            c.drawString(MARGIN_X, y(), "Subtotal:")
            c.drawRightString(PAGE_W - MARGIN_R, y(), _safe(cop(subtotal)))
            nl(LINE_H)
            if desc > 0:
                pct = desc / subtotal * 100 if subtotal > 0 else 0
                c.drawString(MARGIN_X, y(), _safe(f"Descuento ({pct:.0f}%):"))
                c.drawRightString(PAGE_W - MARGIN_R, y(), _safe(f"- {cop(desc)}"))
                nl(LINE_H_SM)

        if total_com > 0:
            metodo_com = (v0.metodo_pago.split()[0]
                         if not v0.pagos_combinados else "Comb.")
            c.setFont(FONT_BOLD, FONT_SMALL)
            c.drawString(MARGIN_X, y(), _safe(f"Comision ({metodo_com}):"))
            c.drawRightString(PAGE_W - MARGIN_R, y(), _safe(f"+ {cop(total_com)}"))
            nl(LINE_H_SM)
            total_final += total_com

        c.setFont(FONT_BOLD, FONT_TITLE)
        c.drawString(MARGIN_X, y(), "TOTAL COP:")
        c.drawRightString(PAGE_W - MARGIN_R, y(), _safe(cop(total_final)))
        nl(LINE_H * 1.2)

        nl(2 * mm); sep(); nl(2 * mm)

        # ── Resumen ────────────────────────────────────────────────────────
        metodo_display = "Combinado" if v0.pagos_combinados else v0.metodo_pago
        total_items = sum(v.cantidad for v in self._ventas)
        c.setFont(FONT_BOLD, FONT_BODY)
        c.drawString(MARGIN_X, y(), "Forma de pago:")
        c.drawRightString(PAGE_W - MARGIN_R, y(), _safe(metodo_display))
        nl(LINE_H_SM)
        c.drawString(MARGIN_X, y(), "Items:")
        c.drawRightString(PAGE_W - MARGIN_R, y(), str(total_items))
        nl(LINE_H_SM)

        # ── Observaciones ─────────────────────────────────────────────────
        notas = getattr(v0, "notas", "") or ""
        if notas:
            c.setFont(FONT_BOLD, FONT_SMALL)
            c.drawString(MARGIN_X, y(), "Observaciones:")
            nl(LINE_H_SM)
            c.setFont(FONT_BOLD, FONT_SMALL)
            for linea in simpleSplit(_safe(notas), FONT_BOLD, FONT_SMALL, COL_W):
                c.drawString(MARGIN_X, y(), linea)
                nl(LINE_H_SM)

        nl(2 * mm); sep(); nl(2 * mm)

        # ── Garantía y política de devoluciones ────────────────────────────
        c.setFont(FONT_BOLD, FONT_SMALL)
        c.setFillColorRGB(0, 0, 0)
        for linea in simpleSplit(_safe(_GARANTIA), FONT_BOLD, FONT_SMALL, COL_W):
            c.drawCentredString(PAGE_W / 2, y(), linea)
            nl(LINE_H_SM)
        nl(1)

        # ── Texto legal ────────────────────────────────────────────────────
        for linea in simpleSplit(_safe(_LEGAL), FONT_BOLD, FONT_SMALL, COL_W):
            c.drawCentredString(PAGE_W / 2, y(), linea)
            nl(LINE_H_SM)
        nl(1)

        c.setFont(FONT_BOLD, FONT_BODY)
        c.drawCentredString(PAGE_W / 2, y(), "!Gracias por su compra!")
        nl(LINE_H)


# ---------------------------------------------------------------------------
# Función pública
# ---------------------------------------------------------------------------

def generar_recibo(ventas) -> str:
    """
    Genera el comprobante como PDF temporal.
    Acepta una sola Venta o una lista de Ventas (carrito multi-producto).
    Retorna la ruta absoluta al PDF generado.
    """
    if isinstance(ventas, Venta):
        ventas = [ventas]
    return _Recibo(list(ventas)).generar()
