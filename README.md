# YouTube Summarizer

Bot de Telegram + CLI para transcribir y resumir videos de YouTube.

**Pipeline:** NoteGPT.io → youtube-transcript-api (fallback) → Gemini 3.1 Flash-Lite → Telegram

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt`

## Instalación

```bash
# Linux / macOS
./setup.sh

# O manual (todas las plataformas)
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuración

```bash
# Asistente gráfico (tkinter)
python run.py setup --gui

# Asistente de terminal
python run.py setup --tui

# O edita .env manualmente
nano .env
```

## Uso

```bash
# Arrancar bot en primer plano
python run.py bot

# Arrancar bot en segundo plano (multiplataforma)
python run.py start

# Detener bot
python run.py stop

# Ver estado
python run.py status

# Menú interactivo
python run.py

# Pipeline CLI
python run.py pipeline "https://youtu.be/VIDEO_ID"
python run.py pipeline "https://youtu.be/VIDEO_ID" -o resumen.md

# Linux/macOS (atajo)
./start.sh
```

## Estructura

```
src/
├── bot.py           Bot de Telegram (polling continuo)
├── transcriber.py   Transcripción: NoteGPT + youtube-transcript-api
├── summarizer.py    Resumen con Gemini 3.1 Flash-Lite
├── pipeline.py      CLI unificado
├── config.py        Gestor de configuración (.env)
├── tui.py           Asistente de terminal (TUI)
├── gui.py           Asistente gráfico (tkinter)
└── daemon.py        Gestor de procesos en segundo plano
run.py               Punto de entrada unificado
```

Extraído de [marodriguezd/my-termux](https://github.com/marodriguezd/my-termux).
