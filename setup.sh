#!/usr/bin/env bash
# setup.sh — Prepara el entorno: venv, dependencias, .env.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

echo "📦 Creando entorno virtual..."
python3 -m venv "$VENV_DIR"

echo "📥 Instalando dependencias..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q

# .env
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo ""
    echo "⚠️  Se copió .env.example a .env"
    echo "   EDITA .env con tus credenciales antes de arrancar:"
    echo "   nano $SCRIPT_DIR/.env"
    echo ""
fi

echo "✅ Entorno listo."
echo ""
echo "Para arrancar el bot:"
echo "  ./start.sh"
echo ""
echo "Para usar el pipeline CLI:"
echo "  $VENV_DIR/bin/python pipeline.py \"https://youtu.be/VIDEO_ID\""
