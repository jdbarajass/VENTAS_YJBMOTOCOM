"""
services/escpos_printer.py
Impresión directa de recibos POS via protocolo ESC/POS.

Usa python-escpos Dummy para generar los bytes del protocolo ESC/POS y
Windows Spooler API via ctypes para enviarlos a la impresora (sin pywin32).
Compatible con impresoras térmicas USB de 80mm instaladas como Windows printers.
"""

import ctypes
import ctypes.wintypes as wt
import subprocess
import sys

from models.venta import Venta
from utils.formatters import cop

CHARS_PER_LINE = 48  # Font A en papel 80mm (72mm imprimible)


# ---------------------------------------------------------------------------
# Impresión via Windows Spooler API (ctypes, sin pywin32)
# ---------------------------------------------------------------------------

def _raw_print_windows(printer_name: str, data: bytes) -> bool:
    """
    Envía bytes raw a la impresora via Windows Spooler API usando ctypes.
    No requiere pywin32. Funciona con cualquier impresora instalada en Windows.
    """
    if sys.platform != "win32" or not data:
        return False
    try:
        winspool = ctypes.WinDLL("winspool.drv")

        h_printer = wt.HANDLE()
        if not winspool.OpenPrinterW(printer_name, ctypes.byref(h_printer), None):
            return False

        class DOC_INFO_1(ctypes.Structure):
            _fields_ = [
                ("pDocName",    wt.LPWSTR),
                ("pOutputFile", wt.LPWSTR),
                ("pDatatype",   wt.LPWSTR),
            ]

        doc = DOC_INFO_1("Recibo YJB", None, "RAW")
        job_id = winspool.StartDocPrinterW(h_printer, 1, ctypes.byref(doc))
        if not job_id:
            winspool.ClosePrinter(h_printer)
            return False

        try:
            winspool.StartPagePrinter(h_printer)
            written = wt.DWORD(0)
            buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
            winspool.WritePrinter(
                h_printer, buf, wt.DWORD(len(data)), ctypes.byref(written)
            )
            winspool.EndPagePrinter(h_printer)
        finally:
            winspool.EndDocPrinter(h_printer)
            winspool.ClosePrinter(h_printer)

        return written.value > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Detección de impresoras Windows
# ---------------------------------------------------------------------------

def listar_impresoras_windows() -> list[str]:
    """Retorna impresoras instaladas en Windows, filtrando virtuales."""
    try:
        result = subprocess.run(
            ["powershell", "-NonInteractive", "-Command",
             "Get-Printer | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, timeout=6,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
            _VIRTUAL = {
                "microsoft print to pdf", "onenote", "pdfcreator",
                "fax", "xps", "snagit", "cutepdf", "docudesk",
            }
            return [p for p in lines
                    if not any(v in p.lower() for v in _VIRTUAL)]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Helpers de formato texto
# ---------------------------------------------------------------------------

def _safe(texto: str) -> str:
    """Reemplaza tildes y caracteres no-ASCII para compatibilidad ESC/POS."""
    tabla = str.maketrans("áéíóúÁÉÍÓÚñÑ¡¿", "aeiouAEIOUnN!?")
    return texto.translate(tabla).encode("ascii", errors="replace").decode("ascii")


def _kv(key: str, value: str, W: int = CHARS_PER_LINE) -> str:
    """Línea clave—valor con valor alineado a la derecha."""
    key = _safe(key)
    value = _safe(value)
    space = W - len(key) - len(value)
    if space < 1:
        value = value[:max(W - len(key) - 1, 1)]
        space = 1
    return key + " " * space + value


def _sep(ch: str = "=", W: int = CHARS_PER_LINE) -> str:
    return ch * W


def _wrap(texto: str, W: int = CHARS_PER_LINE, indent: str = "   ") -> list[str]:
    """Divide texto en líneas de máximo W caracteres."""
    lineas: list[str] = []
    while len(texto) > W:
        corte = texto.rfind(" ", 0, W)
        if corte <= 0:
            corte = W
        lineas.append(texto[:corte])
        texto = indent + texto[corte:].lstrip()
    if texto:
        lineas.append(texto)
    return lineas


# ---------------------------------------------------------------------------
# Generación de contenido del recibo (texto plano, para vista previa)
# ---------------------------------------------------------------------------

def generar_texto_recibo(ventas) -> str:
    """
    Genera el texto del recibo como cadena de Python.
    Sirve para la vista previa en pantalla (sin bytes ESC/POS).
    """
    from datetime import datetime
    if isinstance(ventas, Venta):
        ventas = [ventas]
    ventas = list(ventas)

    v0 = ventas[0]
    now = datetime.now()
    W = CHARS_PER_LINE
    lines: list[str] = []

    def ln(text: str = "") -> None:
        lines.append(_safe(str(text)))

    def sep(ch: str = "=") -> None:
        ln(_sep(ch, W))

    def kv(key: str, value: str) -> None:
        ln(_kv(key, value, W))

    def ctr(text: str) -> None:
        ln(_safe(text).center(W))

    ctr("YJB MOTOCOM")
    ctr("NIT 1032464724-2")
    ctr("AK 14 # 17-21 LOCAL 127, Bogota D.C.")
    ctr("Tel: +57 314 406 5520")
    ctr("yjbmotocom@gmail.com")
    sep()
    ctr("Cliente: Consumidor Final")
    sep()

    num_factura = getattr(v0, "numero_factura", None) or v0.id
    kv("Factura N:", f"#{num_factura}" if num_factura else "---")
    fecha_str = (v0.fecha.strftime("%d/%m/%Y")
                 if hasattr(v0.fecha, "strftime") else str(v0.fecha))
    kv("Fecha:", fecha_str)
    kv("Hora:", now.strftime("%I:%M %p"))

    if v0.pagos_combinados:
        kv("Metodo pago:", "Combinado")
        for pc in v0.pagos_combinados:
            kv(f"  {pc['metodo']}:", cop(pc["monto"]))
    else:
        kv("Metodo pago:", v0.metodo_pago)

    kv("Vendedor:", "YJB Motocom")
    sep()

    hdr_key = "#  Descripcion"
    hdr_val = "Total"
    ln(hdr_key + hdr_val.rjust(W - len(hdr_key)))
    sep("-")

    for idx, v in enumerate(ventas, start=1):
        nombre = f"{idx}. {_safe(v.producto)}"
        for linea in _wrap(nombre, W):
            ln(linea)
        total_linea = v.precio * v.cantidad
        detalle = f"{v.cantidad}u x {cop(v.precio)} = {cop(total_linea)}"
        ln(_safe(detalle).rjust(W))

    sep()

    subtotal = sum(v.precio * v.cantidad for v in ventas)
    total_com = sum(v.comision for v in ventas)
    kv("Subtotal:", cop(subtotal))
    if total_com > 0:
        metodo_com = (v0.metodo_pago.split()[0]
                      if not v0.pagos_combinados else "Comb.")
        kv(f"Comision ({metodo_com}):", cop(total_com))
    kv("TOTAL:", cop(subtotal))
    sep()

    metodo_display = "Combinado" if v0.pagos_combinados else v0.metodo_pago
    total_items = sum(v.cantidad for v in ventas)
    kv("Forma de pago:", _safe(metodo_display))
    kv("Items:", str(total_items))
    sep()

    legal = ("Gracias por su compra. Este documento es un comprobante "
             "interno de venta. No reemplaza la factura electronica oficial.")
    for linea in _wrap(_safe(legal), W, ""):
        ctr(linea)
    ln()
    ctr("!Gracias por su compra!")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Generación de bytes ESC/POS (usa Dummy de python-escpos)
# ---------------------------------------------------------------------------

def _generar_bytes_escpos(ventas: list[Venta]) -> bytes:
    """Genera los bytes ESC/POS del recibo usando python-escpos Dummy printer."""
    from escpos.printer import Dummy  # type: ignore
    d = Dummy()
    _escribir_recibo(d, ventas)
    return d.output


def _escribir_recibo(p, ventas: list[Venta]) -> None:
    """Escribe el recibo al objeto ESC/POS printer (Dummy o Win32Raw)."""
    from datetime import datetime
    v0 = ventas[0]
    now = datetime.now()
    W = CHARS_PER_LINE

    def ln(text: str = "") -> None:
        p.text(_safe(str(text)) + "\n")

    def sep(ch: str = "=") -> None:
        ln(_sep(ch, W))

    def kv(key: str, value: str) -> None:
        ln(_kv(key, value, W))

    p.set(align="center", bold=True)
    ln("YJB MOTOCOM")
    p.set(align="center", bold=False)
    ln("NIT 1032464724-2")
    ln("AK 14 # 17-21 LOCAL 127, Bogota D.C.")
    ln("Tel: +57 314 406 5520")
    ln("yjbmotocom@gmail.com")
    p.set(align="left", bold=False)
    sep()

    p.set(align="center", bold=True)
    ln("Cliente: Consumidor Final")
    p.set(align="left", bold=False)
    sep()

    num_factura = getattr(v0, "numero_factura", None) or v0.id
    kv("Factura N:", f"#{num_factura}" if num_factura else "---")
    fecha_str = (v0.fecha.strftime("%d/%m/%Y")
                 if hasattr(v0.fecha, "strftime") else str(v0.fecha))
    kv("Fecha:", fecha_str)
    kv("Hora:", now.strftime("%I:%M %p"))

    if v0.pagos_combinados:
        kv("Metodo pago:", "Combinado")
        for pc in v0.pagos_combinados:
            kv(f"  {pc['metodo']}:", cop(pc["monto"]))
    else:
        kv("Metodo pago:", v0.metodo_pago)

    kv("Vendedor:", "YJB Motocom")
    sep()

    p.set(bold=True)
    hdr_key = "#  Descripcion"
    hdr_val = "Total"
    ln(hdr_key + hdr_val.rjust(W - len(hdr_key)))
    p.set(bold=False)
    sep("-")

    for idx, v in enumerate(ventas, start=1):
        nombre = f"{idx}. {_safe(v.producto)}"
        for linea in _wrap(nombre, W):
            ln(linea)
        total_linea = v.precio * v.cantidad
        detalle = f"{v.cantidad}u x {cop(v.precio)} = {cop(total_linea)}"
        ln(_safe(detalle).rjust(W))

    sep()

    subtotal = sum(v.precio * v.cantidad for v in ventas)
    total_com = sum(v.comision for v in ventas)
    kv("Subtotal:", cop(subtotal))
    if total_com > 0:
        metodo_com = (v0.metodo_pago.split()[0]
                      if not v0.pagos_combinados else "Comb.")
        kv(f"Comision ({metodo_com}):", cop(total_com))

    p.set(bold=True)
    kv("TOTAL:", cop(subtotal))
    p.set(bold=False)
    sep()

    metodo_display = "Combinado" if v0.pagos_combinados else v0.metodo_pago
    total_items = sum(v.cantidad for v in ventas)
    kv("Forma de pago:", _safe(metodo_display))
    kv("Items:", str(total_items))
    sep()

    p.set(align="center")
    legal = ("Gracias por su compra. Este documento es un comprobante "
             "interno de venta. No reemplaza la factura electronica oficial.")
    for linea in _wrap(_safe(legal), W, ""):
        ln(linea)
    p.text("\n")
    p.set(align="center", bold=True)
    ln("!Gracias por su compra!")
    p.set(align="left", bold=False)
    p.text("\n\n\n")
    p.cut()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def imprimir_recibo_escpos(ventas: list[Venta], nombre_impresora: str) -> bool:
    """
    Imprime el recibo directamente via ESC/POS.
    Genera bytes con python-escpos Dummy y los envía via ctypes sin pywin32.
    Retorna True si el envío fue exitoso.
    """
    if not nombre_impresora or sys.platform != "win32":
        return False
    try:
        raw = _generar_bytes_escpos(ventas)
        return _raw_print_windows(nombre_impresora, raw)
    except Exception:
        return False
