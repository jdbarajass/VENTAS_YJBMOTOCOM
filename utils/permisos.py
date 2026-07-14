"""
utils/permisos.py
Reglas de visibilidad de datos financieros según el rol del usuario.

Los vendedores no deben ver el costo real de los productos ni la ganancia/
margen de las ventas. En vez de ocultar el costo por completo, se les
muestra un costo ficticio (costo real + 30%) para que sigan teniendo una
referencia al armar precios.
"""

MARKUP_COSTO_VENDEDOR = 1.30


def es_vendedor(rol: str) -> bool:
    return rol == "vendedor"


def costo_mostrado(costo_real: float, rol: str) -> float:
    """Costo a mostrar en UI: real para admin, inflado un 30% para vendedor."""
    return costo_real * MARKUP_COSTO_VENDEDOR if es_vendedor(rol) else costo_real
