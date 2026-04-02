"""
Configuración global del sistema YJBMOTOCOM - Control de Rentabilidad
Todos los valores monetarios están en Pesos Colombianos (COP)
"""

import os
from pathlib import Path

# =============================================================================
# RUTAS DEL SISTEMA
# =============================================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"

# Crear directorio de datos si no existe
DATA_DIR.mkdir(exist_ok=True)

# Ruta de la base de datos
DATABASE_PATH = DATA_DIR / "ventas.db"

# =============================================================================
# CONFIGURACIÓN DE GASTOS FIJOS MENSUALES (COP)
# =============================================================================
GASTOS_FIJOS = {
    "arriendo": 3_000_000,
    "sueldo_empleada": 2_000_000,
    "servicios": 300_000,
}

# Total de gastos fijos mensuales
TOTAL_GASTOS_MENSUALES = sum(GASTOS_FIJOS.values())  # = 5,300,000 COP

# Días del mes para cálculo de gasto diario
DIAS_MES = 30

# Gasto operativo diario = 5,300,000 / 30 = 176,666.67 COP
GASTO_OPERATIVO_DIARIO = TOTAL_GASTOS_MENSUALES / DIAS_MES

# =============================================================================
# CONFIGURACIÓN DE COMISIONES
# =============================================================================
COMISIONES = {
    "Bold": 5.11,        # Porcentaje de comisión Bold
    "Efectivo": 0.0,     # Sin comisión
    "Transferencia": 0.0  # Sin comisión
}

# =============================================================================
# MÉTODOS DE PAGO DISPONIBLES
# =============================================================================
METODOS_PAGO = ["Efectivo", "Bold", "Transferencia"]

# =============================================================================
# CONFIGURACIÓN DE LA INTERFAZ
# =============================================================================
APP_NAME = "YJBMOTOCOM - Control de Rentabilidad"
APP_VERSION = "1.0.0"

# Dimensiones de la ventana
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 700

# =============================================================================
# FORMATO DE MONEDA
# =============================================================================
MONEDA_SIMBOLO = "$"
MONEDA_CODIGO = "COP"
SEPARADOR_MILES = "."
SEPARADOR_DECIMAL = ","

def formatear_moneda(valor: float) -> str:
    """
    Formatea un valor numérico como moneda colombiana.
    Ejemplo: 1500000 -> "$1.500.000"
    """
    if valor < 0:
        signo = "-"
        valor = abs(valor)
    else:
        signo = ""

    # Formatear con separador de miles
    valor_str = f"{valor:,.0f}".replace(",", ".")
    return f"{signo}{MONEDA_SIMBOLO}{valor_str}"

def formatear_porcentaje(valor: float) -> str:
    """
    Formatea un valor como porcentaje.
    Ejemplo: 5.11 -> "5,11%"
    """
    return f"{valor:.2f}%".replace(".", ",")

# =============================================================================
# COLORES DE LA INTERFAZ
# =============================================================================
COLORES = {
    "positivo": "#27ae60",      # Verde - ganancia
    "negativo": "#e74c3c",      # Rojo - pérdida
    "neutro": "#3498db",        # Azul - neutral
    "advertencia": "#f39c12",   # Naranja - advertencia
    "fondo": "#f5f6fa",         # Gris claro - fondo
    "fondo_card": "#ffffff",    # Blanco - tarjetas
    "texto": "#2c3e50",         # Gris oscuro - texto
    "texto_secundario": "#7f8c8d",  # Gris - texto secundario
    "borde": "#dcdde1",         # Gris claro - bordes
    "header": "#2c3e50",        # Azul oscuro - encabezados
}
