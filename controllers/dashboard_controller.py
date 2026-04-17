"""
controllers/dashboard_controller.py
Caso de uso: obtener el resumen contable de un día para el dashboard.
"""

from collections import defaultdict
from datetime import date

from database.ventas_repo import obtener_ventas_por_fecha, obtener_ventas_por_mes
from database.gastos_dia_repo import obtener_gastos_por_fecha, obtener_gastos_por_mes
from database.config_repo import obtener_configuracion
from database.prestamos_repo import obtener_prestamos_pendientes
from database.facturas_repo import obtener_facturas_pendientes
from services.reportes import calcular_resumen_diario, ResumenDiario


def _expandir_metodos(ventas: list) -> dict:
    """
    Devuelve {metodo: total_ingresos} expandiendo pagos combinados.
    - Venta simple: acumula por v.metodo_pago (ej. "Transferencia NEQUI")
    - Venta combinada: acumula por cada entrada de pagos_combinados
    Nunca aparece "Combinado" como clave — siempre se expande a los metodos reales.
    """
    totales: dict[str, float] = defaultdict(float)
    for v in ventas:
        if v.pagos_combinados:
            for pago in v.pagos_combinados:
                totales[pago["metodo"]] += pago["monto"]
        else:
            totales[v.metodo_pago] += v.precio * v.cantidad
    return dict(totales)


class DashboardController:

    def get_datos_dia(self, fecha: date) -> dict:
        """
        Carga y calcula todo lo necesario para el dashboard de un día.
        Retorna un dict con:
          resumen    — ResumenDiario
          proyeccion — dict de proyección mensual
          por_metodo — {metodo: total_ingresos}
          productos  — [(nombre, cant, ingresos, ganancia), ...] ordenado por ingreso desc
          alertas    — {"prestamos": N, "facturas": N, "total_facturas": float}
        """
        ventas  = obtener_ventas_por_fecha(fecha)
        gastos  = obtener_gastos_por_fecha(fecha)
        gastos_total = round(sum(g.monto for g in gastos), 2)
        cfg     = obtener_configuracion()

        resumen = calcular_resumen_diario(ventas, cfg, fecha, gastos_total)

        # ── Desglose por método de pago (expandiendo pagos combinados) ──
        por_metodo = _expandir_metodos(ventas)

        # ── Productos vendidos ────────────────────────────────────────
        prods: dict[str, dict] = defaultdict(lambda: {"cant": 0, "ing": 0.0, "gan": 0.0})
        for v in ventas:
            prods[v.producto]["cant"] += v.cantidad
            prods[v.producto]["ing"]  += v.precio * v.cantidad
            prods[v.producto]["gan"]  += v.ganancia_neta
        productos = sorted(
            [(n, d["cant"], d["ing"], d["gan"]) for n, d in prods.items()],
            key=lambda x: x[2], reverse=True,
        )

        # ── Proyección mensual ────────────────────────────────────────
        proyeccion = self._get_proyeccion_mes(fecha, cfg)

        # ── Alertas rápidas ───────────────────────────────────────────
        prest_pend     = obtener_prestamos_pendientes()
        fact_pend      = obtener_facturas_pendientes()
        fact_vencidas  = [f for f in fact_pend if f.dias_para_vencer is not None
                          and f.dias_para_vencer < 0]
        prest_urgentes = [p for p in prest_pend if (fecha - p.fecha).days > 30]
        alertas = {
            "prestamos":           len(prest_pend),
            "facturas":            len(fact_pend),
            "total_facturas":      sum(f.monto for f in fact_pend),
            "facturas_vencidas":   len(fact_vencidas),
            "total_vencidas":      sum(f.monto for f in fact_vencidas),
            "prestamos_urgentes":  len(prest_urgentes),
        }

        return {
            "resumen":    resumen,
            "por_metodo": dict(por_metodo),
            "productos":  productos,
            "proyeccion": proyeccion,
            "alertas":    alertas,
        }

    def _get_proyeccion_mes(self, fecha: date, cfg=None) -> dict:
        if cfg is None:
            cfg = obtener_configuracion()

        ventas_mes       = obtener_ventas_por_mes(fecha.year, fecha.month)
        ventas_hasta     = [v for v in ventas_mes if v.fecha <= fecha]
        gastos_mes       = obtener_gastos_por_mes(fecha.year, fecha.month)
        gastos_extra     = round(sum(g.monto for g in gastos_mes if g.fecha <= fecha), 2)
        ganancia_acum    = round(sum(v.ganancia_neta for v in ventas_hasta), 2)
        utilidad_acum    = round(ganancia_acum - gastos_extra, 2)
        meta             = round(cfg.gasto_diario * fecha.day, 2)

        # ── Comisiones por plataforma acumuladas en el mes ────────────
        comisiones_plataforma: dict[str, float] = {}
        for v in ventas_hasta:
            if v.comision > 0:
                # Para pagos simples usar metodo_pago directo; para combinados
                # distribuir proporcionalmente (la comision ya esta calculada en total)
                metodo = v.metodo_pago if v.metodo_pago != "Combinado" else "Combinado"
                comisiones_plataforma[metodo] = round(
                    comisiones_plataforma.get(metodo, 0.0) + v.comision, 2
                )

        return {
            "dia":                       fecha.day,
            "dias_mes":                  cfg.dias_mes,
            "gasto_diario":              cfg.gasto_diario,
            "meta":                      meta,
            "ganancia_acumulada":        ganancia_acum,
            "gastos_extra_acumulados":   gastos_extra,
            "utilidad_acumulada":        utilidad_acum,
            "diferencia":                round(utilidad_acum - meta, 2),
            "comisiones_plataforma":     comisiones_plataforma,
        }

    # ── Método legado mantenido por compatibilidad ────────────────────
    def get_resumen_dia(self, fecha: date) -> ResumenDiario:
        return self.get_datos_dia(fecha)["resumen"]

    def get_proyeccion_mes(self, fecha: date) -> dict:
        return self._get_proyeccion_mes(fecha)
