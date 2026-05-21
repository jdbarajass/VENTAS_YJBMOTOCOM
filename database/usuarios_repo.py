"""
database/usuarios_repo.py
CRUD para la tabla `usuarios`.
"""
from dataclasses import dataclass, field
from database.connection import DatabaseConnection


@dataclass
class Usuario:
    nombre: str
    rol: str        # 'admin' | 'vendedor'
    clave_hash: str
    id: int | None = field(default=None)


def obtener_todos_usuarios() -> list[Usuario]:
    conn = DatabaseConnection.get()
    rows = conn.execute(
        "SELECT id, nombre, rol, clave_hash FROM usuarios ORDER BY id ASC"
    ).fetchall()
    return [Usuario(id=r[0], nombre=r[1], rol=r[2], clave_hash=r[3]) for r in rows]


def obtener_usuario_por_nombre(nombre: str) -> Usuario | None:
    conn = DatabaseConnection.get()
    row = conn.execute(
        "SELECT id, nombre, rol, clave_hash FROM usuarios WHERE nombre = ?", (nombre,)
    ).fetchone()
    return Usuario(id=row[0], nombre=row[1], rol=row[2], clave_hash=row[3]) if row else None


def insertar_usuario(usuario: Usuario) -> int:
    conn = DatabaseConnection.get()
    cursor = conn.execute(
        "INSERT INTO usuarios (nombre, rol, clave_hash) VALUES (?, ?, ?)",
        (usuario.nombre.strip(), usuario.rol, usuario.clave_hash),
    )
    conn.commit()
    return cursor.lastrowid


def actualizar_clave_usuario(usuario_id: int, clave_hash: str) -> None:
    conn = DatabaseConnection.get()
    conn.execute("UPDATE usuarios SET clave_hash = ? WHERE id = ?", (clave_hash, usuario_id))
    conn.commit()


def eliminar_usuario(usuario_id: int) -> bool:
    conn = DatabaseConnection.get()
    cursor = conn.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    conn.commit()
    return cursor.rowcount > 0


def contar_usuarios() -> int:
    conn = DatabaseConnection.get()
    return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
