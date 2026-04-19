"""
services/pdf_distrifabrica_parser.py
Parsea facturas de DISTRIFABRICA RAMIREZ SAS (formato diferente al de ACCESORIOS PARA MOTOS).
Marcas soportadas: SHAFT, SHAFT PRO, ABT HRO, ICH.
"""
from __future__ import annotations

import re
from pathlib import Path

from services.pdf_pedido_parser import ItemPedido

# ---------------------------------------------------------------------------
# Patrones
# ---------------------------------------------------------------------------

# Línea que inicia un ítem: [código] CASCO ...
_PAT_INICIO = re.compile(r'^\[(\d+)\]\s+(CASCO.+)$', re.IGNORECASE)

# Talla al final de línea: "... T M" o "... T XL"
_PAT_TALLA_FIN = re.compile(r'\bT\s+(XS|S|M|L|XL|2XL)\s*$', re.IGNORECASE)

# Línea que es solo una talla (cuando la talla queda partida en línea propia)
_PAT_TALLA_SOLA = re.compile(r'^(XS|S|M|L|XL|2XL)$', re.IGNORECASE)

# Precio colombiano: 314.500,00
_PAT_PRECIO = re.compile(r'^(\d{1,3}(?:\.\d{3})*),(\d{2})$')

# Porcentaje de descuento: 10,00 o 0,00
_PAT_DCTO = re.compile(r'^(\d{1,2}),(\d{2})$')


# ---------------------------------------------------------------------------
# Entrada pública
# ---------------------------------------------------------------------------

def parsear_pdf_distrifabrica(ruta: str | Path) -> list[ItemPedido]:
    """Lee el PDF de DISTRIFABRICA y retorna ítems de cascos."""
    try:
        import pypdf
    except ImportError:
        raise ImportError("pypdf no está instalado. Ejecuta: pip install pypdf")

    reader = pypdf.PdfReader(str(ruta))
    paginas = [p.extract_text() or "" for p in reader.pages]
    return _parsear_texto("\n".join(paginas))


def generar_codigos_barras_distrifabrica(items: list[ItemPedido]) -> dict[int, str]:
    """Usa el código interno del proveedor como código de barras sugerido."""
    return {i: item.codigo_proveedor for i, item in enumerate(items)}


# ---------------------------------------------------------------------------
# Parser interno
# ---------------------------------------------------------------------------

def _parsear_texto(texto: str) -> list[ItemPedido]:
    lineas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    items: list[ItemPedido] = []
    i = 0

    while i < len(lineas):
        m = _PAT_INICIO.match(lineas[i])
        if not m:
            i += 1
            continue

        codigo_prov = m.group(1)
        desc_lineas = [m.group(2)]
        i += 1

        # ── Recopilar líneas de descripción hasta la cantidad ─────────────
        while i < len(lineas):
            ln = lineas[i]
            if _PAT_INICIO.match(ln):      # siguiente ítem
                break
            if re.match(r'^\d+$', ln):     # cantidad → fin descripción
                break
            desc_lineas.append(ln)
            i += 1

        # ── Extraer talla del texto completo ──────────────────────────────
        full = " ".join(desc_lineas)
        talla = ""

        tm = _PAT_TALLA_FIN.search(full)
        if tm:
            talla = tm.group(1).upper()
            full = full[:tm.start()].strip()
        else:
            # Último recurso: última palabra es talla y penúltima es "T"
            palabras = full.split()
            if len(palabras) >= 2 and palabras[-1].upper() in {"XS","S","M","L","XL","2XL"}:
                if palabras[-2].upper() == "T":
                    talla = palabras[-1].upper()
                    full = " ".join(palabras[:-2]).strip()
                else:
                    talla = palabras[-1].upper()
                    full = " ".join(palabras[:-1]).strip()

        if not talla:
            continue

        descripcion = full
        if not re.search(r'CASCO', descripcion, re.IGNORECASE):
            continue

        # ── Datos numéricos ──────────────────────────────────────────────
        cantidad    = 1
        precio_unit = 0.0
        dcto_pct    = 0.0
        importe     = 0.0

        # Cantidad
        if i < len(lineas) and re.match(r'^\d+$', lineas[i]):
            cantidad = int(lineas[i])
            i += 1

        # "Unidades"
        if i < len(lineas) and lineas[i].lower() == "unidades":
            i += 1

        # Precio unitario (con IVA, formato colombiano: 314.500,00)
        if i < len(lineas):
            pm = _PAT_PRECIO.match(lineas[i])
            if pm:
                precio_unit = float(pm.group(1).replace(".", "") + "." + pm.group(2))
                i += 1

        # % descuento
        if i < len(lineas):
            dm = _PAT_DCTO.match(lineas[i])
            if dm:
                dcto_pct = float(dm.group(1) + "." + dm.group(2))
                i += 1

        # "19%" (IVA — siempre presente)
        if i < len(lineas) and "19%" in lineas[i]:
            i += 1

        # "$" separado o "$  " (puede estar en su propia línea)
        if i < len(lineas) and lineas[i].startswith("$"):
            if lineas[i] == "$":
                i += 1
            else:
                # "$  237.857,14" en una sola línea
                resto = lineas[i][1:].strip()
                im = _PAT_PRECIO.match(resto)
                if im:
                    importe = float(im.group(1).replace(".", "") + "." + im.group(2))
                    i += 1

        # Importe (sin IVA, con descuento aplicado) — si no se tomó arriba
        if importe == 0.0 and i < len(lineas):
            im = _PAT_PRECIO.match(lineas[i])
            if im:
                importe = float(im.group(1).replace(".", "") + "." + im.group(2))
                i += 1

        if precio_unit <= 0:
            continue

        # costo_sin_iva = importe / cantidad (ya descontado y sin IVA)
        costo_unit = round(importe / cantidad, 2) if cantidad > 0 and importe > 0 else round(
            precio_unit * (1 - dcto_pct / 100) / 1.19, 2
        )

        item = ItemPedido(
            modelo_pdf=_extraer_modelo(descripcion),
            descripcion_raw=descripcion,
            talla=talla,
            precio_con_iva=precio_unit,
            costo_sin_iva=costo_unit,
            dcto_pct=dcto_pct,
            cantidad=cantidad,
            codigo_proveedor=codigo_prov,
        )
        item.nombre_sugerido = _generar_nombre(descripcion, talla)
        items.append(item)

    return items


# ---------------------------------------------------------------------------
# Helpers de nombre y modelo
# ---------------------------------------------------------------------------

def _extraer_modelo(desc: str) -> str:
    """Extrae una clave de modelo legible: SHAFT-560-EVO, HRO-3480, ICH-501, etc."""
    m = re.search(
        r'(?:INT|MUL|ABT)\s+'
        r'((?:SHAFT\s+PRO|SHAFT|HRO|ICH)\s+\w+(?:\s+\w+)?)',
        desc, re.IGNORECASE,
    )
    if m:
        return re.sub(r'\s+', '-', m.group(1).strip()).upper()
    return "CASCO-DESCONOCIDO"


def _generar_nombre(desc: str, talla: str) -> str:
    """
    "CASCO INT SHAFT 560 EVO SOLID NM RJ V SM REVO RJ"  → "CASCO SHAFT 560 EVO SOLID NM RJ V SM REVO RJ -T:M"
    Elimina el tipo (INT/MUL/ABT) que no aporta información comercial.
    """
    nombre = re.sub(r'CASCO\s+(?:INT|MUL|ABT)\s+', 'CASCO ', desc, flags=re.IGNORECASE)
    nombre = nombre.strip().upper()
    return f"{nombre} -T:{talla}"
