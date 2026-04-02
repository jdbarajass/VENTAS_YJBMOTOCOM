"""
Modelos de datos para el sistema de rentabilidad.
Define las estructuras de datos utilizadas en la aplicación.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Venta:
    """
    Modelo que representa una venta individual.
    """
    id: Optional[int] = None
    fecha: date = field(default_factory=date.today)
    producto: str = ""
    costo: float = 0.0
    precio_venta: float = 0.0
    metodo_pago: str = "Efectivo"
    comision: float = 0.0
    ganancia_bruta: float = 0.0
    ganancia_neta: float = 0.0
    notas: str = ""
    created_at: Optional[datetime] = None

    def calcular_ganancias(self, porcentaje_comision: float = 0.0) -> None:
        """
        Calcula la ganancia bruta, comisión y ganancia neta de la venta.

        Args:
            porcentaje_comision: Porcentaje de comisión a aplicar (ej: 5.11 para Bold)
        """
        # Ganancia bruta = Precio de venta - Costo
        self.ganancia_bruta = self.precio_venta - self.costo

        # Calcular comisión sobre el precio de venta
        if porcentaje_comision > 0:
            self.comision = self.precio_venta * (porcentaje_comision / 100)
        else:
            self.comision = 0.0

        # Ganancia neta = Ganancia bruta - Comisión
        self.ganancia_neta = self.ganancia_bruta - self.comision

    def to_dict(self) -> dict:
        """Convierte la venta a diccionario."""
        return {
            "id": self.id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "producto": self.producto,
            "costo": self.costo,
            "precio_venta": self.precio_venta,
            "metodo_pago": self.metodo_pago,
            "comision": self.comision,
            "ganancia_bruta": self.ganancia_bruta,
            "ganancia_neta": self.ganancia_neta,
            "notas": self.notas,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Venta":
        """Crea una instancia de Venta desde un diccionario."""
        return cls(
            id=data.get("id"),
            fecha=date.fromisoformat(data["fecha"]) if data.get("fecha") else date.today(),
            producto=data.get("producto", ""),
            costo=float(data.get("costo", 0)),
            precio_venta=float(data.get("precio_venta", 0)),
            metodo_pago=data.get("metodo_pago", "Efectivo"),
            comision=float(data.get("comision", 0)),
            ganancia_bruta=float(data.get("ganancia_bruta", 0)),
            ganancia_neta=float(data.get("ganancia_neta", 0)),
            notas=data.get("notas", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )


@dataclass
class Configuracion:
    """
    Modelo para la configuración del negocio.
    """
    id: int = 1
    arriendo: float = 3_000_000
    sueldo: float = 2_000_000
    servicios: float = 300_000
    comision_bold: float = 5.11
    dias_mes: int = 30

    @property
    def total_gastos(self) -> float:
        """Calcula el total de gastos fijos mensuales."""
        return self.arriendo + self.sueldo + self.servicios

    @property
    def gasto_diario(self) -> float:
        """Calcula el gasto operativo diario."""
        return self.total_gastos / self.dias_mes

    def to_dict(self) -> dict:
        """Convierte la configuración a diccionario."""
        return {
            "id": self.id,
            "arriendo": self.arriendo,
            "sueldo": self.sueldo,
            "servicios": self.servicios,
            "comision_bold": self.comision_bold,
            "dias_mes": self.dias_mes,
            "total_gastos": self.total_gastos,
            "gasto_diario": self.gasto_diario
        }


@dataclass
class ResumenDiario:
    """
    Modelo para el resumen de ventas de un día.
    """
    fecha: date
    total_ventas: float = 0.0
    total_costos: float = 0.0
    ganancia_bruta: float = 0.0
    total_comisiones: float = 0.0
    gasto_operativo: float = 0.0
    utilidad_real: float = 0.0
    num_ventas: int = 0
    ventas_efectivo: float = 0.0
    ventas_bold: float = 0.0
    ventas_transferencia: float = 0.0

    @property
    def meta_cubierta(self) -> bool:
        """Indica si el gasto operativo del día fue cubierto."""
        return self.utilidad_real >= 0

    @property
    def faltante_meta(self) -> float:
        """Cuánto falta para cubrir el gasto operativo (0 si ya se cubrió)."""
        if self.utilidad_real >= 0:
            return 0.0
        return abs(self.utilidad_real)


@dataclass
class ResumenMensual:
    """
    Modelo para el resumen de ventas de un mes.
    """
    anio: int
    mes: int
    total_ventas: float = 0.0
    total_costos: float = 0.0
    ganancia_bruta: float = 0.0
    total_comisiones: float = 0.0
    total_gastos_operativos: float = 0.0
    utilidad_real: float = 0.0
    num_ventas: int = 0
    dias_positivos: int = 0
    dias_negativos: int = 0
    mejor_dia: Optional[date] = None
    mejor_dia_utilidad: float = 0.0
    peor_dia: Optional[date] = None
    peor_dia_utilidad: float = 0.0

    @property
    def nombre_mes(self) -> str:
        """Retorna el nombre del mes en español."""
        meses = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        return meses[self.mes - 1]

    @property
    def periodo(self) -> str:
        """Retorna el periodo formateado (ej: 'Abril 2026')."""
        return f"{self.nombre_mes} {self.anio}"
