from dataclasses import dataclass, field
from datetime import datetime, date


@dataclass
class Nota:
    texto: str
    tipo: str                  # "resurtido" | "tarea"
    completado: bool = False
    fecha_creacion: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    id: int | None = None
    fecha_limite: str | None = None   # YYYY-MM-DD, opcional

    @property
    def vencida(self) -> bool:
        """True si tiene fecha_limite, no está completada y ya pasó."""
        if self.completado or not self.fecha_limite:
            return False
        try:
            return date.fromisoformat(self.fecha_limite) < date.today()
        except ValueError:
            return False

    @property
    def dias_restantes(self) -> int | None:
        """Días hasta fecha_limite (negativo si vencida). None si no tiene límite."""
        if not self.fecha_limite:
            return None
        try:
            return (date.fromisoformat(self.fecha_limite) - date.today()).days
        except ValueError:
            return None
