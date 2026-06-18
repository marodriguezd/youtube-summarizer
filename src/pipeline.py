#!/usr/bin/env python3
"""
pipeline.py — Pipeline CLI: transcripción + resumen con Gemini.
"""

import os
import sys

try:
    from .transcriber import fetch_transcript, extract_video_id
    from .summarizer import call_gemini
except ImportError:
    from src.transcriber import fetch_transcript, extract_video_id
    from src.summarizer import call_gemini


def run_pipeline(url: str, output: str = None):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY no configurada.", file=sys.stderr)
        sys.exit(1)

    video_id = extract_video_id(url)
    if not video_id:
        print(f"ERROR: No se pudo extraer ID de: {url}", file=sys.stderr)
        sys.exit(1)

    print(f"🎬 Video: {url}", file=sys.stderr)
    print("📥 Obteniendo transcripción...", file=sys.stderr)

    transcript = fetch_transcript(video_id)
    if not transcript:
        print("❌ No se pudo obtener transcripción.", file=sys.stderr)
        sys.exit(1)

    print(f"📏 Transcripción: {len(transcript)} caracteres", file=sys.stderr)
    print("🤖 Resumiendo con Gemini...", file=sys.stderr)

    try:
        summary = call_gemini(transcript, url, api_key)
    except RuntimeError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"📄 Resumen guardado en: {output}", file=sys.stderr)
    else:
        print()
        print(summary)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python src/pipeline.py <url> [-o archivo]", file=sys.stderr)
        sys.exit(1)
    run_pipeline(sys.argv[1], sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "-o" else None)
