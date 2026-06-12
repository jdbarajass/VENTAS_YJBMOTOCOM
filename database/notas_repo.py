from database.connection import DatabaseConnection
from models.nota import Nota


def _row_to_nota(r) -> Nota:
    return Nota(
        id=r[0],
        texto=r[1],
        tipo=r[2],
        completado=bool(r[3]),
        fecha_creacion=r[4],
        fecha_limite=r[5] if len(r) > 5 else None,
    )


def obtener_notas(tipo: str) -> list[Nota]:
    """Retorna todas las notas del tipo dado: vencidas primero, luego pendientes, luego completadas."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, texto, tipo, completado, fecha_creacion, fecha_limite "
        "FROM notas WHERE tipo = ? "
        "ORDER BY completado ASC, "
        "CASE WHEN fecha_limite IS NOT NULL AND completado = 0 "
        "     THEN fecha_limite ELSE '9999-99-99' END ASC, "
        "id DESC",
        (tipo,),
    ).fetchall()
    return [_row_to_nota(r) for r in rows]


def obtener_notas_proximas(dias: int = 3) -> list[Nota]:
    """Retorna notas pendientes con fecha_limite en los próximos `dias` días (incluyendo hoy)."""
    from datetime import date, timedelta
    hoy = date.today()
    limite = (hoy + timedelta(days=dias)).isoformat()
    hoy_str = hoy.isoformat()
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, texto, tipo, completado, fecha_creacion, fecha_limite "
        "FROM notas WHERE completado = 0 AND fecha_limite IS NOT NULL "
        "AND fecha_limite >= ? AND fecha_limite <= ? ORDER BY fecha_limite ASC",
        (hoy_str, limite),
    ).fetchall()
    return [_row_to_nota(r) for r in rows]


def obtener_notas_vencidas() -> list[Nota]:
    """Retorna notas pendientes cuya fecha_limite ya pasó."""
    from datetime import date
    hoy = date.today().isoformat()
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, texto, tipo, completado, fecha_creacion, fecha_limite "
        "FROM notas WHERE completado = 0 AND fecha_limite IS NOT NULL AND fecha_limite < ?",
        (hoy,),
    ).fetchall()
    return [_row_to_nota(r) for r in rows]


def insertar_nota(nota: Nota) -> int:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        "INSERT INTO notas (texto, tipo, completado, fecha_creacion, fecha_limite) "
        "VALUES (?,?,?,?,?)",
        (nota.texto, nota.tipo, int(nota.completado), nota.fecha_creacion, nota.fecha_limite),
    )
    conn.commit()
    return cur.lastrowid


def marcar_nota(nota_id: int, completado: bool) -> None:
    conn = DatabaseConnection.get()
    conn.execute(
        "UPDATE notas SET completado = ? WHERE id = ?",
        (int(completado), nota_id),
    )
    conn.commit()


def actualizar_nota(nota_id: int, nuevo_texto: str, fecha_limite: str | None = None) -> None:
    conn = DatabaseConnection.get()
    conn.execute(
        "UPDATE notas SET texto = ?, fecha_limite = ? WHERE id = ?",
        (nuevo_texto.strip(), fecha_limite, nota_id),
    )
    conn.commit()


def eliminar_nota(nota_id: int) -> None:
    conn = DatabaseConnection.get()
    conn.execute("DELETE FROM notas WHERE id = ?", (nota_id,))
    conn.commit()


def eliminar_todas_notas() -> None:
    conn = DatabaseConnection.get()
    conn.execute("DELETE FROM notas")
    conn.commit()
