"""
utils/formatters.py
Formateadores de presentación — usados por la UI para mostrar valores.
Sin dependencias de PySide6 para poder testearlos independientemente.
"""

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def cop(valor: float) -> str:
    """
    Formatea un valor como pesos colombianos.
    Ejemplo: 1200000 -> '$ 1.200.000'
    """
    try:
        entero = int(round(valor))
        negativo = entero < 0
        texto = f"{abs(entero):,}".replace(",", ".")
        return f"- $ {texto}" if negativo else f"$ {texto}"
    except (TypeError, ValueError):
        return "$ 0"


def porcentaje(valor: float, decimales: int = 2) -> str:
    """Formatea un valor como porcentaje. Ejemplo: 3.49 -> '3.49 %'"""
    return f"{valor:.{decimales}f} %"


def nombre_mes(mes: int, año: int) -> str:
    """Ejemplo: nombre_mes(4, 2026) -> 'Abril 2026'"""
    return f"{MESES_ES.get(mes, str(mes))} {año}"


def fecha_corta(d) -> str:
    """date -> 'dd/mm/aaaa'"""
    return d.strftime("%d/%m/%Y")
