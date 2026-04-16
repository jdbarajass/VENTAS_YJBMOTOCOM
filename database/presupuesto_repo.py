"""
database/presupuesto_repo.py
CRUD para la tabla `presupuesto_mensual`.

Permite asignar un monto presupuestado por categoría de gasto y mes,
luego compararlo con los gastos_dia reales del mismo período.
"""

from database.connection import DatabaseConnection


def obtener_presupuesto_mes(anio: int, mes: int) -> dict[str, float]:
    """Retorna {categoria: monto_presupuestado} para el mes dado."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT categoria, monto_presupuestado "
        "FROM presupuesto_mensual WHERE anio=? AND mes=?",
        (anio, mes),
    ).fetchall()
    return {r["categoria"]: r["monto_presupuestado"] for r in rows}


def guardar_presupuesto_categoria(anio: int, mes: int,
                                  categoria: str, monto: float) -> None:
    """Inserta o actualiza el presupuesto de una categoría en un mes dado."""
    conn = DatabaseConnection.get()
    conn.execute(
        """
        INSERT INTO presupuesto_mensual (anio, mes, categoria, monto_presupuestado)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(anio, mes, categoria)
        DO UPDATE SET monto_presupuestado = excluded.monto_presupuestado
        """,
        (anio, mes, categoria, monto),
    )
    conn.commit()


def copiar_presupuesto_mes(anio_origen: int, mes_origen: int,
                           anio_dest: int, mes_dest: int) -> int:
    """
    Copia el presupuesto completo de un mes a otro.
    Útil para pre-cargar el presupuesto del mes siguiente con los mismos valores.
    Retorna el número de categorías copiadas.
    """
    datos = obtener_presupuesto_mes(anio_origen, mes_origen)
    if not datos:
        return 0
    for cat, monto in datos.items():
        guardar_presupuesto_categoria(anio_dest, mes_dest, cat, monto)
    return len(datos)
