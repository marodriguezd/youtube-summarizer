#!/usr/bin/env python3
"""
transcriber.py — Obtiene transcripciones de YouTube.
Métodos: NoteGPT.io (login automático con re-login si expira) → youtube-transcript-api (fallback).
Prioridad de idiomas: es > es-ES > es-419 > en > en-US > en-GB.
"""

import os
import re
import time
import logging
from urllib.parse import urlparse, parse_qs

log = logging.getLogger("transcriber")

NOTE_SESSION = None
NOTE_TOKEN_TIME = 0


def extract_video_id(text: str) -> str | None:
    urls = re.findall(r'(https?://[^\s]+)', text)
    for url in urls:
        parsed = urlparse(url)
        if parsed.hostname in ("youtu.be",):
            vid = parsed.path.lstrip("/").split("?")[0]
            if re.match(r'^[A-Za-z0-9_-]{11}$', vid):
                return vid
        if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
            if parsed.path == "/watch":
                vid = parse_qs(parsed.query).get("v", [None])[0]
                if vid and re.match(r'^[A-Za-z0-9_-]{11}$', vid):
                    return vid
            for prefix in ("/embed/", "/v/", "/shorts/"):
                if parsed.path.startswith(prefix):
                    vid = parsed.path[len(prefix):].split("?")[0]
                    if re.match(r'^[A-Za-z0-9_-]{11}$', vid):
                        return vid
    return None


def note_login(force: bool = False) -> bool:
    global NOTE_SESSION, NOTE_TOKEN_TIME
    now = time.time()
    if not force and NOTE_SESSION is not None and (now - NOTE_TOKEN_TIME) < 1500:
        return True
    try:
        import requests
        email = os.environ.get("NG_EMAIL")
        password = os.environ.get("NG_PASSWORD")
        if not email or not password:
            log.warning("NoteGPT: NG_EMAIL/NG_PASSWORD no configurados")
            return False
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://notegpt.io",
            "Referer": "https://notegpt.io/youtube-transcript-generator",
        })
        r = s.post("https://notegpt.io/api/v1/auth/email/login",
            json={"email": email, "password": password}, timeout=15)
        data = r.json()
        if data.get("code") == 100000:
            token = data["data"]["access_token"]
            s.headers.update({"Authorization": f"Bearer {token}"})
            NOTE_SESSION = s
            NOTE_TOKEN_TIME = now
            return True
        log.warning(f"NoteGPT login falló: {data.get('message', data)}")
        return False
    except Exception as e:
        log.warning(f"NoteGPT login exception: {e}")
        return False


def _parse_note_transcript(data: dict) -> str | None:
    transcripts = data.get("data", {}).get("transcripts", {})
    if not isinstance(transcripts, dict):
        return None
    for lang in ("es", "es-ES", "es-419", "en", "en-US", "en-GB"):
        if lang in transcripts:
            for track in ("custom", "default", "auto"):
                segs = transcripts[lang].get(track, [])
                if segs:
                    texts = [s.get("text", "") for s in segs if isinstance(s, dict)]
                    if texts:
                        return " ".join(texts)
    first_lang = next(iter(transcripts.values()), {})
    for track in ("custom", "default", "auto"):
        segs = first_lang.get(track, [])
        if segs:
            texts = [s.get("text", "") for s in segs if isinstance(s, dict)]
            if texts:
                return " ".join(texts)
    return None


def _extract_texts(transcript) -> list[str]:
    """
    Normaliza segmentos de transcripción: acepta list de dicts, objetos con .text, o strings.
    Filtra vacíos y whitespace redundante. Devuelve lista de strings no-vacíos.
    """
    out: list[str] = []
    for seg in transcript:
        if isinstance(seg, dict):
            t = seg.get("text", "")
        elif hasattr(seg, "text"):
            t = seg.text
        elif isinstance(seg, str):
            t = seg
        else:
            continue
        t = t.strip()
        if t:
            out.append(t)
    return out


def fetch_transcript(video_id: str) -> str | None:
    for attempt in range(2):
        if not note_login(force=(attempt > 0)):
            break
        try:
            import requests
            url = "https://notegpt.io/api/v2/video-transcript"
            params = {"platform": "youtube", "video_id": video_id}
            r = NOTE_SESSION.get(url, params=params, timeout=30)
            data = r.json()

            if data.get("code") == 100000:
                result = _parse_note_transcript(data)
                if result:
                    return result
                log.warning("NoteGPT: sin transcripción disponible")
                break
            elif data.get("code") in (100020, 100001):
                log.warning("NoteGPT: sesión expirada, re-login forzado...")
                continue
            else:
                log.warning(f"NoteGPT: code {data.get('code')}: {data.get('message', '')}")
                if attempt == 0:
                    continue
                break
        except Exception as e:
            log.warning(f"NoteGPT error (intento {attempt+1}): {e}")
            if attempt == 0:
                continue
            break

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        tl = api.list(video_id)
        for lang in ("es", "es-ES", "es-419", "en", "en-US", "en-GB"):
            try:
                sel = tl.find_transcript([lang])
                transcript = sel.fetch()
                texts = []
                for t in transcript:
                    if isinstance(t, dict):
                        texts.append(t.get("text", ""))
                    elif hasattr(t, "text"):
                        texts.append(t.text)
                if texts:
                    return " ".join(texts)
            except Exception:
                continue
        for t in tl:
            try:
                raw = t.fetch()
            except Exception as e:
                log.warning(
                    f"youtube-transcript-api: fallo al fetch idioma "
                    f"{getattr(t, 'language_code', '?')}: {e}"
                )
                continue
            texts = _extract_texts(raw)
            if texts:
                return " ".join(texts)
        return None     # agotados todos los idiomas disponibles
    except ImportError:
        log.warning("youtube-transcript-api no disponible")
        return None
    except Exception as e:
        log.warning(f"YouTube fallback error: {e}")
        return None
