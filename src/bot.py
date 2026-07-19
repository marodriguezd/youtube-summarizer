#!/usr/bin/env python3
"""
bot.py — Bot de Telegram que transcribe y resume videos de YouTube.
Pipeline: NoteGPT.io → youtube-transcript-api (fallback) → Gemini 3.1 Flash-Lite → Telegram.
"""

import os
import re
import sys
import time
import signal
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bot")

try:
    from .transcriber import fetch_transcript, extract_video_id, note_login
    from .summarizer import call_gemini
except ImportError:
    from src.transcriber import fetch_transcript, extract_video_id, note_login
    from src.summarizer import call_gemini

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

running = True
# Track de video_ids:
# _processed_ids: set con clear-on-overflow (comportamiento legacy preservado).
# _failed_ids:    dict con FIFO cap (memory-bounded contra trolls/spam).
_processed_ids = set()
_MAX_PROCESSED = 100
_failed_ids: dict[str, bool] = {}
_MAX_FAILED = 200     # más permisivo que _MAX_PROCESSED: los fallos son útiles para /retry


def _fifo_purge(d: dict, max_size: int) -> None:
    """Borra los más viejos (FIFO) hasta que len(d) <= max_size. O(1) amortizado.

    Aplicada SOLO a _failed_ids. _processed_ids conserva el clear-on-overflow legacy
    por compatibilidad con comportamiento en producción.
    """
    while len(d) > max_size:
        d.pop(next(iter(d)))


def _signal_handler(signum, frame):
    global running
    signame = signal.Signals(signum).name
    log.info(f"Señal {signame} recibida, cerrando bot...")
    running = False


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)

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

    try:
        from .config import load_env
    except ImportError:
        from src.config import load_env
    load_env()

    global TELEGRAM_BOT_TOKEN, GOOGLE_API_KEY
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

    if not TELEGRAM_BOT_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN no configurado. Ejecuta: python run.py setup")
        sys.exit(1)
    if not GOOGLE_API_KEY:
        log.error("GOOGLE_API_KEY no configurado. Ejecuta: python run.py setup")
        sys.exit(1)

    note_login()

    offset = 0
    last_gemini_time = 0

    while running:
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
                         "optimizado para Discord.\n\n"
                         "<b>Comandos:</b>\n"
                         "/help — Ayuda detallada\n"
                         "/retry — Reintentar vídeos que fallaron")
                    continue

                if text == "/help":
                    tg_send(chat_id,
                         "<b>Comandos:</b>\n"
                         "/start — Info\n"
                         "/help — Esta ayuda\n"
                         "/retry — Reintentar vídeos que fallaron\n\n"
                         "<b>Consejos:</b>\n"
                         "• Si un vídeo falla, puedes reenviar el enlace para reintentar\n"
                         "• Si el error persiste, usa /retry para ver los fallos disponibles\n"
                         "• Los fallos suelen ser temporales (rate limit, IP bloqueada, etc.)\n")
                    continue

                if text == "/retry":
                    if not _failed_ids and not _processed_ids:
                        tg_send(chat_id, "📭 No hay vídeos en caché para reintentar.")
                        continue
                    
                    _failed_ids.clear()
                    _processed_ids.clear()
                    
                    tg_send(chat_id,
                         "🔄 Caché de vídeos borrada.\n"
                         "Puedes reenviar cualquier enlace (ya sea que haya fallado o se haya completado antes) y lo intentaré de nuevo.")
                    continue

                if not re.search(r'(youtube\.com|youtu\.be)', text):
                    continue

                video_id = extract_video_id(text)
                if not video_id:
                    tg_send(chat_id, "❌ No pude extraer el ID del video.")
                    continue

                # 🛡️ Control de duplicados: solo bloquea IDs EXITOSOS, no fallidos.
                # Si el video ya se procesó con éxito, avisamos y ofrecemos /retry.
                if video_id in _processed_ids:
                    log.warning(f"Saltando {video_id} (ya procesado exitosamente)")
                    tg_send(chat_id,
                         f"⏭️ El video <code>{video_id}</code> ya se procesó antes. "
                         f"Usa /retry si quieres forzar un nuevo intento.")
                    continue

                log.info(f"Procesando {video_id}")

                now = time.time()
                wait = 4 - (now - last_gemini_time)
                if wait > 0 and last_gemini_time > 0:
                    time.sleep(wait)

                tg_send(chat_id, "⏳ Obteniendo transcripción y resumiendo...")

                transcript = fetch_transcript(video_id)
                if not transcript:
                    _failed_ids[video_id] = True
                    _fifo_purge(_failed_ids, _MAX_FAILED)
                    tg_send(chat_id,
                         "❌ No pude obtener transcripción. El video puede no tener subtítulos "
                         "o YouTube está bloqueando la IP.\n\n"
                         "📌 <b>Puedes reenviar el enlace</b> para reintentar automáticamente.\n"
                         "O usa /retry para gestionar los fallos.")
                    continue

                log.info(f"Transcripción: {len(transcript)} chars")

                video_url = f"https://youtu.be/{video_id}"
                try:
                    summary = call_gemini(transcript, video_url, GOOGLE_API_KEY)
                except RuntimeError as e:
                    log.error(f"Gemini error: {e}")
                    _failed_ids[video_id] = True
                    _fifo_purge(_failed_ids, _MAX_FAILED)
                    tg_send(chat_id, f"❌ Error al resumir: {str(e)[:200]}\n\nReenvía el enlace para reintentar.")
                    continue
                finally:
                    last_gemini_time = time.time()

                cleaned = clean_result(summary)
                # ✅ Solo marcar como procesado si se envió el resumen con éxito
                _processed_ids.add(video_id)
                _failed_ids.pop(video_id, None)
                # Poda para no acumular infinitamente
                if len(_processed_ids) > _MAX_PROCESSED:
                    _processed_ids.clear()
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

    log.info("Bot finalizado")


if __name__ == "__main__":
    if __package__ is None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
