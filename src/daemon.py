"""
daemon.py — Gestor de procesos en segundo plano (multiplataforma).
Inicia, detiene, monitorea y verifica el estado del bot.
Funciona en Linux, macOS y Windows.
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path

try:
    from .config import get_env_path
except ImportError:
    from src.config import get_env_path

PID_FILE = get_env_path().parent / ".bot.pid"
LOG_DIR = get_env_path().parent / "logs"
BOT_LOG = LOG_DIR / "bot.log"
PROJECT_ROOT = get_env_path().parent


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (ProcessLookupError, OSError):
        return False


def _launch_bot(log_file) -> subprocess.Popen:
    """Lanza el bot como módulo (-m src.bot) desde la raíz del proyecto."""
    return subprocess.Popen(
        [sys.executable, "-m", "src.bot"],
        cwd=str(PROJECT_ROOT),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def _kill_process(pid: int):
    """Envía señal de parada al proceso."""
    try:
        if os.name == "nt":
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        else:
            os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    except Exception as e:
        print(f"  Error al detener PID {pid}: {e}")


def start():
    """Arranca el bot en segundo plano."""
    if PID_FILE.exists():
        with open(PID_FILE) as f:
            pid = f.read().strip()
        if pid and pid.isdigit() and _is_running(int(pid)):
            print(f"  El bot ya está corriendo (PID {pid})")
            return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    with open(BOT_LOG, "a") as log:
        log.write(f"\n--- Inicio {time.ctime()} ---\n")
        proc = _launch_bot(log)

    with open(PID_FILE, "w") as f:
        f.write(str(proc.pid))

    time.sleep(2)
    if _is_running(proc.pid):
        print(f"  ✅ Bot arrancado (PID {proc.pid})")
        print(f"     Log: {BOT_LOG}")
    else:
        print(f"  ❌ El bot falló al arrancar. Revisa logs.")
        PID_FILE.unlink(missing_ok=True)


def run_forever():
    """Lanza el bot con watchdog: lo reinicia automáticamente si falla.
    Corre en primer plano (ideal para systemd, docker, supervisord)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  🛡️  Watchdog activo — reinicio automático si el bot falla")
    print(f"     Log: {BOT_LOG}")
    print(f"     Ctrl+C para detener\n")

    first = True
    while True:
        if not first:
            print(f"  🔄 Reintentando en 5s...")
            for i in range(5, 0, -1):
                print(f"     {i}...")
                time.sleep(1)
        first = False

        with open(BOT_LOG, "a") as log:
            log.write(f"\n--- Watchdog: inicio {time.ctime()} ---\n")
            proc = _launch_bot(log)

        print(f"  🤖 Bot arrancado (PID {proc.pid})")
        proc.wait()

        if proc.returncode == 0:
            print(f"  ✅ Bot terminó normalmente (PID {proc.pid})")
            break
        print(f"  ⚠️  Bot terminó con código {proc.returncode}, reiniciando...")


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
    _kill_process(pid)
    time.sleep(1)

    # Forzar si sigue vivo
    if _is_running(pid):
        try:
            os.kill(pid, signal.SIGKILL if os.name != "nt" else signal.SIGTERM)
        except Exception:
            pass

    PID_FILE.unlink(missing_ok=True)
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


def logs(lines: int = 30):
    """Muestra las últimas líneas del log."""
    if not BOT_LOG.exists():
        print("  No hay archivo de log todavía.")
        return
    with open(BOT_LOG) as f:
        all_lines = f.readlines()
    tail = all_lines[-lines:]
    print(f"  📄 Últimas {len(tail)} líneas de {BOT_LOG}:\n")
    for line in tail:
        print(line, end="")


def _fmt_size(bytes_: int) -> str:
    if bytes_ < 1024:
        return f"{bytes_} B"
    elif bytes_ < 1024**2:
        return f"{bytes_/1024:.1f} KB"
    else:
        return f"{bytes_/1024**2:.1f} MB"
