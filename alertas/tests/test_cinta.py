import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cinta import SeguidorCinta, giros  # noqa: E402


def velas(cierres, mecha=0.05):
    t = [1_700_000_000 + 3600 * i for i in range(len(cierres))]
    return t, [c + mecha for c in cierres], [c - mecha for c in cierres], list(cierres)


def baja_y_sube(semilla=3, n_baja=150, n_sube=150):
    rng = random.Random(semilla)
    c = [150.0]
    for i in range(n_baja + n_sube - 1):
        c.append(c[-1] + (-0.10 if i < n_baja else 0.10) + rng.gauss(0, 0.03))
    return velas(c)


def recortar(serie, n):
    return tuple(x[:n] for x in serie)


class TestGiros(unittest.TestCase):
    def test_un_solo_giro_cuando_cambia_la_tendencia(self):
        g = giros(*baja_y_sube())
        self.assertEqual([x.direccion for x in g], [1])
        self.assertGreater(g[0].indice, 150)   # llega después del cambio real, nunca antes

    def test_giro_bajista(self):
        t, a, b, c = baja_y_sube()
        t, a, b, c = velas([300 - x for x in c])  # espejo: sube y luego baja
        self.assertEqual([x.direccion for x in giros(t, a, b, c)], [-1])

    def test_ruido_dentro_de_la_banda_no_da_giros(self):
        for semilla in range(10):
            r = random.Random(semilla)
            c = [150 + r.gauss(0, 0.03) for _ in range(400)]
            self.assertEqual(giros(*velas(c, mecha=0.15)), [])

    def test_retroceso_suave_no_da_giro(self):
        c = [150 + 0.05 * i + 0.4 * math.sin(i / 6) for i in range(400)]
        self.assertEqual(giros(*velas(c)), [])

    def test_poca_historia_no_da_giros(self):
        self.assertEqual(giros(*recortar(baja_y_sube(), 40)), [])


class TestSeguidor(unittest.TestCase):
    def setUp(self):
        self.serie = baja_y_sube()
        self.indice = giros(*self.serie)[0].indice

    def test_primera_lectura_solo_anota_y_no_avisa(self):
        s = SeguidorCinta()
        self.assertEqual(s.procesar("USDJPY", *recortar(self.serie, self.indice + 1)), [])

    def test_avisa_una_vez_en_la_vela_del_giro(self):
        s = SeguidorCinta()
        s.procesar("USDJPY", *recortar(self.serie, self.indice))        # vela anterior (se anota)
        nuevo = s.procesar("USDJPY", *recortar(self.serie, self.indice + 1))
        self.assertEqual([g.direccion for g in nuevo], [1])
        # el bucle consulta cada 15 s: la misma vela no vuelve a avisar
        self.assertEqual(s.procesar("USDJPY", *recortar(self.serie, self.indice + 1)), [])

    def test_vela_sin_giro_no_avisa(self):
        s = SeguidorCinta()
        s.procesar("USDJPY", *recortar(self.serie, 100))
        self.assertEqual(s.procesar("USDJPY", *recortar(self.serie, 101)), [])

    def test_reiniciar_no_repite_el_ultimo_giro(self):
        s = SeguidorCinta()                                              # programa recién arrancado
        self.assertEqual(s.procesar("USDJPY", *recortar(self.serie, self.indice + 1)), [])

    def test_activos_independientes(self):
        s = SeguidorCinta()
        s.procesar("USDJPY", *recortar(self.serie, self.indice))
        self.assertEqual(s.procesar("GBPJPY", *recortar(self.serie, self.indice + 1)), [])  # primera lectura de otro


if __name__ == "__main__":
    unittest.main()
