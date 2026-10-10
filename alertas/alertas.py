"""Avisos por Telegram de movimientos bruscos en 9 activos, con precios de MT5 (Darwinex).

Uso:
    python alertas.py                    # modo normal
    python alertas.py --prueba-telegram  # envía un mensaje de prueba
    python alertas.py --listar-simbolos  # ayuda a encontrar el nombre exacto en tu MT5
    python alertas.py --sin-telegram     # muestra los avisos por pantalla sin enviarlos
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from detector import Enfriamiento, Latido, MercadoParado, mejor_movimiento
from telegram_envio import enviar

AQUI = Path(__file__).resolve().parent


def cargar_env(ruta):
    """Lee un archivo .env sencillo (CLAVE=valor) sin pisar variables ya definidas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8-sig").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def numero(nombre, defecto):
    return float(os.environ.get(nombre, defecto))


def formatear(nombre, m, hora_broker):
    flecha = "📈" if m.pct > 0 else "📉"
    texto = (
        f"{flecha} {nombre}: {m.direccion} brusca {m.pct:+.2f}% en {m.horizonte_min} min "
        f"({abs(m.z):.1f}× lo normal)\n"
        f"Precio: {m.precio:.5g} (antes {m.precio_ref:.5g})\n"
        f"Hora del bróker: {hora_broker}"
    )
    if m.hueco:
        texto += "\n⚠️ Posible hueco de apertura/cierre de mercado"
    return texto


def formatear_latido(total, parados, avisos, errores):
    texto = (
        f"✅ Sigo vivo. Vigilando {total} activos.\n"
        f"Avisos desde el último latido: {avisos}\n"
        f"Activos con el mercado parado ahora: {parados} de {total}"
    )
    if errores:
        texto += f"\n⚠️ Errores de lectura desde el último latido: {errores}"
    return texto


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--prueba-telegram", action="store_true")
    ap.add_argument("--listar-simbolos", action="store_true")
    ap.add_argument("--sin-telegram", action="store_true")
    args = ap.parse_args()

    cargar_env(AQUI / ".env")
    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")

    if args.prueba_telegram:
        if not token or not chat_id:
            sys.exit("Faltan TELEGRAM_TOKEN y TELEGRAM_CHAT_ID (ver .env.example).")
        ok = enviar(token, chat_id, "✅ Prueba: el bot de alertas puede escribir en este canal.")
        sys.exit(0 if ok else "No se pudo enviar. Revisa token, chat_id y que el bot sea administrador.")

    from fuente_mt5 import FuenteMT5
    fuente = FuenteMT5()
    if not fuente.conectar():
        sys.exit("No se pudo conectar con MT5. ¿Está abierto el terminal de Darwinex y con sesión iniciada?")

    if args.listar_simbolos:
        for nombre, desc in fuente.buscar_simbolos(["XTI", "WTI", "OIL", "CRUDE"]):
            print(f"{nombre}  —  {desc}")
        fuente.cerrar()
        return

    if not args.sin_telegram and (not token or not chat_id):
        sys.exit("Faltan TELEGRAM_TOKEN y TELEGRAM_CHAT_ID (ver .env.example), o usa --sin-telegram.")

    simbolos = json.loads((AQUI / "simbolos.json").read_text(encoding="utf-8-sig"))["simbolos"]
    k = numero("UMBRAL_K", 5)
    horizontes = [int(h) for h in os.environ.get("HORIZONTES_MIN", "1,5").split(",")]
    historial = int(numero("HISTORIAL_VELAS", 2880))
    intervalo = numero("INTERVALO_SEG", 15)
    enfriamiento = Enfriamiento(numero("ENFRIAMIENTO_MIN", 15))
    parado = MercadoParado(numero("MERCADO_PARADO_MIN", 5))
    latido = Latido(os.environ.get("LATIDO_HORA", "09:00"))
    avisos = errores = parados_ahora = 0

    activos = []
    for s in simbolos:
        if fuente.activar(s["mt5"]):
            activos.append(s)
        else:
            print(f"AVISO: el símbolo {s['mt5']} ({s['nombre']}) no existe en tu MT5; lo ignoro.")
    if not activos:
        sys.exit("Ningún símbolo válido.")
    print(f"Vigilando {len(activos)} activos. Umbral {k}× lo normal. Ctrl+C para parar.")

    while True:
        parados_ciclo = 0
        for s in activos:
            try:
                hora_tick = fuente.hora_tick(s["mt5"])
                if hora_tick is None or parado.parado(s["mt5"], hora_tick):
                    parados_ciclo += 1
                    continue  # mercado cerrado o sin datos
                velas = fuente.velas_m1(s["mt5"], historial)
                if velas is None:
                    continue
                m = mejor_movimiento(*velas, horizontes, k, s["minimo_pct"])
                if m and enfriamiento.permitir(s["nombre"], m.direccion):
                    hora = datetime.fromtimestamp(velas[0][-1], timezone.utc).strftime("%Y-%m-%d %H:%M")
                    texto = formatear(s["nombre"], m, hora)
                    print(texto, "\n")
                    avisos += 1
                    if not args.sin_telegram:
                        enviar(token, chat_id, texto)
            except Exception as e:  # un fallo en un activo no debe parar el resto
                errores += 1
                print(f"Error con {s['nombre']}: {e}")
        parados_ahora = parados_ciclo
        if latido.toca():
            texto = formatear_latido(len(activos), parados_ahora, avisos, errores)
            print(texto, "\n")
            if not args.sin_telegram:
                enviar(token, chat_id, texto)
            avisos = errores = 0
        time.sleep(intervalo)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Parado.")
