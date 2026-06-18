"""
daemon.py — Gestor de procesos en segundo plano (multiplataforma).
Inicia, detiene y verifica el estado del bot usando subprocess + PID file.
Funciona en Linux, macOS y Windows.
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path

from .config import get_env_path

PID_FILE = get_env_path().parent / ".bot.pid"
LOG_DIR = get_env_path().parent / "logs"
BOT_LOG = LOG_DIR / "bot.log"


def _is_running(pid: int) -> bool:
    """Verifica si un PID existe (funciona en Unix y Windows)."""
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (ProcessLookupError, OSError):
        return False


def start():
    """Arranca el bot en segundo plano."""
    if PID_FILE.exists():
        with open(PID_FILE) as f:
            pid = f.read().strip()
        if pid and pid.isdigit() and _is_running(int(pid)):
            print(f"  El bot ya está corriendo (PID {pid})")
            return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    bot_script = os.path.join(os.path.dirname(__file__), "bot.py")

    with open(BOT_LOG, "a") as log:
        log.write(f"\n--- Inicio {time.ctime()} ---\n")
        proc = subprocess.Popen(
            [sys.executable, bot_script],
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    time.sleep(2)
    if _is_running(proc.pid):
        print(f"  ✅ Bot arrancado (PID {proc.pid})")
        print(f"     Log: {BOT_LOG}")
    else:
        print(f"  ❌ El bot falló al arrancar. Revisa: tail -20 {BOT_LOG}")
        PID_FILE.unlink(missing_ok=True)


def stop():
    """Detiene el bot en segundo plano."""
    if not PID_FILE.exists():
        print("  El bot no está corriendo.")
        return

    with open(PID_FILE) as f:
        pid = f.read().strip()

    if not pid or not pid.isdigit():
        PID_FILE.unlink(missing_ok=True)
        print("  PID inválido, archivo limpiado.")
        return

    pid = int(pid)
    try:
        if os.name == "nt":
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        else:
            os.kill(pid, signal.SIGTERM)
        time.sleep(1)
    except ProcessLookupError:
        pass
    except Exception as e:
        print(f"  Error al detener: {e}")

    if PID_FILE.exists():
        PID_FILE.unlink()

    print(f"  ✅ Bot detenido (PID {pid})")


def status():
    """Muestra el estado del bot."""
    if not PID_FILE.exists():
        print("  ❌ Bot no está corriendo")
        return False

    with open(PID_FILE) as f:
        pid = f.read().strip()

    if not pid or not pid.isdigit():
        PID_FILE.unlink(missing_ok=True)
        print("  ❌ PID inválido, archivo limpiado.")
        return False

    if _is_running(int(pid)):
        print(f"  ✅ Bot corriendo (PID {pid})")
        if BOT_LOG.exists():
            size = BOT_LOG.stat().st_size
            print(f"     Log: {BOT_LOG} ({_fmt_size(size)})")
        return True
    else:
        print("  ❌ PID file existe pero el proceso ya no está activo.")
        PID_FILE.unlink(missing_ok=True)
        return False


def _fmt_size(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024**2:
        return f"{bytes_/1024:.1f} KB"
    else:
        return f"{bytes_/1024**2:.1f} MB"
