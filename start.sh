#!/usr/bin/env bash
# start.sh — Arranca el bot de Telegram en segundo plano.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/.bot.pid"
BOT_SCRIPT="$SCRIPT_DIR/bot.py"

mkdir -p "$LOG_DIR"

# Matar instancia previa
pkill -f "python3.*bot.py" 2>/dev/null || true
sleep 1
rm -f "$PID_FILE"

# Validar .env
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "❌ .env no encontrado. Copia .env.example a .env y rellena las credenciales."
    exit 1
fi

# Validar venv
if [ ! -d "$VENV_DIR" ]; then
    echo "❌ Entorno virtual no encontrado. Ejecuta ./setup.sh primero."
    exit 1
fi

source "$VENV_DIR/bin/activate"

cd "$SCRIPT_DIR"
nohup python3 "$BOT_SCRIPT" >> "$LOG_DIR/bot.log" 2>&1 &
BOT_PID=$!
echo "$BOT_PID" > "$PID_FILE"

sleep 2
if kill -0 "$BOT_PID" 2>/dev/null; then
    echo ""
    echo "✅ Bot corriendo (PID $BOT_PID)"
    echo "   Log: $LOG_DIR/bot.log"
    echo "   Parar: pkill -f \"python3.*bot.py\""
    echo ""
else
    echo "❌ El bot falló al arrancar. Revisa: tail -20 $LOG_DIR/bot.log"
    rm -f "$PID_FILE"
    exit 1
fi
