"""
utils/security.py
Funciones de seguridad: hash SHA-256 de contraseñas y verificación con soporte legacy.
"""

import hashlib


def hashear_clave(clave: str) -> str:
    """Devuelve el SHA-256 hex de la clave (64 caracteres)."""
    return hashlib.sha256(clave.encode("utf-8")).hexdigest()


def es_hash(valor: str) -> bool:
    """True si el valor ya es un SHA-256 hex válido (64 chars hexadecimales)."""
    return len(valor) == 64 and all(c in "0123456789abcdef" for c in valor.lower())


def verificar_clave(clave_ingresada: str, clave_guardada: str) -> bool:
    """
    Compara la clave ingresada contra la guardada.
    Soporta ambos formatos:
      - SHA-256 hex (64 chars): compara hashes.
      - Plain-text legacy: comparación directa (se migra al primer uso en main.py).
    """
    if es_hash(clave_guardada):
        return hashear_clave(clave_ingresada) == clave_guardada
    return clave_ingresada == clave_guardada
