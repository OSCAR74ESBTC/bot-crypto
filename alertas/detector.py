"""Detección de movimientos bruscos. Funciones puras: no dependen de MT5 ni de Telegram."""
import math
import statistics
import time
from dataclasses import dataclass


@dataclass
class Movimiento:
    horizonte_min: int
    pct: float          # variación porcentual (con signo) en el horizonte
    z: float            # cuántas veces lo normal del activo (con signo)
    precio: float
    precio_ref: float
    hueco: bool         # True si hubo un salto de tiempo grande (cierre de mercado / apertura)

    @property
    def direccion(self):
        return "subida" if self.pct > 0 else "bajada"


def evaluar(tiempos, cierres, horizonte, k, minimo_pct_5m, historial_min=300):
    """Compara el movimiento de los últimos `horizonte` minutos con lo normal del activo.

    tiempos/cierres: velas M1 en orden cronológico; la última es la vela en formación.
    k: veces lo normal (sigma robusta, MAD) que debe superar el movimiento.
    minimo_pct_5m: suelo absoluto en % para 5 min; para otro horizonte h se escala con sqrt(h/5).
    Devuelve un Movimiento si hay que avisar, o None.
    """
    n = len(cierres)
    h = horizonte
    if n < 2 * h + historial_min:
        return None  # calentamiento: poca historia para saber qué es "normal"
    hist = [math.log(cierres[i] / cierres[i - h]) for i in range(h, n - h)]
    centro = statistics.median(hist)
    sigma = 1.4826 * statistics.median(abs(r - centro) for r in hist)
    if sigma <= 0:
        sigma = statistics.pstdev(hist)
    if sigma <= 0:
        return None
    actual = math.log(cierres[-1] / cierres[-1 - h])
    z = (actual - centro) / sigma
    pct = (math.exp(actual) - 1) * 100
    if abs(z) < k or abs(pct) < minimo_pct_5m * math.sqrt(h / 5):
        return None
    hueco = (tiempos[-1] - tiempos[-1 - h]) > 3 * h * 60
    return Movimiento(h, pct, z, cierres[-1], cierres[-1 - h], hueco)


def mejor_movimiento(tiempos, cierres, horizontes, k, minimo_pct_5m, historial_min=300):
    """Evalúa varios horizontes y devuelve el más extremo (mayor |z|), o None."""
    candidatos = [
        m for h in horizontes
        if (m := evaluar(tiempos, cierres, h, k, minimo_pct_5m, historial_min))
    ]
    return max(candidatos, key=lambda m: abs(m.z)) if candidatos else None


class Enfriamiento:
    """Evita avisos repetidos: un aviso por activo y dirección cada `minutos`."""

    def __init__(self, minutos, reloj=time.time):
        self.segundos = minutos * 60
        self.reloj = reloj
        self.ultimo = {}

    def permitir(self, simbolo, direccion):
        ahora = self.reloj()
        clave = (simbolo, direccion)
        if ahora - self.ultimo.get(clave, -math.inf) < self.segundos:
            return False
        self.ultimo[clave] = ahora
        return True


class MercadoParado:
    """Detecta mercado cerrado: el último tick no avanza durante `minutos` (reloj local)."""

    def __init__(self, minutos, reloj=time.monotonic):
        self.segundos = minutos * 60
        self.reloj = reloj
        self.visto = {}  # simbolo -> (tick_time, momento en que cambió por última vez)

    def parado(self, simbolo, tick_time):
        ahora = self.reloj()
        previo = self.visto.get(simbolo)
        if previo is None or previo[0] != tick_time:
            self.visto[simbolo] = (tick_time, ahora)
            return False
        return ahora - previo[1] >= self.segundos
