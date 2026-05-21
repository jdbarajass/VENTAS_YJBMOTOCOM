"""
tests/run_tests.py
Script de conveniencia para correr todos los tests desde la raíz del proyecto.

Uso:
    python tests/run_tests.py
    python tests/run_tests.py -v          # verbose
"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

loader = unittest.TestLoader()
suite = loader.discover(start_dir=str(Path(__file__).parent), pattern="test_*.py")

runner = unittest.TextTestRunner(verbosity=2 if "-v" in sys.argv else 1)
resultado = runner.run(suite)
sys.exit(0 if resultado.wasSuccessful() else 1)
