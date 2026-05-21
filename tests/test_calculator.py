"""tests/test_calculator.py — Tests para services/calculator.py"""
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.venta import Venta
from models.configuracion import Configuracion
from services.calculator import (
    calcular_comision,
    calcular_ganancia_bruta,
    calcular_ganancia_neta,
    calcular_comision_combinada,
    completar_venta,
    calcular_utilidad_real_dia,
    calcular_utilidad_real_mes,
)


def _cfg(addi=5.0, bold=3.0, transferencia=1.0,
         arriendo=1_200_000, sueldo=1_300_000,
         servicios=200_000, otros=0, dias=30):
    return Configuracion(
        arriendo=arriendo, sueldo=sueldo, servicios=servicios,
        otros_gastos=otros, dias_mes=dias,
        comision_bold=bold, comision_addi=addi,
        comision_transferencia=transferencia,
    )


def _venta(**kwargs):
    defaults = dict(
        fecha="2026-01-15", producto="Casco", costo=100_000,
        precio=150_000, metodo_pago="Efectivo", cantidad=1,
    )
    defaults.update(kwargs)
    return Venta(**defaults)


class TestComision(unittest.TestCase):

    def test_efectivo_sin_comision(self):
        self.assertEqual(calcular_comision(100_000, "Efectivo", _cfg()), 0.0)

    def test_addi_5_pct(self):
        self.assertEqual(calcular_comision(100_000, "Addi", _cfg(addi=5.0)), 5_000.0)

    def test_bold_3_pct(self):
        self.assertEqual(calcular_comision(200_000, "Bold", _cfg(bold=3.0)), 6_000.0)

    def test_transferencia_1_pct(self):
        self.assertEqual(calcular_comision(50_000, "Transferencia", _cfg(transferencia=1.0)), 500.0)


class TestGanancias(unittest.TestCase):

    def test_ganancia_bruta(self):
        self.assertEqual(calcular_ganancia_bruta(150_000, 100_000), 50_000.0)

    def test_ganancia_neta_con_comision(self):
        self.assertEqual(calcular_ganancia_neta(150_000, 100_000, 5_000), 45_000.0)

    def test_ganancia_neta_sin_comision(self):
        self.assertEqual(calcular_ganancia_neta(150_000, 100_000, 0), 50_000.0)


class TestComisionCombinada(unittest.TestCase):

    def test_dos_metodos(self):
        pagos = [
            {"metodo": "Efectivo", "monto": 50_000},
            {"metodo": "Addi", "monto": 100_000},
        ]
        cfg = _cfg(addi=5.0)
        # Efectivo: 0, Addi: 5000
        self.assertEqual(calcular_comision_combinada(pagos, cfg), 5_000.0)

    def test_todo_efectivo(self):
        pagos = [{"metodo": "Efectivo", "monto": 200_000}]
        self.assertEqual(calcular_comision_combinada(pagos, _cfg()), 0.0)


class TestCompletarVenta(unittest.TestCase):

    def test_venta_efectivo_una_unidad(self):
        v = _venta(precio=150_000, costo=100_000, metodo_pago="Efectivo", cantidad=1)
        completar_venta(v, _cfg())
        self.assertEqual(v.comision, 0.0)
        self.assertEqual(v.ganancia_neta, 50_000.0)

    def test_venta_addi_dos_unidades(self):
        v = _venta(precio=100_000, costo=60_000, metodo_pago="Addi", cantidad=2)
        completar_venta(v, _cfg(addi=5.0))
        # comisión unitaria = 5000, x2 = 10000
        self.assertEqual(v.comision, 10_000.0)
        # ganancia neta = (100k - 60k - 5k) * 2 = 35k * 2 = 70k
        self.assertEqual(v.ganancia_neta, 70_000.0)

    def test_venta_combinada(self):
        pagos = [
            {"metodo": "Efectivo", "monto": 80_000},
            {"metodo": "Bold", "monto": 70_000},
        ]
        v = _venta(precio=150_000, costo=100_000, cantidad=1, metodo_pago="Combinado",
                   pagos_combinados=pagos)
        completar_venta(v, _cfg(bold=3.0))
        # Comisión Bold: 70000 * 3% = 2100
        self.assertAlmostEqual(v.comision, 2_100.0, places=1)
        # Ganancia neta: 150k - 100k - 2100 = 47900
        self.assertAlmostEqual(v.ganancia_neta, 47_900.0, places=1)


class TestUtilidadReal(unittest.TestCase):

    def test_utilidad_dia_positiva(self):
        cfg = _cfg(arriendo=900_000, sueldo=900_000, servicios=0, otros=0, dias=30)
        # gasto_diario = 1_800_000 / 30 = 60_000
        resultado = calcular_utilidad_real_dia(100_000, cfg)
        self.assertAlmostEqual(resultado, 40_000.0, places=0)

    def test_utilidad_mes(self):
        cfg = _cfg(arriendo=1_200_000, sueldo=1_300_000, servicios=200_000, otros=0)
        # total_gastos_mes = 2_700_000
        resultado = calcular_utilidad_real_mes(3_000_000, cfg)
        self.assertAlmostEqual(resultado, 300_000.0, places=0)


if __name__ == "__main__":
    unittest.main()
