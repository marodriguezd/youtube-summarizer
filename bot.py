#!/usr/bin/env python3
"""
bot.py — Bot de Telegram que transcribe y resume videos de YouTube.
Pipeline: NoteGPT.io → youtube-transcript-api (fallback) → Gemini 3.1 Flash-Lite → Telegram.
"""

import os
import re
import sys
import time
import logging
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip("\"'")
                if v:
                    os.environ.setdefault(k.strip(), v)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot")

from transcriber import fetch_transcript, extract_video_id, note_login
from summarizer import call_gemini

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    log.error("TELEGRAM_BOT_TOKEN no configurado")
    sys.exit(1)
if not GOOGLE_API_KEY:
    log.error("GOOGLE_API_KEY no configurado")
    sys.exit(1)

log.info("Bot iniciado")


def tg_send(chat_id: int, text: str):
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=15)
        return resp.json().get("ok", False)
    except Exception as e:
        log.warning(f"sendMessage error: {e}")
        return False


def tg_send_long(chat_id: int, text: str):
    max_len = 4000
    if len(text) <= max_len:
        return tg_send(chat_id, text)
    for i in range(0, len(text), max_len):
        tg_send(chat_id, text[i:i+max_len])
        time.sleep(0.3)


def clean_result(result: str) -> str:
    c = re.sub(r'^```markdown\s*', '', result, flags=re.MULTILINE)
    c = re.sub(r'\s*```$', '', c, flags=re.MULTILINE)
    return c.strip()


def main():
    import requests

    note_login()

    offset = 0
    last_gemini_time = 0

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            resp = requests.get(url, params={
                "offset": offset,
                "timeout": 30,
                "allowed_updates": ["message"],
            }, timeout=35)
            data = resp.json()

            if not data.get("ok"):
                time.sleep(5)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "").strip()

                if not text:
                    continue

                if text == "/start":
                    tg_send(chat_id,
                         "🎬 <b>YouTube Transcriber</b>\n\n"
                         "Envíame un enlace de YouTube y te devuelvo un resumen "
                         "optimizado para Discord.")
                    continue
                if text == "/help":
                    tg_send(chat_id,
                         "<b>Comandos:</b>\n"
                         "/start - Info\n/help - Ayuda\n\n"
                         "Pega un enlace de YouTube y te lo resumo.")
                    continue

                if not re.search(r'(youtube\.com|youtu\.be)', text):
                    continue

                video_id = extract_video_id(text)
                if not video_id:
                    tg_send(chat_id, "❌ No pude extraer el ID del video.")
                    continue

                log.info(f"Procesando {video_id}")

                now = time.time()
                wait = 4 - (now - last_gemini_time)
                if wait > 0 and last_gemini_time > 0:
                    time.sleep(wait)

                tg_send(chat_id, "⏳ Obteniendo transcripción y resumiendo...")

                transcript = fetch_transcript(video_id)
                if not transcript:
                    tg_send(chat_id,
                         "❌ No pude obtener transcripción. El video puede no tener subtítulos "
                         "o YouTube está bloqueando la IP. Prueba con otro video.")
                    continue

                log.info(f"Transcripción: {len(transcript)} chars")

                video_url = f"https://youtu.be/{video_id}"
                try:
                    summary = call_gemini(transcript, video_url, GOOGLE_API_KEY)
                except RuntimeError as e:
                    log.error(f"Gemini error: {e}")
                    tg_send(chat_id, f"❌ Error al resumir: {str(e)[:200]}")
                    continue
                finally:
                    last_gemini_time = time.time()

                cleaned = clean_result(summary)
                tg_send_long(chat_id, cleaned)
                log.info(f"Resumen enviado ({len(cleaned)} chars)")

        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.ConnectionError as e:
            log.warning(f"Connection error, reintento en 10s: {str(e)[:80]}")
            time.sleep(10)
            continue
        except KeyboardInterrupt:
            log.info("Bot detenido por el usuario")
            break
        except Exception as e:
            log.error(f"Error inesperado: {str(e)[:200]}")
            time.sleep(5)


if __name__ == "__main__":
    main()
