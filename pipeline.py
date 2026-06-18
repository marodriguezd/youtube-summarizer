#!/usr/bin/env python3
"""
pipeline.py — Pipeline CLI completo: transcripción + resumen con Gemini.
Uso:
  python pipeline.py "https://youtu.be/XXXXX"
  python pipeline.py "https://youtu.be/XXXXX" -o resumen.md
"""

import os
import sys
import argparse
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip("\"'")
                if v:
                    os.environ.setdefault(k.strip(), v)

from transcriber import fetch_transcript, extract_video_id
from summarizer import call_gemini


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline completo: transcripción + resumen con Gemini.")
    parser.add_argument("url", help="URL del video de YouTube")
    parser.add_argument("--output", "-o", default=None,
                        help="Guardar resumen a archivo")
    args = parser.parse_args()

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY no configurada.", file=sys.stderr)
        print("  Crea un archivo .env con: GOOGLE_API_KEY=tu_key", file=sys.stderr)
        sys.exit(1)

    video_id = extract_video_id(args.url)
    if not video_id:
        print(f"ERROR: No se pudo extraer ID de: {args.url}", file=sys.stderr)
        sys.exit(1)

    print(f"🎬 Video: {args.url}", file=sys.stderr)
    print("📥 Obteniendo transcripción...", file=sys.stderr)

    transcript = fetch_transcript(video_id)
    if not transcript:
        print("❌ No se pudo obtener transcripción.", file=sys.stderr)
        sys.exit(1)

    print(f"📏 Transcripción: {len(transcript)} caracteres", file=sys.stderr)
    print("🤖 Resumiendo con Gemini...", file=sys.stderr)

    try:
        summary = call_gemini(transcript, args.url, api_key)
    except RuntimeError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"📄 Resumen guardado en: {args.output}", file=sys.stderr)
    else:
        print()
        print(summary)


if __name__ == "__main__":
    main()
