from database.connection import DatabaseConnection
from models.nota import Nota


def obtener_notas(tipo: str) -> list[Nota]:
    """Retorna todas las notas del tipo dado, pendientes primero."""
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, texto, tipo, completado, fecha_creacion "
        "FROM notas WHERE tipo = ? ORDER BY completado ASC, id DESC",
        (tipo,),
    ).fetchall()
    return [
        Nota(
            id=r[0],
            texto=r[1],
            tipo=r[2],
            completado=bool(r[3]),
            fecha_creacion=r[4],
        )
        for r in rows
    ]


def insertar_nota(nota: Nota) -> int:
    conn = DatabaseConnection.get()
    cur = conn.execute(
        "INSERT INTO notas (texto, tipo, completado, fecha_creacion) VALUES (?,?,?,?)",
        (nota.texto, nota.tipo, int(nota.completado), nota.fecha_creacion),
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


def actualizar_nota(nota_id: int, nuevo_texto: str) -> None:
    conn = DatabaseConnection.get()
    conn.execute(
        "UPDATE notas SET texto = ? WHERE id = ?",
        (nuevo_texto.strip(), nota_id),
    )
    conn.commit()


def eliminar_nota(nota_id: int) -> None:
    conn = DatabaseConnection.get()
    conn.execute("DELETE FROM notas WHERE id = ?", (nota_id,))
    conn.commit()
