"""
services/pdf_pedido_parser.py
Parsea facturas de ACCESORIOS PARA MOTOS S.A.S. (texto extraído por pypdf).
Solo procesa ítems de casco (código proveedor XTR-...).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

TALLAS_VALIDAS = {"XS", "S", "M", "L", "XL", "2XL"}
TALLA_DIGITO   = {"XS": "1", "S": "2", "M": "3", "L": "4", "XL": "5", "2XL": "6"}
PREFIJO_XTRONG = "1106"

# Mapeo código de modelo → nombre de display en inventario
_MODEL_DISPLAY: dict[str, str] = {
    "DREXO": "GP 80 XTR-DREXO",
    "M70":   "M70",
    "M69":   "M69",
    "902":   "902",
    "820":   "820",
    "R1":    "R1",
}

# Palabras/patrones ruidosos que se eliminan de la descripción al generar nombre
_RUIDO = re.compile(
    r"\b(?:SET|ECE-\w+|XTRONG(?:-GP)?|FLY|SP|FOTO-\S+|RACING)\b"
    r"|\bVISOR\s+\S+",
    re.IGNORECASE,
)

# Líneas de encabezado/pie que deben ignorarse al reconstruir descripción
_ES_HEADER = re.compile(
    r"ACCESORIOS PARA MOTOS|YJBMOTOCOM|BOGOT|NIT\.|TEL[EÉ]FONO|VENDEDOR"
    r"|SE[NÑ]ORES|EMAIL|yojan|PEDIDOS|DIRECCI[OÓ]N|CIUDAD|DEPENDEN"
    r"|RECIB[IÍ] CONFORME|VPOPAYAN|OBSERVACIONES|BRUTO|DESCUENTO:"
    r"|SUBTOTAL:|IVA:|NETO|FECHA|pag:|CANT\.|VALOR|PRECIO|C[OÓ]DIGO"
    r"|PORCENTAJE|RTE\.",
    re.IGNORECASE,
)

# Líneas que parecen precios embebidos sin ser ítems XTRONG (ej. SEGURO DE MERCANCIA)
_PRECIO_EMBEBIDO = re.compile(r"\d{1,3},\d{3}")

# Patrón para línea de datos: VALOR+PRECIO+DCTOpct+CODIGO+NCAJAS
# Ejemplo: "254,202302,500 5%16353 191"
_PAT_DATOS = re.compile(
    r"^(\d{1,3},\d{3})(\d{1,3},\d{3})\s+(\d+(?:\.\d+)?)%(\S+)\s+(\d+)\s*$"
)


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

@dataclass
class ItemPedido:
    """Un ítem de casco extraído de la factura del proveedor."""
    modelo_pdf:       str    # ej. "XTR-352R1"
    descripcion_raw:  str    # descripción completa del PDF (sin talla)
    talla:            str    # XS / S / M / L / XL / 2XL
    precio_con_iva:   float  # precio por unidad CON IVA (columna PRECIO del PDF)
    costo_sin_iva:    float  # = precio_con_iva / 1.19  → costo real para inventario
    dcto_pct:         float  # % descuento del proveedor
    cantidad:         int    # número de unidades
    codigo_proveedor: str    # código interno del proveedor
    nombre_sugerido:  str = ""  # nombre generado para inventario


# ---------------------------------------------------------------------------
# Entrada pública
# ---------------------------------------------------------------------------

def parsear_pdf(ruta: str | Path) -> list[ItemPedido]:
    """Lee el PDF y retorna ítems de cascos. Lanza ImportError si pypdf no está."""
    try:
        import pypdf
    except ImportError:
        raise ImportError("pypdf no está instalado. Ejecuta: pip install pypdf")

    reader = pypdf.PdfReader(str(ruta))
    paginas = [p.extract_text() or "" for p in reader.pages]
    return _parsear_texto("\n".join(paginas))


# ---------------------------------------------------------------------------
# Parser interno
# ---------------------------------------------------------------------------

def _parsear_texto(texto: str) -> list[ItemPedido]:
    lineas = [ln.strip() for ln in texto.splitlines() if ln.strip()]
    items: list[ItemPedido] = []

    for idx, linea in enumerate(lineas):
        m = _PAT_DATOS.match(linea)
        if not m:
            continue

        valor_raw  = float(m.group(1).replace(",", ""))
        precio_raw = float(m.group(2).replace(",", ""))
        dcto_pct   = float(m.group(3))
        codigo     = m.group(4)

        # Precio por unidad (con IVA) y costo sin IVA
        precio_unit = precio_raw
        costo_unit  = round(precio_unit / 1.19, 2)

        # Calcular cantidad: VALOR_total ÷ costo_unit
        cantidad = max(1, round(valor_raw / costo_unit)) if costo_unit > 0 else 1

        # Reconstruir descripción + talla mirando hacia atrás
        talla = ""
        desc_partes: list[str] = []
        j = idx - 1
        while j >= 0 and len(desc_partes) < 6:
            ln = lineas[j]
            if _PAT_DATOS.match(ln):
                break
            if _ES_HEADER.search(ln):
                break
            # Línea con precio embebido que NO es un casco XTR (ej. SEGURO DE MERCANCIA)
            if _PRECIO_EMBEBIDO.search(ln) and not re.search(r"XTR-", ln, re.IGNORECASE):
                break
            # Talla en línea propia
            if ln in TALLAS_VALIDAS and not talla:
                talla = ln
                j -= 1
                continue
            # Talla al final de la línea de descripción (ej. "AZUL MATE VISOR ROJO XL")
            palabras = ln.split()
            if palabras and palabras[-1] in TALLAS_VALIDAS and not talla:
                talla = palabras[-1]
                resto = " ".join(palabras[:-1]).strip()
                if resto:
                    desc_partes.insert(0, resto)
                j -= 1
                continue
            desc_partes.insert(0, ln)
            j -= 1

        descripcion = " ".join(desc_partes).strip()

        # Solo cascos XTRONG (descripción contiene XTR-...)
        mod_m = re.search(r"XTR-(\w+)", descripcion, re.IGNORECASE)
        if not (mod_m and talla):
            continue

        modelo_pdf = f"XTR-{mod_m.group(1).upper()}"
        item = ItemPedido(
            modelo_pdf=modelo_pdf,
            descripcion_raw=descripcion,
            talla=talla,
            precio_con_iva=precio_unit,
            costo_sin_iva=costo_unit,
            dcto_pct=dcto_pct,
            cantidad=cantidad,
            codigo_proveedor=codigo,
        )
        item.nombre_sugerido = _generar_nombre(item)
        items.append(item)

    return items


# ---------------------------------------------------------------------------
# Generación de nombre para inventario
# ---------------------------------------------------------------------------

def _generar_nombre(item: ItemPedido) -> str:
    """CASCO XTRONG [model_display] [color_limpio] -T:[talla]"""
    codigo  = item.modelo_pdf.replace("XTR-", "")
    display = _MODEL_DISPLAY.get(codigo, codigo)

    desc = item.descripcion_raw
    # Reparar guiones partidos por salto de línea: "BLANCO- NARANJA" → "BLANCO-NARANJA"
    desc = re.sub(r"-\s+", "-", desc)
    desc = re.sub(re.escape(item.modelo_pdf), "", desc, flags=re.IGNORECASE)
    desc = _RUIDO.sub(" ", desc)
    desc = re.sub(rf"\b{re.escape(item.talla)}\b", "", desc)
    # Eliminar palabras sueltas de una sola letra que queden como artefactos
    desc = re.sub(r"\b[A-Z]\b", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip().upper()

    return f"CASCO XTRONG {display} {desc} -T:{item.talla}"


def _color_key(item: ItemPedido) -> str:
    """Clave de color para agrupar tallas del mismo diseño."""
    desc = item.descripcion_raw
    desc = re.sub(re.escape(item.modelo_pdf), "", desc, flags=re.IGNORECASE)
    desc = _RUIDO.sub(" ", desc)
    desc = re.sub(rf"\b{re.escape(item.talla)}\b", "", desc)
    return re.sub(r"\s+", " ", desc).strip().upper()


# ---------------------------------------------------------------------------
# Generación de códigos de barras
# ---------------------------------------------------------------------------

def generar_codigos_barras(items: list[ItemPedido]) -> dict[int, str]:
    """
    Genera códigos de barras para cada ítem del pedido.
    Retorna {índice_en_items: codigo_barras_10dig}.

    Estructura CB XTRONG (10 dígitos):
        1106  NNN  SS  T
        marca mod  sub talla
    """
    from database.inventario_repo import obtener_todos_productos

    prods = obtener_todos_productos()

    # ── Recopilar CBs XTRONG existentes ────────────────────────────────────
    cbs_existentes: list[str] = [
        str(p.codigo_barras)
        for p in prods
        if str(p.codigo_barras or "").startswith(PREFIJO_XTRONG)
        and len(str(p.codigo_barras or "")) == 10
    ]

    nums_modelo_usados: set[int] = set()
    sub_refs_por_modelo: dict[str, set[int]] = {}
    for cb in cbs_existentes:
        try:
            nums_modelo_usados.add(int(cb[4:7]))
            num_mod = cb[4:7]
            sub_refs_por_modelo.setdefault(num_mod, set()).add(int(cb[7:9]))
        except ValueError:
            pass

    # ── Mapeo modelo_code → num_modelo ya en inventario ────────────────────
    modelo_a_num: dict[str, str] = {}
    for p in prods:
        cb = str(p.codigo_barras or "")
        if not (cb.startswith(PREFIJO_XTRONG) and len(cb) == 10):
            continue
        nombre = (p.producto or "").upper()
        for code, display in _MODEL_DISPLAY.items():
            if display.upper() in nombre or f"XTR-{code}" in nombre:
                modelo_a_num[code] = cb[4:7]
                break

    next_modelo = (max(nums_modelo_usados) if nums_modelo_usados else 0) + 1

    # ── Asignar modelo + sub-ref a cada ítem ───────────────────────────────
    resultado: dict[int, str] = {}
    color_a_subref: dict[tuple[str, str], str] = {}

    for i, item in enumerate(items):
        codigo = item.modelo_pdf.replace("XTR-", "")

        # Número de modelo
        if codigo not in modelo_a_num:
            modelo_a_num[codigo] = f"{next_modelo:03d}"
            next_modelo += 1
        num_mod = modelo_a_num[codigo]

        # Sub-referencia por color
        ck = _color_key(item)
        grupo = (codigo, ck)
        if grupo not in color_a_subref:
            usados = sub_refs_por_modelo.get(num_mod, set())
            next_sub = (max(usados) if usados else 0) + 1
            sub_str = f"{next_sub:02d}"
            color_a_subref[grupo] = sub_str
            usados.add(next_sub)
            sub_refs_por_modelo[num_mod] = usados
        else:
            sub_str = color_a_subref[grupo]

        talla_dig = TALLA_DIGITO.get(item.talla, "1")
        resultado[i] = f"{PREFIJO_XTRONG}{num_mod}{sub_str}{talla_dig}"

    return resultado
