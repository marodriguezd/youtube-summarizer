# transcription-bot

Bot de Telegram + CLI para transcribir y resumir videos de YouTube.

**Pipeline:** NoteGPT.io → youtube-transcript-api (fallback) → Gemini 3.1 Flash-Lite → Telegram

Extraído de [marodriguezd/my-termux](https://github.com/marodriguezd/my-termux).

## Requisitos

- Python 3.10+
- `GOOGLE_API_KEY` de [Google AI Studio](https://aistudio.google.com/app/apikey)
- Token de bot de [@BotFather](https://t.me/BotFather)
- (Opcional) Cuenta en [NoteGPT.io](https://notegpt.io) para transcripciones más fiables

## Setup

```bash
./setup.sh
```

Edita `.env` con tus credenciales.

## Uso

### Bot de Telegram

```bash
./start.sh
```

Envía una URL de YouTube al bot en Telegram.

### CLI

```bash
./venv/bin/python pipeline.py "https://youtu.be/VIDEO_ID"
```

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `bot.py` | Bot de Telegram (polling continuo) |
| `transcriber.py` | Transcripción NoteGPT + fallback |
| `summarizer.py` | Resumen con Gemini 3.1 Flash-Lite |
| `pipeline.py` | CLI unificado |
| `start.sh` | Entrypoint para arrancar el bot |
| `setup.sh` | Setup inicial del entorno |

Ver `SKILL.md` del repo original para documentación completa del pipeline.
