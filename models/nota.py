from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Nota:
    texto: str
    tipo: str                  # "resurtido" | "tarea"
    completado: bool = False
    fecha_creacion: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    id: int | None = None
