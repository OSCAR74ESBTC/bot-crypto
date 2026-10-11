import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import fuente_mt5  # noqa: E402


class MT5Falso:
    TIMEFRAME_H1 = 16385

    def __init__(self, tamanos_ok):
        self.tamanos_ok = tamanos_ok
        self.peticiones = []

    def copy_rates_from_pos(self, simbolo, tf, pos, n):
        self.peticiones.append((tf, pos, n))
        if n not in self.tamanos_ok:
            return None
        return {"time": list(range(n)), "high": [2.0] * n, "low": [1.0] * n, "close": [1.5] * n}

    def last_error(self):
        return (-1, "sin datos")


def fuente(tamanos_ok):
    f = object.__new__(fuente_mt5.FuenteMT5)   # sin importar MetaTrader5 (no existe en Linux)
    f.mt5, f.ultimo_error = MT5Falso(tamanos_ok), None
    return f


@mock.patch.object(fuente_mt5.time, "sleep", lambda s: None)
class TestVelasH1(unittest.TestCase):
    def test_a_la_primera_si_hay_datos(self):
        f = fuente({2000})
        self.assertEqual(len(f.velas_h1("USDJPY", 2000)[0]), 2000)
        self.assertEqual(f.mt5.peticiones, [(16385, 1, 2000)])   # posición 1: solo velas cerradas

    def test_reintenta_con_menos_velas_si_mt5_devuelve_vacio(self):
        f = fuente({500})
        self.assertEqual(len(f.velas_h1("USDJPY", 2000)[0]), 500)

    def test_sin_datos_devuelve_none_y_guarda_el_error(self):
        f = fuente(set())
        self.assertIsNone(f.velas_h1("USDJPY", 300))
        self.assertEqual(f.ultimo_error, (-1, "sin datos"))

    def test_nunca_pide_mas_de_lo_solicitado(self):
        f = fuente(set())
        f.velas_h1("USDJPY", 300)
        self.assertTrue(all(n <= 300 for _, _, n in f.mt5.peticiones))


if __name__ == "__main__":
    unittest.main()
