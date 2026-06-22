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
    comision_bold: float = 0.0          # Guardado para compatibilidad histórica
    comision_addi: float = 0.0          # Porcentaje ej: 5.0
    comision_transferencia: float = 0.0 # Fallback genérico de transferencia
    comision_nequi: float = 0.0         # Transferencia NEQUI
    comision_nu: float = 0.0            # Transferencia NU
    comision_qr: float = 0.0            # Transferencia QR / Bancolombia
    comision_daviplata: float = 0.0     # Transferencia DAVIPLATA
    comision_datafono: float = 0.0      # Datafono (Tarjeta Débito / Crédito) — cae en cuenta NU
    clave_inventario: str = "YJB2026_*"  # Contraseña para Inventario y Configuración
    nombre_impresora: str = ""           # Nombre Windows de la impresora térmica POS
    modo_oscuro: bool = False            # Tema oscuro activado
    timeout_minutos: int = 10            # Minutos de inactividad antes de bloquear sesión
    backup_automatico_activo: bool = True  # Backup periódico mientras la app está abierta
    backup_intervalo_horas: int = 24       # Cada cuántas horas se ejecuta el backup periódico

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
        """Retorna el porcentaje de comisión según el método de pago."""
        m = (metodo_pago or "").strip().lower()
        if m == "bold":
            return self.comision_bold
        if m == "addi":
            return self.comision_addi
        if m.startswith("datafono"):
            return self.comision_datafono
        if m == "transferencia nequi":
            return self.comision_nequi
        if m == "transferencia nu":
            return self.comision_nu
        if m in ("transferencia qr", "transferencia qr / bancolombia"):
            return self.comision_qr
        if m == "transferencia daviplata":
            return self.comision_daviplata
        if m.startswith("transferencia"):
            return self.comision_transferencia
        return 0.0
