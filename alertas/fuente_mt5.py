"""Lectura de precios desde MetaTrader 5 (solo Windows, con el terminal de Darwinex abierto)."""
import time


class FuenteMT5:
    def __init__(self):
        import MetaTrader5 as mt5  # aquí dentro para poder probar el detector sin MT5
        self.mt5 = mt5
        self.ultimo_error = None

    def conectar(self, reintentos=5, espera=10):
        for _ in range(reintentos):
            if self.mt5.initialize():
                return True
            print(f"MT5: no conecta ({self.mt5.last_error()}); reintento en {espera}s")
            time.sleep(espera)
        return False

    def cerrar(self):
        self.mt5.shutdown()

    def activar(self, simbolo):
        """Hay que activar el símbolo en 'Observación de mercado' o no devuelve datos."""
        return self.mt5.symbol_select(simbolo, True)

    def velas_m1(self, simbolo, n):
        datos = self.mt5.copy_rates_from_pos(simbolo, self.mt5.TIMEFRAME_M1, 0, n)
        if datos is None or len(datos) == 0:
            return None
        # La hora de las velas es la del servidor del bróker, no UTC.
        return [int(t) for t in datos["time"]], [float(c) for c in datos["close"]]

    def velas_h1(self, simbolo, n):
        """Velas de 1 hora ya cerradas (posición 1 salta la vela en formación): tiempos, altos, bajos, cierres.

        MT5 devuelve vacío si piden más velas de las que el terminal tiene descargadas o si aún está
        sincronizando el histórico. Por eso se reintenta una vez y, si sigue vacío, con menos velas.
        """
        for cantidad in dict.fromkeys(c for c in (n, 1000, 500, 300, 150, 100) if c <= n):
            for _ in range(2):
                datos = self.mt5.copy_rates_from_pos(simbolo, self.mt5.TIMEFRAME_H1, 1, cantidad)
                if datos is not None and len(datos) > 0:
                    return (
                        [int(t) for t in datos["time"]],
                        [float(x) for x in datos["high"]],
                        [float(x) for x in datos["low"]],
                        [float(x) for x in datos["close"]],
                    )
                time.sleep(1)
        self.ultimo_error = self.mt5.last_error()
        return None

    def hora_tick(self, simbolo):
        tick = self.mt5.symbol_info_tick(simbolo)
        return tick.time if tick else None

    def buscar_simbolos(self, patrones):
        patrones = [p.upper() for p in patrones]
        todos = self.mt5.symbols_get() or []
        return sorted(
            (s.name, s.description) for s in todos
            if any(p in s.name.upper() or p in (s.description or "").upper() for p in patrones)
        )
