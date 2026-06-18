"""
tui.py — Asistente de configuración por terminal (TUI).
Funciona sin dependencias externas. Usa ANSI colores si el terminal lo soporta.
"""

import os
import sys
from pathlib import Path

try:
    from .config import FIELDS, get_creds, save_creds, validate_creds, has_minimum, ENV_PATH
except ImportError:
    from src.config import FIELDS, get_creds, save_creds, validate_creds, has_minimum, ENV_PATH


def _c():
    """Detecta si el terminal soporta color."""
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return os.getenv("TERM") is not None or os.getenv("ANSICON") is not None


USE_COLOR = _c()


def _green(s):
    return f"\033[92m{s}\033[0m" if USE_COLOR else s


def _red(s):
    return f"\033[91m{s}\033[0m" if USE_COLOR else s


def _yellow(s):
    return f"\033[93m{s}\033[0m" if USE_COLOR else s


def _cyan(s):
    return f"\033[96m{s}\033[0m" if USE_COLOR else s


def _bold(s):
    return f"\033[1m{s}\033[0m" if USE_COLOR else s


def _input(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def _clear():
    os.system("cls" if os.name == "nt" else "clear")


def _header(title):
    width = 56
    print()
    print(_bold("=" * width))
    print(_bold(f"   {title}"))
    print(_bold("=" * width))
    print()


def _status_icon(value, required):
    if required:
        return _green("OK") if value else _red("--")
    else:
        return _green("OK") if value else _yellow("(opcional)")


def _show_status():
    creds = get_creds()
    validation = validate_creds(creds)
    print("  Estado actual:\n")
    for key in FIELDS:
        info = FIELDS[key]
        val = creds.get(key, "")
        status = validation.get(key)
        icon = _status_icon(status, info["required"])
        masked = val[:8] + "*" * min(len(val) - 8, 12) if val and info["secret"] else val
        label = f"{key:25s}"
        print(f"    {label} {icon}  {masked if val else _red('(vacío)')}")
    print()


def run_tui_setup():
    """Asistente interactivo de configuración por terminal."""
    while True:
        _clear()
        _header("YouTube Summarizer — Configuración")
        _show_status()

        print("  Opciones:")
        print("    [1] Configurar una variable")
        print("    [2] Configurar todo")
        print("    [3] Validar configuración")
        print("    [4] Ayuda — ¿dónde obtengo cada clave?")
        print("    [5] Volver")
        print()
        op = _input("  Selecciona [1-5]: ")

        if op == "1":
            _configure_one()
        elif op == "2":
            _configure_all()
        elif op == "3":
            _validate()
        elif op == "4":
            _show_help()
        elif op == "5":
            break
        else:
            print(_red("\n  Opción inválida."))
            _input("  Presiona Enter para continuar...")


def _configure_one():
    creds = get_creds()
    keys = list(FIELDS.keys())
    while True:
        _clear()
        _header("Configurar variable")
        for i, key in enumerate(keys, 1):
            info = FIELDS[key]
            val = creds.get(key, "")
            icon = _green("✓") if val else _red("✗")
            req = _red("*") if info["required"] else ""
            print(f"    [{i}] {key:25s} {icon} {req}")
        print(f"    [{len(keys)+1}] Volver")
        print()
        op = _input("  Selecciona [1-{}]: ".format(len(keys) + 1))
        try:
            idx = int(op) - 1
            if 0 <= idx < len(keys):
                key = keys[idx]
                _prompt_field(key, creds)
                save_creds(creds)
                print(_green(f"\n  ✓ {key} guardado"))
                _input("  Presiona Enter...")
            elif idx == len(keys):
                break
            else:
                print(_red("  Opción inválida."))
                _input("  Presiona Enter...")
        except ValueError:
            print(_red("  Opción inválida."))
            _input("  Presiona Enter...")


def _configure_all():
    creds = get_creds()
    _clear()
    _header("Configurar todo")
    for key in FIELDS:
        _prompt_field(key, creds)
    save_creds(creds)
    print(_green("\n  ✓ Configuración guardada"))
    _input("  Presiona Enter para continuar...")


def _prompt_field(key, creds):
    info = FIELDS[key]
    current = creds.get(key, "")
    req = _red(" (obligatorio)") if info["required"] else _yellow(" (opcional)")
    label = f"{info['label']}{req}"
    print(f"\n  {label}")
    print(f"    {_cyan(info['help'])}")
    if current:
        masked = current[:4] + "*" * min(len(current) - 4, 10)
        print(f"    Actual: {masked}")
    val = _input(f"    Nuevo valor (Enter = mantener): ")
    if val:
        creds[key] = val


def _validate():
    _clear()
    _header("Validación de configuración")
    validation = validate_creds()
    missing = [k for k, v in validation.items() if v is False]
    optional = [k for k, v in validation.items() if v is None]
    if not missing:
        print(_green("  ✅ Todas las variables obligatorias están configuradas.\n"))
        if optional:
            for k in optional:
                print(f"     ⬜ {k} — opcional, no configurado")
    else:
        print(_red("  ❌ Faltan las siguientes variables obligatorias:\n"))
        for k in missing:
            print(f"     - {k} ({FIELDS[k]['label']})")
        print()
        print("  Ejecuta 'python run.py setup' para configurarlas.")
    print()
    _input("  Presiona Enter para continuar...")


def _show_help():
    _clear()
    _header("Ayuda — ¿Dónde obtengo cada clave?")
    print()
    for key, info in FIELDS.items():
        print(f"  {_bold(key)}")
        print(f"    {info['help']}")
        print()
    _input("  Presiona Enter para continuar...")


def show_main_menu():
    """Menú principal interactivo."""
    while True:
        _clear()
        _header("YouTube Summarizer v0")
        if has_minimum():
            print(_green("  ✅ Configuración mínima presente\n"))
        else:
            print(_red("  ❌ Configuración incompleta — ejecuta 'setup' primero\n"))

        print("  [1] Configurar")
        print("  [2] Arrancar bot (primer plano)")
        print("  [3] Arrancar bot (segundo plano)")
        print("  [4] Watchdog — reinicio automático si falla")
        print("  [5] Ver estado")
        print("  [6] Ver logs")
        print("  [7] Detener bot")
        print("  [8] Reiniciar bot")
        print("  [9] Pipeline CLI — transcribir un video")
        print("  [0] Salir")
        print()
        op = _input("  Selecciona [0-9]: ")

        if op == "1":
            run_tui_setup()
        elif op == "2":
            if not has_minimum():
                print(_red("\n  ❌ Configura primero las credenciales."))
                _input("  Presiona Enter...")
                continue
            print(_yellow("\n  Arrancando bot en primer plano..."))
            print(_yellow("  Presiona Ctrl+C para detener.\n"))
            _input("  Presiona Enter para iniciar...")
            from .bot import main
            main()
        elif op == "3":
            if not has_minimum():
                print(_red("\n  ❌ Configura primero las credenciales."))
                _input("  Presiona Enter...")
                continue
            from .daemon import start
            start()
            _input("  Presiona Enter...")
        elif op == "4":
            if not has_minimum():
                print(_red("\n  ❌ Configura primero las credenciales."))
                _input("  Presiona Enter...")
                continue
            from .daemon import run_forever
            run_forever()
        elif op == "5":
            from .daemon import status as daemon_status
            daemon_status()
            print()
            _input("  Presiona Enter...")
        elif op == "6":
            from .daemon import logs
            logs()
            print()
            _input("  Presiona Enter...")
        elif op == "7":
            from .daemon import stop
            stop()
            _input("  Presiona Enter...")
        elif op == "8":
            from .daemon import stop as ds, start as dst
            ds()
            print()
            dst()
            _input("  Presiona Enter...")
        elif op == "9":
            url = _input("  URL de YouTube: ")
            if url:
                from .pipeline import run_pipeline
                run_pipeline(url)
                _input("\n  Presiona Enter...")
        elif op == "0":
            print()
            sys.exit(0)
