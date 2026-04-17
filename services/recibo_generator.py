"""
services/recibo_generator.py
Genera un recibo de venta en formato PDF (80 mm de ancho, estilo POS termico).
Basado en el formato Alegra POS: cabecera empresa, datos transaccion, tabla
de producto, totales y pie legal.

Dependencia: reportlab (pip install reportlab)
Uso:
    from services.recibo_generator import generar_recibo
    path = generar_recibo(venta)   # devuelve ruta al PDF temporal
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
# Constantes del negocio
# ---------------------------------------------------------------------------
NEGOCIO_NOMBRE  = "YJB MOTOCOM"
NEGOCIO_NIT     = "NIT 1032464724-2"
NEGOCIO_DIR     = "AK 14 # 17-21 LOCAL 127, Bogota D.C."
NEGOCIO_TEL     = "Tel: +57 314 406 5520"
NEGOCIO_EMAIL   = "yjbmotocom@gmail.com"
NEGOCIO_REGIMEN = "Regimen: Responsable de IVA"

# ---------------------------------------------------------------------------
# Dimensiones del papel
# ---------------------------------------------------------------------------
PAGE_W   = 80 * mm          # Ancho hoja 80 mm (aprox 226.77 pt)
MARGIN_X = 5 * mm           # Margen lateral
COL_W    = PAGE_W - 2 * MARGIN_X  # Ancho util de contenido

# ---------------------------------------------------------------------------
# Fuentes y tamanhos
# ---------------------------------------------------------------------------
FONT_BOLD   = "Helvetica-Bold"
FONT_NORMAL = "Helvetica"
FONT_TITLE  = 10
FONT_NORMAL_SIZE = 7.5
FONT_SMALL  = 6.5
LINE_H      = 9.5            # Interlineado base (pt)
LINE_H_SM   = 8.0            # Interlineado pequeño


def _safe(texto: str) -> str:
    """Convierte texto a latin-1 seguro para reportlab (reemplaza caracteres problematicos)."""
    return texto.encode("latin-1", errors="replace").decode("latin-1")


class _Recibo:
    """Construye el PDF en un canvas de altura dinamica."""

    def __init__(self, venta: Venta) -> None:
        self.venta = venta
        self._lineas: list[tuple] = []
        # Acumula las "instrucciones de dibujo" para calcular altura primero
        self._items: list = []
        self._y = 0.0       # cursor vertical (de arriba hacia abajo)

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------

    def generar(self) -> str:
        """Genera el PDF y devuelve la ruta al archivo temporal."""
        # Primera pasada: acumular altura
        altura = self._calcular_altura()
        page_size = (PAGE_W, altura)

        # Crear archivo temporal
        fd, path = tempfile.mkstemp(suffix=".pdf", prefix="recibo_")
        os.close(fd)

        c = canvas.Canvas(path, pagesize=page_size)
        self._dibujar(c, altura)
        c.save()
        return path

    # ------------------------------------------------------------------
    # Calculo de altura (primera pasada)
    # ------------------------------------------------------------------

    def _calcular_altura(self) -> float:
        """Simula el dibujo sin canvas para calcular la altura necesaria."""
        cursor = 0.0

        def avanzar(n: float) -> None:
            nonlocal cursor
            cursor += n

        v = self.venta
        now = datetime.now()

        # -- Cabecera -------------------------------------------------------
        avanzar(4 * mm)           # margen superior
        avanzar(LINE_H * 1.4)     # nombre empresa (grande)
        avanzar(LINE_H_SM)        # NIT
        avanzar(LINE_H_SM)        # direccion
        avanzar(LINE_H_SM)        # telefono
        avanzar(LINE_H_SM)        # email
        avanzar(LINE_H_SM)        # regimen
        avanzar(2 * mm)           # espacio

        avanzar(1)                # linea sep
        avanzar(2 * mm)

        # -- Cliente --------------------------------------------------------
        avanzar(LINE_H_SM)        # "Cliente: Consumidor Final"
        avanzar(2 * mm)

        avanzar(1)                # linea sep
        avanzar(2 * mm)

        # -- Datos transaccion -----------------------------------------------
        avanzar(LINE_H_SM)        # Factura N
        avanzar(LINE_H_SM)        # Fecha
        avanzar(LINE_H_SM)        # Hora
        # Metodo de pago puede ser largo si es Combinado
        if v.pagos_combinados:
            avanzar(LINE_H_SM)    # "Combinado:"
            for _ in v.pagos_combinados:
                avanzar(LINE_H_SM)
        else:
            avanzar(LINE_H_SM)    # metodo
        avanzar(LINE_H_SM)        # Vendedor
        avanzar(2 * mm)

        avanzar(1)                # linea sep
        avanzar(2 * mm)

        # -- Cabecera tabla -------------------------------------------------
        avanzar(LINE_H)

        # -- Filas de producto (puede haber texto largo que rompa en 2 lineas)
        prod_nombre = _safe(v.producto)
        # Calcular cuantas lineas ocupa el nombre del producto
        # col producto ~45 mm de 72 mm totales
        col_prod_w = 45 * mm
        lineas_prod = len(simpleSplit(prod_nombre, FONT_NORMAL, FONT_NORMAL_SIZE, col_prod_w))
        avanzar(max(lineas_prod, 1) * LINE_H + 1)

        avanzar(1)                # linea sep
        avanzar(2 * mm)

        # -- Totales --------------------------------------------------------
        avanzar(LINE_H)           # Subtotal
        if v.comision > 0:
            avanzar(LINE_H_SM)    # Comision plataforma
        avanzar(LINE_H * 1.2)     # TOTAL
        avanzar(2 * mm)

        avanzar(1)                # linea sep
        avanzar(2 * mm)

        # -- Resumen --------------------------------------------------------
        avanzar(LINE_H_SM)        # Forma de pago
        avanzar(LINE_H_SM)        # Items
        avanzar(2 * mm)

        avanzar(1)                # linea sep
        avanzar(2 * mm)

        # -- Texto legal ----------------------------------------------------
        legal = _safe(
            "Gracias por su compra. Este documento es "
            "un comprobante interno de venta. No reemplaza "
            "la factura electronica oficial."
        )
        lineas_legal = simpleSplit(legal, FONT_NORMAL, FONT_SMALL, COL_W)
        avanzar(len(lineas_legal) * LINE_H_SM + 1)
        avanzar(LINE_H)           # Gracias texto
        avanzar(4 * mm)           # margen inferior

        return cursor

    # ------------------------------------------------------------------
    # Dibujo real
    # ------------------------------------------------------------------

    def _dibujar(self, c: canvas.Canvas, altura: float) -> None:
        """Dibuja todos los elementos del recibo en el canvas."""
        # Trabajamos con coordenadas y = altura - offset (ReportLab dibuja de abajo hacia arriba)
        # Usamos cursor como offset desde la parte SUPERIOR de la pagina
        cur = [0.0]  # cursor (distancia desde arriba)

        def y() -> float:
            """Convierte offset de cursor a coordenada y de ReportLab."""
            return altura - cur[0]

        def nl(n: float = LINE_H) -> None:
            """Avanza el cursor n puntos hacia abajo."""
            cur[0] += n

        v = self.venta
        now = datetime.now()

        # ----------------------------------------------------------------
        # Cabecera del negocio
        # ----------------------------------------------------------------
        nl(4 * mm)

        c.setFont(FONT_BOLD, FONT_TITLE * 1.3)
        c.drawCentredString(PAGE_W / 2, y(), _safe(NEGOCIO_NOMBRE))
        nl(LINE_H * 1.4)

        c.setFont(FONT_NORMAL, FONT_NORMAL_SIZE)
        for linea in (NEGOCIO_NIT, NEGOCIO_DIR, NEGOCIO_TEL,
                      NEGOCIO_EMAIL, NEGOCIO_REGIMEN):
            c.drawCentredString(PAGE_W / 2, y(), _safe(linea))
            nl(LINE_H_SM)

        nl(2 * mm)
        self._linea_sep(c, altura, cur, "solid")
        nl(2 * mm)

        # ----------------------------------------------------------------
        # Cliente
        # ----------------------------------------------------------------
        c.setFont(FONT_BOLD, FONT_NORMAL_SIZE)
        c.drawCentredString(PAGE_W / 2, y(), "Cliente: Consumidor Final")
        nl(LINE_H_SM)

        nl(2 * mm)
        self._linea_sep(c, altura, cur, "solid")
        nl(2 * mm)

        # ----------------------------------------------------------------
        # Datos de la transaccion
        # ----------------------------------------------------------------
        c.setFont(FONT_NORMAL, FONT_NORMAL_SIZE)

        def kv(llave: str, valor: str) -> None:
            c.setFont(FONT_BOLD, FONT_NORMAL_SIZE)
            c.drawString(MARGIN_X, y(), _safe(llave))
            c.setFont(FONT_NORMAL, FONT_NORMAL_SIZE)
            c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(valor))
            nl(LINE_H_SM)

        num_recibo = str(v.id) if v.id else "---"
        kv("Factura de venta N:", f"#{num_recibo}")
        kv("Fecha:", now.strftime("%d/%m/%Y"))
        kv("Hora:", now.strftime("%I:%M %p"))

        if v.pagos_combinados:
            c.setFont(FONT_BOLD, FONT_NORMAL_SIZE)
            c.drawString(MARGIN_X, y(), "Metodo pago:")
            c.setFont(FONT_NORMAL, FONT_NORMAL_SIZE)
            c.drawRightString(PAGE_W - MARGIN_X, y(), "Combinado")
            nl(LINE_H_SM)
            for p in v.pagos_combinados:
                c.drawString(MARGIN_X + 4 * mm, y(),
                             _safe(f"  {p['metodo']}:"))
                c.drawRightString(PAGE_W - MARGIN_X, y(),
                                  _safe(cop(p["monto"])))
                nl(LINE_H_SM)
        else:
            kv("Metodo pago:", v.metodo_pago)

        kv("Vendedor:", "YJB Motocom")

        nl(2 * mm)
        self._linea_sep(c, altura, cur, "solid")
        nl(2 * mm)

        # ----------------------------------------------------------------
        # Tabla de productos
        # ----------------------------------------------------------------
        # Columnas: # | Descripcion | Cant | P.Unit | Total
        # Anchos relativos (en mm desde MARGIN_X)
        x_num     = MARGIN_X
        x_prod    = MARGIN_X + 5 * mm
        x_cant    = MARGIN_X + 48 * mm
        x_punit   = MARGIN_X + 54 * mm
        x_total_r = PAGE_W - MARGIN_X  # drawRightString

        # Cabecera tabla
        c.setFont(FONT_BOLD, FONT_SMALL + 0.5)
        c.drawString(x_num,   y(), "#")
        c.drawString(x_prod,  y(), "Descripcion")
        c.drawString(x_cant,  y(), "Cant")
        c.drawString(x_punit, y(), "P.Unit")
        c.drawRightString(x_total_r, y(), "Total")
        nl(LINE_H)

        # Fila del producto
        prod_nombre = _safe(v.producto)
        col_prod_w  = x_cant - x_prod - 2 * mm
        lineas_prod = simpleSplit(prod_nombre, FONT_NORMAL, FONT_NORMAL_SIZE, col_prod_w)

        c.setFont(FONT_BOLD, FONT_SMALL + 0.5)
        c.drawString(x_num, y(), "1")

        c.setFont(FONT_NORMAL, FONT_NORMAL_SIZE)
        fila_y = y()
        for i, linea in enumerate(lineas_prod):
            c.drawString(x_prod, fila_y - i * LINE_H, linea)

        c.drawString(x_cant,  y(), str(v.cantidad))
        c.drawString(x_punit, y(), _safe(cop(v.precio)))
        total_venta = v.precio * v.cantidad
        c.drawRightString(x_total_r, y(), _safe(cop(total_venta)))

        nl(max(len(lineas_prod), 1) * LINE_H + 1)

        self._linea_sep(c, altura, cur, "dashed")
        nl(2 * mm)

        # ----------------------------------------------------------------
        # Totales
        # ----------------------------------------------------------------
        subtotal = v.precio * v.cantidad

        c.setFont(FONT_NORMAL, FONT_NORMAL_SIZE)
        c.drawString(MARGIN_X, y(), "Subtotal:")
        c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(cop(subtotal)))
        nl(LINE_H)

        if v.comision > 0:
            c.setFont(FONT_NORMAL, FONT_SMALL)
            c.drawString(MARGIN_X, y(), _safe(f"Comision ({v.metodo_pago.split()[0]}):"))
            c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(cop(v.comision)))
            nl(LINE_H_SM)

        c.setFont(FONT_BOLD, FONT_TITLE)
        c.drawString(MARGIN_X, y(), "TOTAL:")
        c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(cop(subtotal)))
        nl(LINE_H * 1.2)

        nl(2 * mm)
        self._linea_sep(c, altura, cur, "solid")
        nl(2 * mm)

        # ----------------------------------------------------------------
        # Resumen
        # ----------------------------------------------------------------
        c.setFont(FONT_NORMAL, FONT_NORMAL_SIZE)
        metodo_display = "Combinado" if v.pagos_combinados else v.metodo_pago
        c.drawString(MARGIN_X, y(), "Forma de pago:")
        c.drawRightString(PAGE_W - MARGIN_X, y(), _safe(metodo_display))
        nl(LINE_H_SM)

        c.drawString(MARGIN_X, y(), "Items:")
        c.drawRightString(PAGE_W - MARGIN_X, y(), str(v.cantidad))
        nl(LINE_H_SM)

        nl(2 * mm)
        self._linea_sep(c, altura, cur, "solid")
        nl(2 * mm)

        # ----------------------------------------------------------------
        # Texto legal y despedida
        # ----------------------------------------------------------------
        legal = _safe(
            "Gracias por su compra. Este documento es "
            "un comprobante interno de venta. No reemplaza "
            "la factura electronica oficial."
        )
        c.setFont(FONT_NORMAL, FONT_SMALL)
        lineas_legal = simpleSplit(legal, FONT_NORMAL, FONT_SMALL, COL_W)
        for linea in lineas_legal:
            c.drawCentredString(PAGE_W / 2, y(), linea)
            nl(LINE_H_SM)

        nl(1)
        c.setFont(FONT_BOLD, FONT_NORMAL_SIZE)
        c.drawCentredString(PAGE_W / 2, y(), "!Gracias por su compra!")
        nl(LINE_H)

    # ------------------------------------------------------------------
    # Helpers de dibujo
    # ------------------------------------------------------------------

    def _linea_sep(self, c: canvas.Canvas, altura: float,
                   cur: list, estilo: str = "solid") -> None:
        """Dibuja una linea separadora horizontal."""
        yy = altura - cur[0]
        if estilo == "dashed":
            c.setDash(3, 3)
        else:
            c.setDash(1, 0)
        c.setLineWidth(0.4)
        c.line(MARGIN_X, yy, PAGE_W - MARGIN_X, yy)
        c.setDash(1, 0)
        cur[0] += 1


# ---------------------------------------------------------------------------
# Funcion publica
# ---------------------------------------------------------------------------

def generar_recibo(venta: Venta) -> str:
    """
    Genera el recibo de la venta como PDF en un archivo temporal.
    Retorna la ruta absoluta al archivo PDF generado.
    """
    return _Recibo(venta).generar()
