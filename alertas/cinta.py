"""Cinta de tendencia (propia, no es el indicador de Illumri): funciones puras, sin MT5 ni Telegram.

La cinta es el espacio entre dos medias móviles exponenciales (rápida y lenta). Tiene tres estados:
alcista, neutral y bajista. Hay una zona neutral proporcional al ATR para filtrar el ruido.
Solo se avisa cuando la dirección se invierte de verdad (alcista <-> bajista) tras cruzar esa zona,
y siempre con la vela ya cerrada.
"""
from dataclasses import dataclass


@dataclass
class Giro:
    indice: int
    tiempo: int      # hora de apertura de la vela, en hora del servidor del bróker
    direccion: int   # +1 alcista, -1 bajista
    cierre: float
    rapida: float
    lenta: float


def ema(valores, n):
    alfa = 2 / (n + 1)
    salida = [valores[0]]
    for v in valores[1:]:
        salida.append(alfa * v + (1 - alfa) * salida[-1])
    return salida


def atr(altos, bajos, cierres, n):
    rangos = [altos[0] - bajos[0]]
    for i in range(1, len(cierres)):
        rangos.append(max(altos[i] - bajos[i], abs(altos[i] - cierres[i - 1]), abs(bajos[i] - cierres[i - 1])))
    alfa = 1 / n
    salida = [rangos[0]]
    for r in rangos[1:]:
        salida.append(alfa * r + (1 - alfa) * salida[-1])
    return salida


def barras_minimas(lenta, atr_n=14):
    """Historia necesaria para que las medias se estabilicen antes de dar señales."""
    return max(lenta * 3, atr_n * 3, 60)


def giros(tiempos, altos, bajos, cierres, rapida=9, lenta=21, umbral_atr=0.3, atr_n=14):
    """Devuelve todos los giros de dirección de la serie (velas cerradas, en orden cronológico)."""
    minimo = barras_minimas(lenta, atr_n)
    if len(cierres) < minimo:
        return []
    r, l = ema(cierres, rapida), ema(cierres, lenta)
    a = atr(altos, bajos, cierres, atr_n)
    direccion, salida = 0, []
    for i in range(minimo, len(cierres)):
        dif, banda = r[i] - l[i], umbral_atr * a[i]
        estado = 1 if dif > banda else -1 if dif < -banda else 0
        if estado != 0:
            if direccion != 0 and estado != direccion:
                salida.append(Giro(i, tiempos[i], estado, cierres[i], r[i], l[i]))
            direccion = estado
    return salida


class SeguidorCinta:
    """Avisa como mucho una vez por vela cerrada y no repite el último giro al reiniciar el programa."""

    def __init__(self, rapida=9, lenta=21, umbral_atr=0.3, atr_n=14):
        self.parametros = dict(rapida=rapida, lenta=lenta, umbral_atr=umbral_atr, atr_n=atr_n)
        self.ultima_barra = {}

    def procesar(self, simbolo, tiempos, altos, bajos, cierres):
        """Devuelve la lista de giros nuevos desde la última lectura (normalmente vacía)."""
        if len(cierres) < barras_minimas(self.parametros["lenta"], self.parametros["atr_n"]):
            return []
        previa = self.ultima_barra.get(simbolo)
        self.ultima_barra[simbolo] = tiempos[-1]
        if previa is None or tiempos[-1] == previa:
            return []  # primera lectura tras arrancar (solo se anota) o misma vela
        return [g for g in giros(tiempos, altos, bajos, cierres, **self.parametros) if g.tiempo > previa]
