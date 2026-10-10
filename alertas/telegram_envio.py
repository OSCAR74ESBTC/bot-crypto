"""Envío de mensajes a Telegram con la API HTTP (sin dependencias pesadas)."""
import time

import requests


def enviar(token, chat_id, texto, reintentos=3):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for intento in range(reintentos):
        try:
            r = requests.post(url, data={"chat_id": chat_id, "text": texto}, timeout=15)
        except requests.RequestException as e:
            print(f"Telegram: error de red ({e}); reintento {intento + 1}/{reintentos}")
            time.sleep(2 * (intento + 1))
            continue
        if r.status_code == 429:  # demasiados mensajes: Telegram indica cuánto esperar
            espera = r.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(espera + 1)
            continue
        if r.ok:
            return True
        print(f"Telegram: respuesta {r.status_code}: {r.text}")
        return False
    return False
