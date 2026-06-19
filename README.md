# YouTube Summarizer

Telegram bot + CLI to transcribe and summarize YouTube videos.

**Pipeline:** NoteGPT.io → youtube-transcript-api (fallback) → Gemini 3.1 Flash-Lite → Telegram

> 💡 **Default language:** The built-in summarization prompt is in **Spanish** and produces output in Spanish. You can change both the language and the output format by editing the `SUMMARIZER_PROMPT` variable in `src/summarizer.py`. See [Customization](#customization) below.

> 🌐 **Versión en español:** [README.es.md](README.es.md)

## Requirements

- Python 3.10+
- `pip install -r requirements.txt`

## Installation

```bash
# Option A: Linux / macOS
./setup.sh

# Option B: manual (all platforms)
python3 -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Setup

```bash
# Terminal (recommended, no extra dependencies)
python run.py setup --tui

# GUI window (tkinter)
python run.py setup --gui

# Or edit .env manually
nano .env
```

The setup wizard will guide you through configuring:
- `GOOGLE_API_KEY` — [Google AI Studio](https://aistudio.google.com/app/apikey)
- `TELEGRAM_BOT_TOKEN` — [@BotFather](https://t.me/BotFather)
- `NG_EMAIL` / `NG_PASSWORD` — [NoteGPT.io](https://notegpt.io) (optional)

All credentials are stored in a local `.env` file with `600` permissions.

## Usage

### Telegram Bot

```bash
# Foreground (Ctrl+C to stop)
python run.py bot

# Background (cross-platform)
python run.py start
python run.py status
python run.py logs
python run.py stop
python run.py restart

# Watchdog: auto-restart if the bot crashes (production-ready)
python run.py forever
```

### CLI (transcription + summary)

```bash
python run.py pipeline "https://youtu.be/VIDEO_ID"
python run.py pipeline "https://youtu.be/VIDEO_ID" -o summary.md
```

### Interactive menu

```bash
python run.py
```

## Customization

The system prompt used to summarize videos is defined in `src/summarizer.py` as the `SUMMARIZER_PROMPT` variable.

By default, it instructs the AI to:
- Act as an expert summarizer
- Write in **Spanish**
- Use Markdown with specific section headers and emojis
- Keep results under 1900 characters
- Output a block ready to copy-paste into Discord

You can edit this prompt to:
- Change the output **language** (e.g., to English, Portuguese, French)
- Modify the **format** (plain text, JSON, HTML, etc.)
- Adjust the **tone** (formal, casual, technical)
- Set a different **character limit**
- Target a different **platform** (email, Twitter, Notion, etc.)

No code changes are needed — just edit the prompt string and restart the bot.

## Production

### Deployment recommendations

| Scenario | Command / Tool |
|----------|---------------|
| Docker | `python run.py forever` as entrypoint |
| systemd | Run `python run.py forever` in the service |
| supervisord | `command=python run.py forever` |
| VPS | `python run.py start` + cron running `python run.py start` every hour |
| Windows (Tray) | `python run.py start` |
| Linux/macOS (CLI) | `./start.sh` |

### Watchdog (auto-restart)

```bash
python run.py forever
```

Launches the bot with a watchdog that automatically restarts it if it crashes.
Runs in the foreground. Ideal as a Docker entrypoint or systemd service.

### Logs

```bash
# View recent lines
python run.py logs

# View full log
cat logs/bot.log
```

Logs are written to `logs/bot.log`. Setting up logrotate on Linux for automatic rotation is recommended.

## Structure

```
src/
├── bot.py           Telegram bot (continuous polling)
├── transcriber.py   Transcription: NoteGPT + youtube-transcript-api
├── summarizer.py    Summarization with Gemini 3.1 Flash-Lite
├── pipeline.py      Unified CLI
├── config.py        Configuration manager (.env)
├── tui.py           Terminal UI setup wizard
├── gui.py           Graphical setup wizard (tkinter)
└── daemon.py        Background process manager
run.py               Unified entry point
```

## License

MIT — see [LICENSE](LICENSE).
