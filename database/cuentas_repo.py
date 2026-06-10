"""
database/cuentas_repo.py
CRUD para el sistema de Cuentas.
"""

import json
from datetime import date, datetime
from database.connection import DatabaseConnection
from models.cuenta import Cuenta, MovimientoCuenta, CierreMensual
from utils.logger import log


# ── Cuentas ───────────────────────────────────────────────────────────────────

def obtener_todas() -> list[Cuenta]:
    """Retorna todas las cuentas activas ordenadas por su campo orden."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, nombre, metodo_pago, balance_actual, color, activa, orden "
        "FROM cuentas ORDER BY orden, id"
    ).fetchall()
    return [_row_to_cuenta(r) for r in rows]


def obtener_todas_incluyendo_inactivas() -> list[Cuenta]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, nombre, metodo_pago, balance_actual, color, activa, orden "
        "FROM cuentas ORDER BY orden, id"
    ).fetchall()
    return [_row_to_cuenta(r) for r in rows]


def obtener_por_id(cuenta_id: int) -> Cuenta | None:
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT id, nombre, metodo_pago, balance_actual, color, activa, orden "
        "FROM cuentas WHERE id = ?", (cuenta_id,)
    ).fetchone()
    return _row_to_cuenta(row) if row else None


def obtener_por_metodo_pago(metodo: str) -> Cuenta | None:
    """Busca la cuenta cuyo metodo_pago coincide exactamente con el string dado."""
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT id, nombre, metodo_pago, balance_actual, color, activa, orden "
        "FROM cuentas WHERE metodo_pago = ? AND activa = 1",
        (metodo,)
    ).fetchone()
    return _row_to_cuenta(row) if row else None


def actualizar_balance_manual(cuenta_id: int, nuevo_balance: float,
                               descripcion: str = "Ajuste manual", usuario: str = "") -> None:
    """
    Establece el saldo de una cuenta directamente y registra el cambio como ajuste_manual.
    El movimiento almacena la diferencia (delta) para mantener el historial coherente.
    """
    conn = DatabaseConnection.get()
    balance_anterior = conn.execute(
        "SELECT balance_actual FROM cuentas WHERE id = ?", (cuenta_id,)
    ).fetchone()[0]
    delta = nuevo_balance - balance_anterior
    conn.execute(
        "UPDATE cuentas SET balance_actual = ? WHERE id = ?",
        (round(nuevo_balance, 2), cuenta_id)
    )
    _registrar_movimiento(conn, cuenta_id, "ajuste_manual", delta,
                          descripcion or "Ajuste manual")
    conn.commit()
    log.info("Balance cuenta %d ajustado: %.2f → %.2f", cuenta_id, balance_anterior, nuevo_balance)


def registrar_transferencia(desde_id: int, hasta_id: int, monto: float,
                             descripcion: str = "") -> None:
    """Transfiere monto de una cuenta a otra, registrando ambos movimientos."""
    if monto <= 0:
        raise ValueError("El monto de la transferencia debe ser positivo.")
    conn = DatabaseConnection.get()
    desde = obtener_por_id(desde_id)
    hasta = obtener_por_id(hasta_id)
    if not desde or not hasta:
        raise ValueError("Una de las cuentas no existe.")
    if desde.balance_actual < monto:
        raise ValueError(
            f"Saldo insuficiente en '{desde.nombre}'. "
            f"Disponible: {desde.balance_actual:,.0f}"
        )
    desc_base = descripcion or f"Transferencia {desde.nombre} → {hasta.nombre}"
    conn.execute(
        "UPDATE cuentas SET balance_actual = balance_actual - ? WHERE id = ?",
        (round(monto, 2), desde_id)
    )
    conn.execute(
        "UPDATE cuentas SET balance_actual = balance_actual + ? WHERE id = ?",
        (round(monto, 2), hasta_id)
    )
    _registrar_movimiento(conn, desde_id, "transferencia_salida", -monto,
                          f"→ {hasta.nombre}: {desc_base}")
    _registrar_movimiento(conn, hasta_id, "transferencia_entrada", monto,
                          f"← {desde.nombre}: {desc_base}")
    conn.commit()
    log.info("Transferencia %.2f: cuenta %d → %d", monto, desde_id, hasta_id)


# ── Auto-crédito desde ventas ────────────────────────────────────────────────

def acreditar_venta(venta) -> None:
    """
    Acredita el importe de una venta a la(s) cuenta(s) correspondiente(s).
    Silencioso si el metodo_pago no tiene cuenta asociada (e.g. 'Otro').
    """
    conn = DatabaseConnection.get()
    try:
        if venta.metodo_pago == "Combinado" and venta.pagos_combinados:
            for pago in venta.pagos_combinados:
                _acreditar_un_pago(conn, pago["metodo"], pago["monto"],
                                   venta.id, venta.fecha)
        elif venta.metodo_pago not in ("Otro", "Combinado"):
            _acreditar_un_pago(conn, venta.metodo_pago, venta.precio * venta.cantidad,
                               venta.id, venta.fecha)
        conn.commit()
    except Exception as exc:
        log.warning("No se pudo acreditar venta %s a cuentas: %s", venta.id, exc)


def _acreditar_un_pago(conn, metodo: str, monto: float, venta_id, fecha) -> None:
    row = conn.execute(
        "SELECT id FROM cuentas WHERE metodo_pago = ? AND activa = 1", (metodo,)
    ).fetchone()
    if not row:
        return
    cuenta_id = row[0]
    conn.execute(
        "UPDATE cuentas SET balance_actual = balance_actual + ? WHERE id = ?",
        (round(monto, 2), cuenta_id)
    )
    fecha_str = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)
    conn.execute(
        """INSERT INTO cuentas_movimientos
           (cuenta_id, fecha, tipo, monto, descripcion, venta_id)
           VALUES (?, ?, 'venta', ?, 'Ingreso por venta', ?)""",
        (cuenta_id, fecha_str, round(monto, 2), venta_id)
    )


# ── Movimientos ───────────────────────────────────────────────────────────────

def obtener_movimientos(
    cuenta_id: int | None = None,
    desde: str | None = None,
    hasta: str | None = None,
    limite: int = 200,
) -> list[MovimientoCuenta]:
    conn = DatabaseConnection.get()
    conds, params = [], []
    if cuenta_id is not None:
        conds.append("cuenta_id = ?")
        params.append(cuenta_id)
    if desde:
        conds.append("fecha >= ?")
        params.append(desde)
    if hasta:
        conds.append("fecha <= ?")
        params.append(hasta)
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    params.append(limite)
    rows = conn.execute(
        f"SELECT id, cuenta_id, fecha, tipo, monto, descripcion, venta_id "
        f"FROM cuentas_movimientos {where} ORDER BY fecha DESC, id DESC LIMIT ?",
        params
    ).fetchall()
    return [MovimientoCuenta(
        id=r[0], cuenta_id=r[1], fecha=r[2], tipo=r[3],
        monto=r[4], descripcion=r[5] or "", venta_id=r[6]
    ) for r in rows]


def _registrar_movimiento(conn, cuenta_id: int, tipo: str, monto: float,
                           descripcion: str = "") -> None:
    hoy = date.today().isoformat()
    conn.execute(
        """INSERT INTO cuentas_movimientos (cuenta_id, fecha, tipo, monto, descripcion)
           VALUES (?, ?, ?, ?, ?)""",
        (cuenta_id, hoy, tipo, round(monto, 2), descripcion)
    )


# ── Cierres mensuales ─────────────────────────────────────────────────────────

def hacer_cierre_mes(anio: int, mes: int, notas: str = "") -> CierreMensual:
    """
    Toma un snapshot de todos los saldos actuales y lo guarda como cierre del mes.
    Si ya existe un cierre para ese mes/año lo sobreescribe.
    """
    conn = DatabaseConnection.get()
    cuentas = obtener_todas()
    datos = [
        {"cuenta_id": c.id, "nombre": c.nombre, "balance": c.balance_actual}
        for c in cuentas
    ]
    datos_json = json.dumps(datos, ensure_ascii=False)
    fecha_cierre = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute(
        """INSERT INTO cuentas_cierres (anio, mes, datos_json, notas, fecha_cierre)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(anio, mes) DO UPDATE SET
               datos_json = excluded.datos_json,
               notas = excluded.notas,
               fecha_cierre = excluded.fecha_cierre""",
        (anio, mes, datos_json, notas, fecha_cierre)
    )
    conn.commit()
    cierre_id = conn.execute(
        "SELECT id FROM cuentas_cierres WHERE anio = ? AND mes = ?", (anio, mes)
    ).fetchone()[0]
    log.info("Cierre mensual %d/%d realizado (id=%d)", mes, anio, cierre_id)
    return CierreMensual(id=cierre_id, anio=anio, mes=mes,
                         datos_json=datos_json, notas=notas,
                         fecha_cierre=fecha_cierre)


def obtener_cierres() -> list[CierreMensual]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, anio, mes, datos_json, notas, fecha_cierre "
        "FROM cuentas_cierres ORDER BY anio DESC, mes DESC"
    ).fetchall()
    return [CierreMensual(id=r[0], anio=r[1], mes=r[2],
                          datos_json=r[3], notas=r[4] or "",
                          fecha_cierre=r[5]) for r in rows]


# ── Utilitarios ───────────────────────────────────────────────────────────────

def _row_to_cuenta(row) -> Cuenta:
    return Cuenta(
        id=row[0], nombre=row[1], metodo_pago=row[2],
        balance_actual=row[3], color=row[4],
        activa=bool(row[5]), orden=row[6]
    )
