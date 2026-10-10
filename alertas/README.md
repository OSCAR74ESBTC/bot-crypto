# Alertas de movimientos bruscos por Telegram

Vigila 9 activos (USDJPY, GBPJPY, XAUUSD, XAGUSD, CADCHF, WS30, SP500, NDX y XTIUSD) con los precios
de MetaTrader 5 de Darwinex y avisa por Telegram cuando uno sube o baja de golpe.

## Cómo decide cuándo avisar

- Mide el movimiento de los últimos **1 y 5 minutos** y lo compara con lo que es normal **en ese activo**
  (últimos 2 días de velas de 1 minuto, con una medida robusta a picos antiguos).
- Avisa si el movimiento supera **5 veces lo normal** (`UMBRAL_K`) **y** el suelo mínimo en % de
  `simbolos.json` (`minimo_pct`). El suelo evita avisos por movimientos diminutos en momentos muy tranquilos.
- No repite el mismo aviso (mismo activo y dirección) durante 15 minutos.
- Si el mercado está cerrado (sin ticks nuevos durante 5 minutos) no avisa.
- Si el salto viene de un cierre/apertura de mercado, el aviso lo indica con «Posible hueco de apertura».
- Los valores de `minimo_pct` son un punto de partida: ajústalos viendo los avisos reales.

## Requisitos

- **Windows** con el terminal **MetaTrader 5 de Darwinex abierto y con la sesión iniciada**.
  La librería `MetaTrader5` de Python solo existe para Windows, así que en un VPS hace falta uno con Windows.
- Python 3.9 o superior: `pip install -r requirements.txt`

## Puesta en marcha

1. **Crea el bot:** en Telegram abre `@BotFather`, escribe `/newbot` y copia el **token**.
2. **Crea el canal:** nuevo canal **privado**, y en Administradores añade tu bot con permiso para publicar.
3. **Obtén el chat_id del canal:** escribe cualquier mensaje en el canal y abre en el navegador
   `https://api.telegram.org/bot<TOKEN>/getUpdates`. Busca `"chat":{"id":-100...` (empieza por `-100`).
4. **Configura:** copia `.env.example` como `.env` y rellena `TELEGRAM_TOKEN` y `TELEGRAM_CHAT_ID`.
   El archivo `.env` está ignorado por git; no lo subas nunca.
5. **Prueba Telegram:** `python alertas.py --prueba-telegram`. Debe llegar un mensaje al canal.
6. **Busca el nombre de XTIUSD:** `python alertas.py --listar-simbolos`. Si en tu MT5 se llama distinto,
   cámbialo en `simbolos.json`. Haz lo mismo con cualquier otro símbolo que el programa diga que no existe.
7. **Ejecuta:** `python alertas.py` (o `python alertas.py --sin-telegram` para ver los avisos solo por pantalla).

## Arranque automático en Windows

Programador de tareas → Crear tarea → desencadenador «Al iniciar sesión» → acción: iniciar
`python` con el argumento `C:\ruta\alertas\alertas.py` y «Iniciar en» `C:\ruta\alertas`.
MT5 también debe arrancar solo y con la sesión guardada.

## Pruebas

`python -m unittest discover -s tests -v` comprueba el detector con series sintéticas (no necesita MT5).
La conexión real con MT5 solo puede probarse en Windows con el terminal abierto.
