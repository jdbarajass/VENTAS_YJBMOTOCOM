"""
services/recibo_generator.py
Genera un recibo POS (80 mm ancho) en PDF con altura dinámica.
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
NEGOCIO_REGIMEN = "Regimen: Responsable de IVA"

# ---------------------------------------------------------------------------
# Dimensiones del papel (80 mm ancho, alto dinámico)
# ---------------------------------------------------------------------------
PAGE_W   = 80 * mm
MARGIN_X = 4 * mm
COL_W    = PAGE_W - 2 * MARGIN_X      # ~204 pt de ancho útil

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


def _safe(t: str) -> str:
    """Reemplaza caracteres no-latin1 para ReportLab."""
    return t.encode("latin-1", errors="replace").decode("latin-1")


# ---------------------------------------------------------------------------
# Clase constructora del PDF
# ---------------------------------------------------------------------------

class _Recibo:
    """
    Construye el PDF con altura exactamente igual al contenido.
    Layout por producto (sin columnas apretadas):
      Línea 1: "N. Nombre del producto"       (nombre completo, wrapping)
      Línea 2:          cant × $ precio_unit = $ total   (alineado a la derecha)
    """

    def __init__(self, ventas: list[Venta]) -> None:
        self._ventas = ventas
        self._v0 = ventas[0]   # primera venta: metodo pago, fecha, id de factura

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

        # Cabecera empresa
        av(4 * mm)
        av(LINE_H * 1.4)          # nombre (fuente grande)
        av(LINE_H_SM * 5)         # NIT + dir + tel + email + regimen
        av(2 * mm); av(1); av(2 * mm)   # gap + sep + gap

        # Cliente
        av(LINE_H_SM)
        av(2 * mm); av(1); av(2 * mm)

        # Datos de transacción
        av(LINE_H_SM * 3)         # Factura N, Fecha, Hora
        if v0.pagos_combinados:
            av(LINE_H_SM)         # "Metodo pago: Combinado"
            av(LINE_H_SM * len(v0.pagos_combinados))
        else:
            av(LINE_H_SM)         # metodo pago simple
        av(LINE_H_SM)             # Vendedor
        av(2 * mm); av(1); av(2 * mm)

        # Cabecera tabla
        av(LINE_H)

        # Filas de productos
        for v in self._ventas:
            av(self._altura_fila(v))

        av(1); av(2 * mm)          # sep punteada + gap

        # Totales
        av(LINE_H)                 # Subtotal
        total_com = sum(v.comision for v in self._ventas)
        if total_com > 0:
            av(LINE_H_SM)          # Comision
        av(LINE_H * 1.2)           # TOTAL
        av(2 * mm); av(1); av(2 * mm)

        # Resumen forma de pago + items
        av(LINE_H_SM * 2)
        av(2 * mm); av(1); av(2 * mm)

        # Texto legal
        legal = _safe(
            "Gracias por su compra. Este documento es un comprobante "
            "interno de venta. No reemplaza la factura electronica oficial."
        )
        av(len(simpleSplit(legal, FONT_NORMAL, FONT_SMALL, COL_W)) * LINE_H_SM + 1)
        av(LINE_H)                 # "!Gracias por su compra!"
        av(4 * mm)                 # margen inferior

        return cur[0]

    def _altura_fila(self, v: Venta) -> float:
        """Altura de la fila de un producto (2 líneas: nombre + detalle precio)."""
        nombre = _safe(v.producto)
        lineas = simpleSplit(nombre, FONT_NORMAL, FONT_BODY, COL_W - 6 * mm)
        return max(len(lineas), 1) * LINE_H + LINE_H_SM + 3

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
            c.line(MARGIN_X, y(), PAGE_W - MARGIN_X, y())
            c.setDash(1, 0)
            cur[0] += 1

        def kv(llave: str, valor: str) -> None:
            """Dibuja par clave:valor con llave en negrita y valor alineado a la derecha."""
            c.setFont(FONT_BOLD, FONT_BODY)
            c.drawString(MARGIN_X, y(), _safe(llave))
            c.setFont(FONT_NORMAL, FONT_BODY)
            c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(valor))
            nl(LINE_H_SM)

        v0 = self._v0
        now = datetime.now()

        # ── Cabecera del negocio ───────────────────────────────────────
        nl(4 * mm)
        c.setFont(FONT_BOLD, FONT_TITLE * 1.3)
        c.drawCentredString(PAGE_W / 2, y(), _safe(NEGOCIO_NOMBRE))
        nl(LINE_H * 1.4)

        c.setFont(FONT_NORMAL, FONT_BODY)
        for linea in (NEGOCIO_NIT, NEGOCIO_DIR, NEGOCIO_TEL,
                      NEGOCIO_EMAIL, NEGOCIO_REGIMEN):
            c.drawCentredString(PAGE_W / 2, y(), _safe(linea))
            nl(LINE_H_SM)

        nl(2 * mm); sep(); nl(2 * mm)

        # ── Cliente ────────────────────────────────────────────────────
        c.setFont(FONT_BOLD, FONT_BODY)
        c.drawCentredString(PAGE_W / 2, y(), "Cliente: Consumidor Final")
        nl(LINE_H_SM)
        nl(2 * mm); sep(); nl(2 * mm)

        # ── Datos de la transacción ────────────────────────────────────
        num_factura = getattr(v0, "numero_factura", None) or v0.id
        num = str(num_factura) if num_factura else "---"
        kv("Factura N:", f"#{num}")

        fecha_str = (v0.fecha.strftime("%d/%m/%Y")
                     if hasattr(v0.fecha, "strftime") else str(v0.fecha))
        kv("Fecha:", fecha_str)
        kv("Hora:", now.strftime("%I:%M %p"))

        if v0.pagos_combinados:
            kv("Metodo pago:", "Combinado")
            for p in v0.pagos_combinados:
                c.setFont(FONT_NORMAL, FONT_BODY)
                c.drawString(MARGIN_X + 4 * mm, y(),
                             _safe(f"  {p['metodo']}:"))
                c.drawRightString(PAGE_W - MARGIN_X, y(),
                                  _safe(cop(p["monto"])))
                nl(LINE_H_SM)
        else:
            kv("Metodo pago:", v0.metodo_pago)

        kv("Vendedor:", "YJB Motocom")
        nl(2 * mm); sep(); nl(2 * mm)

        # ── Tabla de productos ─────────────────────────────────────────
        # Cabecera sencilla: "#  Descripcion" | "Total" (sin columnas apretadas)
        c.setFont(FONT_BOLD, FONT_SMALL + 0.5)
        c.drawString(MARGIN_X, y(), "#  Descripcion")
        c.drawRightString(PAGE_W - MARGIN_X, y(), "Total")
        nl(LINE_H)

        for idx, v in enumerate(self._ventas, start=1):
            nombre = _safe(v.producto)
            lineas_nombre = simpleSplit(nombre, FONT_NORMAL, FONT_BODY, COL_W - 6 * mm)

            # Línea 1: número + nombre del producto (puede wrappear)
            c.setFont(FONT_BOLD, FONT_BODY)
            c.drawString(MARGIN_X, y(), f"{idx}.")
            c.setFont(FONT_NORMAL, FONT_BODY)
            base_y = y()
            for i, linea in enumerate(lineas_nombre):
                c.drawString(MARGIN_X + 6 * mm, base_y - i * LINE_H, linea)
            nl(max(len(lineas_nombre), 1) * LINE_H)

            # Línea 2: cant × precio_unit = total  (todo en pequeño, alineado derecha)
            total_linea = v.precio * v.cantidad
            detalle = f"{v.cantidad}u x {cop(v.precio)} = {cop(total_linea)}"
            c.setFont(FONT_NORMAL, FONT_SMALL)
            c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(detalle))
            nl(LINE_H_SM + 3)

        sep("dashed"); nl(2 * mm)

        # ── Totales ────────────────────────────────────────────────────
        subtotal = sum(v.precio * v.cantidad for v in self._ventas)
        total_com = sum(v.comision for v in self._ventas)

        c.setFont(FONT_NORMAL, FONT_BODY)
        c.drawString(MARGIN_X, y(), "Subtotal:")
        c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(cop(subtotal)))
        nl(LINE_H)

        if total_com > 0:
            metodo_com = (v0.metodo_pago.split()[0]
                         if not v0.pagos_combinados else "Comb.")
            c.setFont(FONT_NORMAL, FONT_SMALL)
            c.drawString(MARGIN_X, y(), _safe(f"Comision ({metodo_com}):"))
            c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(cop(total_com)))
            nl(LINE_H_SM)

        c.setFont(FONT_BOLD, FONT_TITLE)
        c.drawString(MARGIN_X, y(), "TOTAL:")
        c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(cop(subtotal)))
        nl(LINE_H * 1.2)

        nl(2 * mm); sep(); nl(2 * mm)

        # ── Resumen ────────────────────────────────────────────────────
        metodo_display = "Combinado" if v0.pagos_combinados else v0.metodo_pago
        total_items = sum(v.cantidad for v in self._ventas)
        c.setFont(FONT_NORMAL, FONT_BODY)
        c.drawString(MARGIN_X, y(), "Forma de pago:")
        c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(metodo_display))
        nl(LINE_H_SM)
        c.drawString(MARGIN_X, y(), "Items:")
        c.drawRightString(PAGE_W - MARGIN_X, y(), str(total_items))
        nl(LINE_H_SM)

        nl(2 * mm); sep(); nl(2 * mm)

        # ── Texto legal y despedida ────────────────────────────────────
        legal = _safe(
            "Gracias por su compra. Este documento es un comprobante "
            "interno de venta. No reemplaza la factura electronica oficial."
        )
        c.setFont(FONT_NORMAL, FONT_SMALL)
        for linea in simpleSplit(legal, FONT_NORMAL, FONT_SMALL, COL_W):
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
    Genera el recibo como PDF temporal.
    Acepta una sola Venta o una lista de Ventas (carrito multi-producto).
    Retorna la ruta absoluta al PDF generado.
    """
    if isinstance(ventas, Venta):
        ventas = [ventas]
    return _Recibo(list(ventas)).generar()
