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
    from .config import get_env_path, load_env
except ImportError:
    from src.config import get_env_path, load_env

PID_FILE = get_env_path().parent / ".bot.pid"
LOG_DIR = get_env_path().parent / "logs"
BOT_LOG = LOG_DIR / "bot.log"
PROJECT_ROOT = get_env_path().parent

# Health-check: tras lanzar el bot, esperamos hasta que escriba "Bot iniciado" al log
# Y que su proceso siga vivo. Evita falsos positivos tipo "✅" cuando el bot ya murió.
HEALTH_CHECK_TIMEOUT = 30    # segundos máximos
HEALTH_CHECK_INTERVAL = 1    # cada cuánto re-leer el log


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, OSError):
        return False

    # Extra check for Linux to avoid false positives with stale PIDs reused by other processes
    if sys.platform.startswith("linux"):
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                cmdline = f.read().split(b'\x00')
                if not any(b"python" in arg or b"src.bot" in arg for arg in cmdline):
                    return False
        except Exception:
            pass

    return True


def _launch_bot(log_file) -> subprocess.Popen:
    """Lanza el bot como módulo (-m src.bot) desde la raíz del proyecto."""
    # Usar explícitamente el Python del venv para que las dependencias estén disponibles
    venv_python = str(PROJECT_ROOT / "venv" / "bin" / "python")
    if not os.path.isfile(venv_python):
        # Fallback a sys.executable si no hay venv
        venv_python = sys.executable
    return subprocess.Popen(
        [venv_python, "-m", "src.bot"],
        cwd=str(PROJECT_ROOT),
        stdout=log_file,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )


def _wait_for_healthy(pid: int) -> bool:
    """
    Espera hasta que el bot haya escrito 'Bot iniciado' al log Y su proceso siga vivo.
    Devuelve True SOLO si ambas condiciones se cumplen dentro de HEALTH_CHECK_TIMEOUT.
    Re-check tras cada lectura de log para evitar race condition (print → crash inmediato).
    """
    deadline = time.time() + HEALTH_CHECK_TIMEOUT
    while time.time() < deadline:
        if not _is_running(pid):
            return False
        try:
            # Seek al final del log (no cargar entero en RAM — puede ser grande).
            tail_size = 4096   # 4 KB bastan para encontrar "Bot iniciado"
            with open(BOT_LOG, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                if size > tail_size:
                    f.seek(size - tail_size)
                tail = f.read().decode("utf-8", errors="replace")
            if "Bot iniciado" in tail:
                if _is_running(pid):    # re-check tras la señal (cubre race condition)
                    return True
        except FileNotFoundError:
            pass
        except Exception:
            pass
        time.sleep(HEALTH_CHECK_INTERVAL)
    return False     # timeout sin señal de ready + proceso vivo


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
    load_env()
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

    if _wait_for_healthy(proc.pid):
        print(f"  ✅ Bot arrancado y operativo (PID {proc.pid})")
        print(f"     Log: {BOT_LOG}")
    else:
        print(f"  ❌ El bot no levantó correctamente en {HEALTH_CHECK_TIMEOUT}s.")
        print(f"     Revisa: tail -30 {BOT_LOG}")
        _kill_process(proc.pid)               # kill ANTES del unlink (evita carrera)
        PID_FILE.unlink(missing_ok=True)


def run_forever():
    """Lanza el bot con watchdog: lo reinicia automáticamente si falla.
    Corre en primer plano (ideal para systemd, docker, supervisord)."""
    load_env()
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
