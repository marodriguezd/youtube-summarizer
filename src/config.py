"""
config.py — Gestor de configuración (.env) multiplataforma.
Carga, guarda y valida credenciales desde archivo .env + variables de entorno.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

FIELDS = {
    "GOOGLE_API_KEY": {
        "label": "Google API Key",
        "required": True,
        "secret": True,
        "help": "https://aistudio.google.com/app/apikey",
    },
    "TELEGRAM_BOT_TOKEN": {
        "label": "Telegram Bot Token",
        "required": True,
        "secret": True,
        "help": "Crea un bot con @BotFather en Telegram",
    },
    "NG_EMAIL": {
        "label": "NoteGPT Email",
        "required": False,
        "secret": False,
        "help": "Opcional — https://notegpt.io — para transcripciones más fiables",
    },
    "NG_PASSWORD": {
        "label": "NoteGPT Password",
        "required": False,
        "secret": True,
        "help": "Opcional — contraseña de NoteGPT",
    },
}


def load_env():
    """Carga .env en os.environ si existe y las vars no están ya definidas."""
    if not ENV_PATH.exists():
        return
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip("\"'")
                if v:
                    os.environ.setdefault(k.strip(), v)


def get_creds() -> dict:
    """Lee credenciales actuales (desde .env + os.environ)."""
    creds = {}
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    v = v.strip().strip("\"'")
                    if v:
                        creds[k.strip()] = v
    for key in FIELDS:
        env_val = os.environ.get(key)
        if env_val:
            creds[key] = env_val
    return creds


def save_creds(creds: dict):
    """Guarda credenciales en .env."""
    current = {}
    if ENV_PATH.exists():
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    current[k.strip()] = v
    current.update(creds)
    with open(ENV_PATH, "w") as f:
        for key in FIELDS:
            if key in current:
                f.write(f"{key}={current[key]}\n")
        for key in current:
            if key not in FIELDS:
                f.write(f"{key}={current[key]}\n")
    os.chmod(ENV_PATH, 0o600)


def validate_creds(creds: dict = None) -> dict:
    """Valida credenciales. Devuelve dict con key -> True/False/None."""
    if creds is None:
        creds = get_creds()
    result = {}
    for key, info in FIELDS.items():
        val = creds.get(key, "")
        if info["required"]:
            result[key] = bool(val) and len(val) > 5
        else:
            result[key] = bool(val) and len(val) > 2 if val else None
    return result


def has_minimum() -> bool:
    """True si las credenciales obligatorias están configuradas."""
    creds = get_creds()
    return bool(creds.get("GOOGLE_API_KEY")) and bool(creds.get("TELEGRAM_BOT_TOKEN"))


def get_env_path() -> Path:
    return ENV_PATH
