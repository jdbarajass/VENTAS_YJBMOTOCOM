"""
services/inventario_gen.py
Genera automáticamente el serial y el código de barras para productos nuevos.

Formato del código de barras (10 dígitos): CC MM NNN VV T
  CC  — categoría (11=Casco, 12=Baul, 13=Chaqueta, 14=Cuello, 15=Guante,
                   16=Impermeable, 17=Audio/Intercomunicador, 18=Tech,
                   19=Slider, 20=Parrilla, 10=Accesorios)
  MM  — subtipo/marca dentro de la categoría (01-99)
  NNN — número de modelo (001-999, zero-padded)
  VV  — variante/color dentro del modelo (01-99, zero-padded)
  T   — dígito de talla (0=N/A, 1=XS, 2=S, 3=M, 4=L, 5=XL, 6=2XL, 7=3XL)
"""

from __future__ import annotations

# ── Mapas de referencia ────────────────────────────────────────────────────────

_CAT_PREFIJOS: dict[str, str] = {
    "casco":             "11",
    "baul":              "12",
    "baúl":              "12",
    "chaqueta":          "13",
    "cuello":            "14",
    "guante":            "15",
    "impermeable":       "16",
    "audio":             "17",
    "intercomunicador":  "17",
    "tech":              "18",
    "tecnología":        "18",
    "tecnologia":        "18",
    "slider":            "19",
    "parrilla":          "20",
    "accesorio":         "10",
    "accesorios":        "10",
}

_TALLA_DIGITO: dict[str, str] = {
    "n/a": "0",
    "xs":  "1",
    "s":   "2",
    "m":   "3",
    "l":   "4",
    "xl":  "5",
    "2xl": "6",
    "xxl": "6",
    "3xl": "7",
}

TALLAS_DISPONIBLES = ["XS", "S", "M", "L", "XL", "2XL", "3XL", "N/A"]


# ── Funciones públicas ─────────────────────────────────────────────────────────

def generar_siguiente_serial(productos: list) -> int:
    """Retorna el siguiente serial entero (MAX existente + 1, mínimo 1)."""
    maximo = 0
    for p in productos:
        try:
            serial_int = int(str(getattr(p, "serial", 0) or 0))
            if serial_int > maximo:
                maximo = serial_int
        except (ValueError, TypeError):
            pass
    return maximo + 1


def detectar_categoria(nombre: str) -> str:
    """
    Intenta inferir el prefijo CC (2 dígitos) a partir del nombre del producto.
    Retorna "10" (Accesorios) si no reconoce ninguna categoría.
    """
    nombre_lc = nombre.lower()
    for kw, cc in _CAT_PREFIJOS.items():
        if kw in nombre_lc:
            return cc
    return "10"


def generar_codigo_barras_auto(
    nombre: str,
    talla: str,
    productos_existentes: list,
) -> str:
    """
    Genera un código de barras de 10 dígitos siguiendo el formato CC+MM+NNN+VV+T.

    Estrategia:
    1. CC  — se detecta del nombre del producto.
    2. MM  — se usa el subtipo más frecuente en la misma categoría, o "01".
    3. NNN — máximo NNN en esa CC+MM + 1 (nuevo modelo).
    4. VV  — "01" (primera variante del modelo nuevo).
    5. T   — dígito correspondiente a la talla seleccionada.
    """
    cc = detectar_categoria(nombre)
    t_digit = _talla_a_digito(talla)

    # Filtrar códigos de 10 dígitos de la misma categoría
    codigos_cat = _codigos_de_categoria(productos_existentes, cc)

    # MM más frecuente en la categoría
    mm = _mm_mas_frecuente(codigos_cat) or "01"

    # Códigos del mismo CC+MM
    codigos_ccmm = [c for c in codigos_cat if c[2:4] == mm]

    # Siguiente NNN
    nnn_max = 0
    for cod in codigos_ccmm:
        try:
            nnn_max = max(nnn_max, int(cod[4:7]))
        except (ValueError, IndexError):
            pass
    nnn = str(nnn_max + 1).zfill(3)

    return f"{cc}{mm}{nnn}01{t_digit}"


def codigo_para_variante_existente(
    codigo_base: str,
    talla: str,
    productos_existentes: list,
) -> str:
    """
    Dado el código de un producto ya existente (mismo modelo, otra talla),
    genera un nuevo código con la siguiente VV disponible y el dígito T correcto.
    Útil cuando el nuevo producto es el mismo artículo en otra talla/color.
    """
    if len(codigo_base) != 10:
        return generar_codigo_barras_auto("", talla, productos_existentes)

    cc  = codigo_base[:2]
    mm  = codigo_base[2:4]
    nnn = codigo_base[4:7]
    t_digit = _talla_a_digito(talla)

    # Buscar mayor VV con ese CC+MM+NNN
    codigos_modelo = _codigos_de_modelo(productos_existentes, cc, mm, nnn)
    vv_max = 0
    for cod in codigos_modelo:
        try:
            vv_max = max(vv_max, int(cod[7:9]))
        except (ValueError, IndexError):
            pass
    vv = str(vv_max + 1).zfill(2)

    return f"{cc}{mm}{nnn}{vv}{t_digit}"


# ── Helpers privados ──────────────────────────────────────────────────────────

def _talla_a_digito(talla: str) -> str:
    return _TALLA_DIGITO.get(talla.lower().strip(), "0")


def _codigos_validos(productos: list) -> list[str]:
    """Extrae códigos de barras de 10 dígitos numéricos de la lista de productos."""
    result = []
    for p in productos:
        cod = str(getattr(p, "codigo_barras", "") or "").strip()
        if len(cod) == 10 and cod.isdigit():
            result.append(cod)
    return result


def _codigos_de_categoria(productos: list, cc: str) -> list[str]:
    return [c for c in _codigos_validos(productos) if c[:2] == cc]


def _codigos_de_modelo(productos: list, cc: str, mm: str, nnn: str) -> list[str]:
    prefix = cc + mm + nnn
    return [c for c in _codigos_validos(productos) if c[:7] == prefix]


def _mm_mas_frecuente(codigos: list[str]) -> str | None:
    if not codigos:
        return None
    freq: dict[str, int] = {}
    for cod in codigos:
        mm = cod[2:4]
        freq[mm] = freq.get(mm, 0) + 1
    return max(freq, key=freq.__getitem__)
