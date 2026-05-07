"""
models/configuracion.py
Modelo de dominio para la configuración de gastos operativos.
Singleton lógico — solo existe una fila en la BD.
"""

from dataclasses import dataclass


@dataclass
class Configuracion:
    """Parámetros de gastos fijos mensuales y comisiones por método de pago."""

    arriendo: float = 0.0          # COP/mes
    sueldo: float = 0.0            # COP/mes
    servicios: float = 0.0         # COP/mes (agua, luz, internet, etc.)
    otros_gastos: float = 0.0      # COP/mes (misceláneos)
    dias_mes: int = 30             # Días para repartir el gasto diario
    comision_bold: float = 0.0     # Guardado para compatibilidad histórica
    comision_addi: float = 0.0     # Porcentaje ej: 5.0
    comision_transferencia: float = 0.0  # Porcentaje (normalmente 0)
    clave_inventario: str = "YJB2026_*"  # Contraseña para Inventario y Configuración
    nombre_impresora: str = ""           # Nombre Windows de la impresora térmica POS

    # ------------------------------------------------------------------
    # Propiedades derivadas
    # ------------------------------------------------------------------

    @property
    def total_gastos_mes(self) -> float:
        """Suma de todos los gastos fijos mensuales."""
        return self.arriendo + self.sueldo + self.servicios + self.otros_gastos

    @property
    def gasto_diario(self) -> float:
        """Gasto operativo prorrateado por día."""
        if self.dias_mes <= 0:
            return 0.0
        return self.total_gastos_mes / self.dias_mes

    def porcentaje_para(self, metodo_pago: str) -> float:
        """
        Retorna el porcentaje de comisión según el método de pago.
        Admite sub-tipos de transferencia: "Transferencia NEQUI" → usa comision_transferencia.
        """
        key = metodo_pago.lower().split()[0] if metodo_pago else ""
        mapping = {
            "bold": self.comision_bold,
            "addi": self.comision_addi,
            "transferencia": self.comision_transferencia,
            "efectivo": 0.0,
            "otro": 0.0,
        }
        return mapping.get(key, 0.0)
