#!/usr/bin/env bash
# start.sh — Arranca el bot en segundo plano (Linux/macOS).
# Para Windows o multiplataforma, usa: python run.py start
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "❌ .env no encontrado. Copia .env.example a .env y rellena las credenciales."
    exit 1
fi

if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "❌ Entorno virtual no encontrado. Ejecuta ./setup.sh primero."
    exit 1
fi

source "$SCRIPT_DIR/venv/bin/activate"
python "$SCRIPT_DIR/run.py" start
