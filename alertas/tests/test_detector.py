import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from datetime import datetime  # noqa: E402
from detector import Enfriamiento, Latido, MercadoParado, evaluar, mejor_movimiento  # noqa: E402


def serie(n=1500, sigma=0.0001, precio=100.0, semilla=1):
    """Velas M1 sintéticas con ruido normal (sigma = 0,01% por minuto)."""
    rng = random.Random(semilla)
    cierres = [precio]
    for _ in range(n - 1):
        cierres.append(cierres[-1] * math.exp(rng.gauss(0, sigma)))
    return [1_700_000_000 + 60 * i for i in range(n)], cierres


def con_salto(cierres, pct, minutos=5):
    """Los últimos `minutos` suben/bajan `pct` % de forma gradual."""
    base = cierres[-minutos - 1]
    nuevo = cierres[: -minutos]
    for i in range(1, minutos + 1):
        nuevo.append(base * (1 + pct / 100 * i / minutos))
    return nuevo


class TestDetector(unittest.TestCase):
    def test_detecta_subida_brusca(self):
        t, c = serie()
        m = evaluar(t, con_salto(c, 1.0), 5, k=5, minimo_pct_5m=0.3)
        self.assertIsNotNone(m)
        self.assertEqual(m.direccion, "subida")
        self.assertGreater(m.z, 5)

    def test_detecta_bajada_brusca(self):
        t, c = serie()
        m = evaluar(t, con_salto(c, -1.0), 5, k=5, minimo_pct_5m=0.3)
        self.assertIsNotNone(m)
        self.assertEqual(m.direccion, "bajada")

    def test_periodo_tranquilo_no_avisa(self):
        for semilla in range(20):
            t, c = serie(semilla=semilla)
            self.assertIsNone(mejor_movimiento(t, c, [1, 5], k=5, minimo_pct_5m=0.05))

    def test_suelo_absoluto_evita_avisos_triviales(self):
        # Activo muy quieto: un salto de 0,03 % es muchas sigmas, pero no es relevante.
        t, c = serie(sigma=0.00001)
        self.assertIsNone(evaluar(t, con_salto(c, 0.03), 5, k=5, minimo_pct_5m=0.3))
        self.assertIsNotNone(evaluar(t, con_salto(c, 0.03), 5, k=5, minimo_pct_5m=0.01))

    def test_calentamiento_sin_historia_suficiente(self):
        t, c = serie(n=100)
        self.assertIsNone(evaluar(t, con_salto(c, 2.0), 5, k=5, minimo_pct_5m=0.1))

    def test_marca_hueco_de_apertura(self):
        t, c = serie()
        t = list(t)
        t[-1] += 3 * 3600  # el mercado estuvo cerrado horas antes de la última vela
        m = evaluar(t, con_salto(c, 1.0), 5, k=5, minimo_pct_5m=0.3)
        self.assertTrue(m.hueco)

    def test_sin_hueco_en_mercado_continuo(self):
        t, c = serie()
        self.assertFalse(evaluar(t, con_salto(c, 1.0), 5, 5, 0.3).hueco)

    def test_elige_el_horizonte_mas_extremo(self):
        t, c = serie()
        m = mejor_movimiento(t, con_salto(c, 1.0, minutos=1), [1, 5], k=5, minimo_pct_5m=0.3)
        self.assertIsNotNone(m)
        self.assertEqual(m.horizonte_min, 1)


class TestEnfriamiento(unittest.TestCase):
    def test_no_repite_hasta_pasado_el_tiempo(self):
        ahora = [1000.0]
        e = Enfriamiento(15, reloj=lambda: ahora[0])
        self.assertTrue(e.permitir("XAUUSD", "subida"))
        self.assertFalse(e.permitir("XAUUSD", "subida"))
        self.assertTrue(e.permitir("XAUUSD", "bajada"))   # otra dirección sí avisa
        self.assertTrue(e.permitir("NDX", "subida"))      # otro activo sí avisa
        ahora[0] += 15 * 60
        self.assertTrue(e.permitir("XAUUSD", "subida"))


class TestMercadoParado(unittest.TestCase):
    def test_parado_si_el_tick_no_avanza(self):
        ahora = [0.0]
        p = MercadoParado(5, reloj=lambda: ahora[0])
        self.assertFalse(p.parado("NDX", 100))
        ahora[0] += 4 * 60
        self.assertFalse(p.parado("NDX", 100))
        ahora[0] += 2 * 60
        self.assertTrue(p.parado("NDX", 100))
        self.assertFalse(p.parado("NDX", 101))  # vuelve a haber ticks


class TestLatido(unittest.TestCase):
    def test_una_vez_al_dia_a_partir_de_la_hora(self):
        ahora = [datetime(2026, 10, 12, 8, 59)]
        l = Latido("09:00", ahora=lambda: ahora[0])
        self.assertFalse(l.toca())                      # antes de la hora
        ahora[0] = datetime(2026, 10, 12, 9, 0)
        self.assertTrue(l.toca())                       # llega la hora
        ahora[0] = datetime(2026, 10, 12, 18, 30)
        self.assertFalse(l.toca())                      # ya enviado hoy
        ahora[0] = datetime(2026, 10, 13, 8, 0)
        self.assertFalse(l.toca())                      # día nuevo, aún no es la hora
        ahora[0] = datetime(2026, 10, 13, 9, 5)
        self.assertTrue(l.toca())                       # día nuevo, ya es la hora

    def test_desactivado(self):
        for valor in ("no", "off", "", None):
            l = Latido(valor, ahora=lambda: datetime(2026, 10, 12, 12, 0))
            self.assertFalse(l.toca())


if __name__ == "__main__":
    unittest.main()
