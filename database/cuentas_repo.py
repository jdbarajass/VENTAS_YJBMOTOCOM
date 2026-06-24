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
            _acreditar_un_pago(conn, venta.metodo_pago, venta.ingreso_real(),
                               venta.id, venta.fecha)
        conn.commit()
    except Exception as exc:
        log.warning("No se pudo acreditar venta %s a cuentas: %s", venta.id, exc)


def _acreditar_un_pago(conn, metodo: str, monto: float, venta_id, fecha) -> None:
    # Datafono (Tarjeta Débito/Crédito) cae en la cuenta NU
    metodo_lookup = "Transferencia NU" if metodo.startswith("Datafono") else metodo
    row = conn.execute(
        "SELECT id FROM cuentas WHERE metodo_pago = ? AND activa = 1", (metodo_lookup,)
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


def revertir_credito_venta(venta) -> None:
    """
    Revierte el crédito que acreditar_venta() aplicó cuando se elimina una venta.
    Silencioso si el método de pago no tiene cuenta asociada.
    """
    conn = DatabaseConnection.get()
    try:
        if venta.metodo_pago == "Combinado" and venta.pagos_combinados:
            for pago in venta.pagos_combinados:
                _revertir_un_pago(conn, pago["metodo"], pago["monto"],
                                  venta.id, venta.fecha)
        elif venta.metodo_pago not in ("Otro", "Combinado"):
            _revertir_un_pago(conn, venta.metodo_pago, venta.ingreso_real(),
                              venta.id, venta.fecha)
        conn.commit()
    except Exception as exc:
        log.warning("No se pudo revertir crédito de venta %s: %s", venta.id, exc)


def _revertir_un_pago(conn, metodo: str, monto: float, venta_id, fecha) -> None:
    # Datafono (Tarjeta Débito/Crédito) cae en la cuenta NU
    metodo_lookup = "Transferencia NU" if metodo.startswith("Datafono") else metodo
    row = conn.execute(
        "SELECT id FROM cuentas WHERE metodo_pago = ? AND activa = 1", (metodo_lookup,)
    ).fetchone()
    if not row:
        return
    cuenta_id = row[0]
    conn.execute(
        "UPDATE cuentas SET balance_actual = balance_actual - ? WHERE id = ?",
        (round(monto, 2), cuenta_id)
    )
    fecha_str = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)
    conn.execute(
        """INSERT INTO cuentas_movimientos
           (cuenta_id, fecha, tipo, monto, descripcion, venta_id)
           VALUES (?, ?, 'reversa_venta', ?, 'Reversa: venta eliminada', ?)""",
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


# ── Débito/crédito por gastos operativos ────────────────────────────────────

def debitar_gasto(gasto) -> None:
    """
    Descuenta el monto de un gasto operativo de la cuenta indicada en gasto.cuenta_pago.
    Silencioso si la cuenta no existe o cuenta_pago está vacío.
    """
    cuenta_nombre = getattr(gasto, "cuenta_pago", "") or ""
    if not cuenta_nombre:
        return
    conn = DatabaseConnection.get()
    try:
        row = conn.execute(
            "SELECT id FROM cuentas WHERE nombre = ? AND activa = 1", (cuenta_nombre,)
        ).fetchone()
        if not row:
            return
        cuenta_id = row[0]
        conn.execute(
            "UPDATE cuentas SET balance_actual = balance_actual - ? WHERE id = ?",
            (round(gasto.monto, 2), cuenta_id)
        )
        fecha_str = gasto.fecha.isoformat() if hasattr(gasto.fecha, "isoformat") else str(gasto.fecha)
        conn.execute(
            """INSERT INTO cuentas_movimientos (cuenta_id, fecha, tipo, monto, descripcion)
               VALUES (?, ?, 'gasto_operativo', ?, ?)""",
            (cuenta_id, fecha_str, -round(gasto.monto, 2),
             gasto.descripcion or "Gasto operativo")
        )
        conn.commit()
        log.info("Gasto debitado de cuenta '%s': %.2f", cuenta_nombre, gasto.monto)
    except Exception as exc:
        log.warning("No se pudo debitar gasto de cuenta '%s': %s", cuenta_nombre, exc)


def revertir_gasto(gasto) -> None:
    """
    Revierte el débito de un gasto eliminado, devolviendo el monto a la cuenta.
    Silencioso si la cuenta no existe.
    """
    cuenta_nombre = getattr(gasto, "cuenta_pago", "") or ""
    if not cuenta_nombre:
        return
    conn = DatabaseConnection.get()
    try:
        row = conn.execute(
            "SELECT id FROM cuentas WHERE nombre = ? AND activa = 1", (cuenta_nombre,)
        ).fetchone()
        if not row:
            return
        cuenta_id = row[0]
        conn.execute(
            "UPDATE cuentas SET balance_actual = balance_actual + ? WHERE id = ?",
            (round(gasto.monto, 2), cuenta_id)
        )
        fecha_str = gasto.fecha.isoformat() if hasattr(gasto.fecha, "isoformat") else str(gasto.fecha)
        conn.execute(
            """INSERT INTO cuentas_movimientos (cuenta_id, fecha, tipo, monto, descripcion)
               VALUES (?, ?, 'reversa_gasto', ?, ?)""",
            (cuenta_id, fecha_str, round(gasto.monto, 2),
             f"Reversión gasto: {gasto.descripcion}")
        )
        conn.commit()
        log.info("Gasto revertido en cuenta '%s': %.2f", cuenta_nombre, gasto.monto)
    except Exception as exc:
        log.warning("No se pudo revertir gasto en cuenta '%s': %s", cuenta_nombre, exc)


# ── Débito/crédito por pagos de facturas ─────────────────────────────────────

def debitar_pago_factura(
    cuenta_id: int, monto: float, factura_id: int | None,
    fecha: "date", descripcion: str = "",
) -> None:
    """
    Debita un pago de factura de la cuenta indicada.
    Silencioso si la cuenta no existe o el monto es cero.
    """
    if monto <= 0:
        return
    conn = DatabaseConnection.get()
    try:
        conn.execute(
            "UPDATE cuentas SET balance_actual = balance_actual - ? WHERE id = ?",
            (round(monto, 2), cuenta_id)
        )
        fecha_str = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)
        conn.execute(
            """INSERT INTO cuentas_movimientos (cuenta_id, fecha, tipo, monto, descripcion)
               VALUES (?, ?, 'pago_factura', ?, ?)""",
            (cuenta_id, fecha_str, -round(monto, 2), descripcion or "Pago de factura")
        )
        conn.commit()
        log.info("Pago factura %s debitado de cuenta %d: %.2f", factura_id, cuenta_id, monto)
    except Exception as exc:
        log.warning("No se pudo debitar pago factura de cuenta %d: %s", cuenta_id, exc)


def revertir_abono_factura(
    cuenta_id: int, monto: float, fecha: "date", descripcion: str = "",
) -> None:
    """Revierte el débito de un abono eliminado, devolviendo el monto a la cuenta."""
    if monto <= 0:
        return
    conn = DatabaseConnection.get()
    try:
        conn.execute(
            "UPDATE cuentas SET balance_actual = balance_actual + ? WHERE id = ?",
            (round(monto, 2), cuenta_id)
        )
        fecha_str = fecha.isoformat() if hasattr(fecha, "isoformat") else str(fecha)
        conn.execute(
            """INSERT INTO cuentas_movimientos (cuenta_id, fecha, tipo, monto, descripcion)
               VALUES (?, ?, 'reversa_abono', ?, ?)""",
            (cuenta_id, fecha_str, round(monto, 2), descripcion or "Reversa abono factura")
        )
        conn.commit()
        log.info("Abono revertido en cuenta %d: %.2f", cuenta_id, monto)
    except Exception as exc:
        log.warning("No se pudo revertir abono en cuenta %d: %s", cuenta_id, exc)


# ── Restauración desde backup (importación masiva) ─────────────────────────────

def actualizar_o_crear_cuenta(c: Cuenta, commit: bool = True) -> int:
    """Upsert por nombre: si ya existe una cuenta con ese nombre, actualiza sus
    datos; si no, la crea. Usado al restaurar un respaldo en Excel."""
    conn = DatabaseConnection.get()
    existente = conn.execute(
        "SELECT id FROM cuentas WHERE nombre = ?", (c.nombre,)
    ).fetchone()
    if existente:
        conn.execute(
            """UPDATE cuentas SET metodo_pago=?, balance_actual=?, color=?,
               activa=?, orden=? WHERE id=?""",
            (c.metodo_pago, c.balance_actual, c.color, int(c.activa), c.orden, existente[0]),
        )
        cuenta_id = existente[0]
    else:
        cursor = conn.execute(
            """INSERT INTO cuentas (nombre, metodo_pago, balance_actual, color, activa, orden)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (c.nombre, c.metodo_pago, c.balance_actual, c.color, int(c.activa), c.orden),
        )
        cuenta_id = cursor.lastrowid
    if commit:
        conn.commit()
    return cuenta_id


def insertar_movimiento_directo(m: MovimientoCuenta, commit: bool = True) -> int:
    """Inserta un movimiento histórico tal cual (sin la lógica de acreditar venta).
    Usado al restaurar un respaldo en Excel."""
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        """INSERT INTO cuentas_movimientos (cuenta_id, fecha, tipo, monto, descripcion, venta_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (m.cuenta_id, m.fecha, m.tipo, m.monto, m.descripcion, m.venta_id),
    )
    if commit:
        conn.commit()
    return cursor.lastrowid


def insertar_cierre_directo(c: CierreMensual, commit: bool = True) -> int:
    """Inserta (o reemplaza) un cierre mensual tal cual viene del respaldo."""
    conn = DatabaseConnection.get()
    conn.execute(
        """INSERT INTO cuentas_cierres (anio, mes, datos_json, notas, fecha_cierre)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(anio, mes) DO UPDATE SET
               datos_json = excluded.datos_json,
               notas = excluded.notas,
               fecha_cierre = excluded.fecha_cierre""",
        (c.anio, c.mes, c.datos_json, c.notas, c.fecha_cierre),
    )
    if commit:
        conn.commit()
    cierre_id = conn.execute(
        "SELECT id FROM cuentas_cierres WHERE anio = ? AND mes = ?", (c.anio, c.mes)
    ).fetchone()[0]
    return cierre_id


def eliminar_todos_movimientos(commit: bool = True) -> int:
    conn = DatabaseConnection.get()
    cursor = conn.execute("DELETE FROM cuentas_movimientos")
    if commit:
        conn.commit()
    return cursor.rowcount


def eliminar_todos_cierres(commit: bool = True) -> int:
    conn = DatabaseConnection.get()
    cursor = conn.execute("DELETE FROM cuentas_cierres")
    if commit:
        conn.commit()
    return cursor.rowcount


# ── Utilitarios ───────────────────────────────────────────────────────────────

def _row_to_cuenta(row) -> Cuenta:
    return Cuenta(
        id=row[0], nombre=row[1], metodo_pago=row[2],
        balance_actual=row[3], color=row[4],
        activa=bool(row[5]), orden=row[6]
    )
