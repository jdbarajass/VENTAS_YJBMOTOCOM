"""tests/test_security.py — Tests para utils/security.py"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.security import hashear_clave, es_hash, verificar_clave


class TestHashearClave(unittest.TestCase):

    def test_produce_hex_64_chars(self):
        resultado = hashear_clave("MiClave123")
        self.assertEqual(len(resultado), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in resultado))

    def test_mismo_input_mismo_hash(self):
        self.assertEqual(hashear_clave("abc"), hashear_clave("abc"))

    def test_distinto_input_distinto_hash(self):
        self.assertNotEqual(hashear_clave("abc"), hashear_clave("ABC"))

    def test_clave_vacia(self):
        resultado = hashear_clave("")
        self.assertEqual(len(resultado), 64)


class TestEsHash(unittest.TestCase):

    def test_sha256_hex_valido(self):
        h = hashear_clave("cualquier_clave")
        self.assertTrue(es_hash(h))

    def test_plain_text_no_es_hash(self):
        self.assertFalse(es_hash("YJB2026_*"))
        self.assertFalse(es_hash("hola"))
        self.assertFalse(es_hash(""))

    def test_64_chars_pero_no_hex(self):
        no_hex = "Z" * 64
        self.assertFalse(es_hash(no_hex))


class TestVerificarClave(unittest.TestCase):

    def test_verifica_hash_correcto(self):
        hash_guardado = hashear_clave("MiClave")
        self.assertTrue(verificar_clave("MiClave", hash_guardado))

    def test_rechaza_hash_incorrecto(self):
        hash_guardado = hashear_clave("MiClave")
        self.assertFalse(verificar_clave("OtraClave", hash_guardado))

    def test_legacy_plain_text_correcto(self):
        # BD antigua con contraseña en texto plano
        self.assertTrue(verificar_clave("YJB2026_*", "YJB2026_*"))

    def test_legacy_plain_text_incorrecto(self):
        self.assertFalse(verificar_clave("MalaClave", "YJB2026_*"))

    def test_case_sensitive(self):
        hash_guardado = hashear_clave("clave")
        self.assertFalse(verificar_clave("Clave", hash_guardado))


if __name__ == "__main__":
    unittest.main()
