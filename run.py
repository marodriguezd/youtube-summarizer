#!/usr/bin/env python3
"""
run.py — Punto de entrada unificado multiplataforma.

Uso:
  python run.py                        Menú interactivo
  python run.py setup                  Configuración inicial (auto: TUI/GUI)
  python run.py setup --tui            Forzar terminal
  python run.py setup --gui            Forzar interfaz gráfica
  python run.py bot                    Arrancar bot (primer plano)
  python run.py start                  Arrancar bot (segundo plano)
  python run.py stop                   Detener bot
  python run.py restart                Reiniciar bot
  python run.py status                 Estado del bot
  python run.py logs                   Ver últimas líneas del log
  python run.py forever                Watchdog: reinicio automático en fallo
  python run.py pipeline <url>         Transcribir y resumir un video
  python run.py pipeline <url> -o arch  Guardar resumen a archivo
"""

import sys
import subprocess
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Summarizer — Bot de transcripción y resumen",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Ejemplos:
  python run.py                  Menú interactivo
  python run.py setup            Asistente de configuración
  python run.py bot              Arrancar bot en primer plano
  python run.py start            Arrancar bot en segundo plano
  python run.py stop             Detener bot
  python run.py restart          Reiniciar bot
  python run.py status           Ver estado del bot
  python run.py logs             Ver últimas líneas del log
  python run.py forever          Watchdog: reinicio automático en fallo
  python run.py pipeline <url>   Transcribir y resumir un video
  python run.py pipeline <url> -o resumen.md
        """,
    )
    subparsers = parser.add_subparsers(dest="command")

    p_setup = subparsers.add_parser("setup", help="Configuración inicial")
    p_setup_mode = p_setup.add_mutually_exclusive_group()
    p_setup_mode.add_argument("--tui", action="store_true", help="Usar interfaz de terminal")
    p_setup_mode.add_argument("--gui", action="store_true", help="Usar interfaz gráfica")

    subparsers.add_parser("bot", help="Arrancar bot en primer plano")
    subparsers.add_parser("start", help="Arrancar bot en segundo plano")
    subparsers.add_parser("stop", help="Detener bot en segundo plano")
    subparsers.add_parser("restart", help="Reiniciar bot")
    subparsers.add_parser("status", help="Verificar estado del bot")
    subparsers.add_parser("logs", help="Ver últimas líneas del log")
    subparsers.add_parser("forever", help="Watchdog: reinicio automático si el bot falla")

    p_pipe = subparsers.add_parser("pipeline", help="Pipeline CLI: transcripción + resumen")
    p_pipe.add_argument("url", help="URL del video de YouTube")
    p_pipe.add_argument("-o", "--output", default=None, help="Guardar resumen a archivo")

    args = parser.parse_args()

    if args.command is None:
        _show_menu()
    elif args.command == "setup":
        _run_setup(tui=args.tui, gui=args.gui)
    elif args.command == "bot":
        _run_bot()
    elif args.command == "start":
        _run_start()
    elif args.command == "stop":
        _run_stop()
    elif args.command == "restart":
        _run_stop()
        _run_start()
    elif args.command == "status":
        _run_status()
    elif args.command == "logs":
        _run_logs()
    elif args.command == "forever":
        _run_forever()
    elif args.command == "pipeline":
        _run_pipeline(args.url, args.output)


def _show_menu():
    from src.tui import show_main_menu
    show_main_menu()


def _run_setup(tui=False, gui=False):
    if gui:
        from src.gui import run_gui_setup
        run_gui_setup()
    elif tui:
        from src.tui import run_tui_setup
        run_tui_setup()
    else:
        try:
            from src.gui import run_gui_setup
            run_gui_setup()
        except Exception:
            from src.tui import run_tui_setup
            run_tui_setup()


def _run_bot():
    from src.config import has_minimum
    if not has_minimum():
        print("❌ Configura las credenciales primero: python run.py setup")
        sys.exit(1)
    from src.bot import main
    main()


def _run_start():
    from src.config import has_minimum
    if not has_minimum():
        print("❌ Configura las credenciales primero: python run.py setup")
        sys.exit(1)
    from src.daemon import start
    start()


def _run_stop():
    from src.daemon import stop
    stop()


def _run_status():
    from src.daemon import status as daemon_status
    daemon_status()


def _run_logs():
    from src.daemon import logs
    logs()


def _run_forever():
    from src.daemon import run_forever
    run_forever()


def _run_pipeline(url, output):
    from src.pipeline import run_pipeline
    run_pipeline(url, output)


if __name__ == "__main__":
    main()
