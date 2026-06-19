#!/data/data/com.termux/files/usr/bin/bash
# setup.sh — Prepara el entorno: venv, dependencias, .env.
# Funciona en Linux/macOS. Para Windows, sigue las instrucciones del README.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

echo "📦 Creando entorno virtual..."
python3 -m venv "$VENV_DIR"

echo "📥 Instalando dependencias..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo ""
    echo "⚠️  Se copió .env.example a .env"
    echo "   EDITA .env con tus credenciales:"
    echo "   nano $SCRIPT_DIR/.env"
    echo "   O ejecuta: python run.py setup"
    echo ""
fi

echo "✅ Entorno listo."
echo ""
echo "Para arrancar:"
echo "  ./start.sh                    # Segundo plano (Linux/macOS)"
echo "  python run.py bot             # Primer plano"
echo ""
echo "Para configuración:"
echo "  python run.py setup           # Asistente interactivo"
echo "  python run.py setup --gui     # Ventana gráfica"
echo "  python run.py setup --tui     # Terminal"
