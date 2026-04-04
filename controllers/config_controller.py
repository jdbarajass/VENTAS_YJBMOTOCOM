"""
controllers/config_controller.py
Caso de uso: leer y guardar la configuración operativa.
"""

from models.configuracion import Configuracion
from database.config_repo import obtener_configuracion, guardar_configuracion


class ConfigController:

    def cargar(self) -> Configuracion:
        """Retorna la configuración activa desde la BD."""
        return obtener_configuracion()

    def guardar(self, cfg: Configuracion) -> None:
        """
        Valida y persiste la configuración.
        Lanza ValueError si algún valor es inválido.
        """
        self._validar(cfg)
        guardar_configuracion(cfg)

    @staticmethod
    def _validar(cfg: Configuracion) -> None:
        if cfg.arriendo < 0:
            raise ValueError("El arriendo no puede ser negativo.")
        if cfg.sueldo < 0:
            raise ValueError("El sueldo no puede ser negativo.")
        if cfg.servicios < 0:
            raise ValueError("Los servicios no pueden ser negativos.")
        if cfg.otros_gastos < 0:
            raise ValueError("Los otros gastos no pueden ser negativos.")
        if not (1 <= cfg.dias_mes <= 31):
            raise ValueError("Los días del mes deben estar entre 1 y 31.")
        for nombre, val in [
            ("Bold", cfg.comision_bold),
            ("Addi", cfg.comision_addi),
            ("Transferencia", cfg.comision_transferencia),
        ]:
            if not (0 <= val <= 100):
                raise ValueError(f"La comisión de {nombre} debe estar entre 0 y 100 %.")
