"""tests/test_schema_migrations.py — Tests para el sistema de migraciones versionadas."""
import unittest
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class _FakeConn:
    """Conexión SQLite en memoria para aislar tests del archivo .db real."""
    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.execute("PRAGMA foreign_keys=ON")

    def execute(self, sql, params=()):
        return self._conn.execute(sql, params)

    def commit(self):
        self._conn.commit()

    def fetchone(self):
        pass


class TestMigraciones(unittest.TestCase):

    def _conn_limpia(self):
        return sqlite3.connect(":memory:")

    def test_initialize_schema_no_falla(self):
        """initialize_schema() debe completar sin excepciones en BD vacía."""
        from database import connection as _conn_mod
        from database import schema as _schema_mod

        conn_real = sqlite3.connect(":memory:")
        conn_real.execute("PRAGMA foreign_keys=ON")
        conn_real.execute("PRAGMA journal_mode=WAL")

        orig_get = _conn_mod.DatabaseConnection.get
        _conn_mod.DatabaseConnection.get = staticmethod(lambda: conn_real)
        try:
            _schema_mod.initialize_schema()
        finally:
            _conn_mod.DatabaseConnection.get = orig_get

    def test_schema_version_tabla_creada(self):
        """Después de initialize_schema() debe existir la tabla schema_version."""
        from database import connection as _conn_mod
        from database import schema as _schema_mod

        conn_real = sqlite3.connect(":memory:")
        conn_real.execute("PRAGMA foreign_keys=ON")

        orig_get = _conn_mod.DatabaseConnection.get
        _conn_mod.DatabaseConnection.get = staticmethod(lambda: conn_real)
        try:
            _schema_mod.initialize_schema()
            tablas = {r[0] for r in conn_real.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
            self.assertIn("schema_version", tablas)
        finally:
            _conn_mod.DatabaseConnection.get = orig_get

    def test_version_max_correcta(self):
        """La versión máxima en schema_version debe coincidir con _VERSION_ACTUAL."""
        from database import connection as _conn_mod
        from database import schema as _schema_mod

        conn_real = sqlite3.connect(":memory:")
        conn_real.execute("PRAGMA foreign_keys=ON")

        orig_get = _conn_mod.DatabaseConnection.get
        _conn_mod.DatabaseConnection.get = staticmethod(lambda: conn_real)
        try:
            _schema_mod.initialize_schema()
            version_max = conn_real.execute(
                "SELECT MAX(version) FROM schema_version"
            ).fetchone()[0]
            self.assertEqual(version_max, _schema_mod._VERSION_ACTUAL)
        finally:
            _conn_mod.DatabaseConnection.get = orig_get

    def test_idempotente_doble_llamada(self):
        """Llamar initialize_schema() dos veces no debe duplicar registros."""
        from database import connection as _conn_mod
        from database import schema as _schema_mod

        conn_real = sqlite3.connect(":memory:")
        conn_real.execute("PRAGMA foreign_keys=ON")

        orig_get = _conn_mod.DatabaseConnection.get
        _conn_mod.DatabaseConnection.get = staticmethod(lambda: conn_real)
        try:
            _schema_mod.initialize_schema()
            _schema_mod.initialize_schema()
            count = conn_real.execute(
                "SELECT COUNT(*) FROM schema_version"
            ).fetchone()[0]
            self.assertEqual(count, _schema_mod._VERSION_ACTUAL)
        finally:
            _conn_mod.DatabaseConnection.get = orig_get


if __name__ == "__main__":
    unittest.main()
