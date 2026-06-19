# YouTube Summarizer

Bot de Telegram + CLI para transcribir y resumir videos de YouTube.

**Pipeline:** NoteGPT.io → youtube-transcript-api (fallback) → Gemini 3.1 Flash-Lite → Telegram

> 💡 **Idioma por defecto:** El prompt de resumen viene en **español** y genera resultados en español. Puedes cambiarlo editando la variable `SUMMARIZER_PROMPT` en `src/summarizer.py`. Más detalles en [Personalización](#personalización).

> 🌐 **English version:** [README.md](README.md)

## Requisitos

- Python 3.10+
- `pip install -r requirements.txt`

## Instalación

```bash
# Opción A: Linux / macOS
./setup.sh

# Opción B: manual (todas las plataformas)
python3 -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuración inicial

```bash
# Terminal (recomendado, sin dependencias extra)
python run.py setup --tui

# Ventana gráfica (tkinter)
python run.py setup --gui

# O edita .env manualmente
nano .env
```

El asistente te guía para configurar:
- `GOOGLE_API_KEY` — [Google AI Studio](https://aistudio.google.com/app/apikey)
- `TELEGRAM_BOT_TOKEN` — [@BotFather](https://t.me/BotFather)
- `NG_EMAIL` / `NG_PASSWORD` — [NoteGPT.io](https://notegpt.io) (opcional)

Todas las credenciales se guardan en `.env` local con permisos `600`.

## Uso

### Bot de Telegram

```bash
# Primer plano (Ctrl+C para detener)
python run.py bot

# Segundo plano (multiplataforma)
python run.py start
python run.py status
python run.py logs
python run.py stop
python run.py restart

# Watchdog: reinicio automático si el bot falla (ideal para producción)
python run.py forever
```

### CLI (transcripción + resumen)

```bash
python run.py pipeline "https://youtu.be/VIDEO_ID"
python run.py pipeline "https://youtu.be/VIDEO_ID" -o resumen.md
```

### Menú interactivo

```bash
python run.py
```

## Personalización

El prompt que usa el sistema para resumir vídeos está definido en `src/summarizer.py` como la variable `SUMMARIZER_PROMPT`.

Por defecto, instruye a la IA para:
- Actuar como expert_summarizer
- Escribir en **español**
- Usar Markdown con secciones y emojis
- Mantener el resultado por debajo de 1900 caracteres
- Generar un bloque listo para copiar y pegar en Discord

Puedes editar este prompt para:
- Cambiar el **idioma** de salida
- Modificar el **formato** (texto plano, JSON, HTML, etc.)
- Ajustar el **tono** (formal, casual, técnico)
- Poner otro **límite de caracteres**
- Apuntar a otra **plataforma** (email, Twitter, Notion, etc.)

No necesitas tocar nada más del código — solo edita el prompt y reinicia el bot.

## Producción

### Recomendaciones para deploy

| Escenario | Comando / Herramienta |
|-----------|----------------------|
| Docker | `python run.py forever` como entrypoint |
| systemd | Ejecutar `python run.py forever` en el service |
| supervisord | `command=python run.py forever` |
| Servidor VPS | `python run.py start` + cron que ejecute `python run.py start` cada hora |
| Windows (Tray) | `python run.py start` |
| Linux/macOS (CLI) | `./start.sh` |

### Watchdog (auto-restart)

```bash
python run.py forever
```

Lanza el bot con un watchdog que lo reinicia automáticamente si falla.
Corre en primer plano. Ideal como entrypoint de Docker o service de systemd.

### Logs

```bash
# Ver últimas líneas
python run.py logs

# Ver log completo
cat logs/bot.log
```

Los logs se escriben en `logs/bot.log`. Se recomienda configurar logrotate
en Linux para rotación automática.

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

