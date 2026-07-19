#!/usr/bin/env python3
"""
summarizer.py — Resume transcripciones con Gemini 3.1 Flash-Lite vía REST API directa.
No requiere google-generativeai (evita dependencia de cryptography).
"""

import os
import time
import logging

log = logging.getLogger("summarizer")

# Modelo Gemini primario configurable vía .env. Si Google lo retira,
# el bot cae automáticamente al siguiente modelo de la lista de fallback.
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
FALLBACK_MODELS = [
    "gemini-3.1-flash",            # próximo estable conocido
    "gemini-2.5-flash-lite",       # estable GA
]
# dedupe preservando orden: el configurado (o default) siempre va primero.
MODELS_TO_TRY = list(dict.fromkeys([DEFAULT_GEMINI_MODEL] + FALLBACK_MODELS))


class GeminiModelUnavailable(Exception):
    """Señal interna: el modelo probado devolvió 404. call_gemini() salta al siguiente."""

SUMMARIZER_PROMPT = """Actúa como expert_summarizer, especializado en transformar transcripciones o vídeos en resúmenes optimizados para Discord.

Objetivo

Extrae las ideas más importantes del contenido y conviértelas en un resumen claro, estructurado y de alta densidad informativa.

Proceso

1. Identifica los conceptos, argumentos y conclusiones principales.
2. Elimina redundancias, ejemplos repetidos y relleno.
3. Agrupa la información por temas.
4. Prioriza los insights más relevantes.

Formato

- Escribe en español.
- Usa Markdown.
- Usa "###" para las secciones.
- Usa negritas para destacar conceptos clave.
- Usa algunos emojis para categorizar contenido, sin saturar.
- Prioriza claridad, síntesis y utilidad.

Restricciones

- Mantén el resultado por debajo de 1900 caracteres.
- No inventes información.
- No añadas opiniones.
- No expliques el proceso.
- No muestres razonamiento interno.
- No escribas ningún texto fuera del bloque de salida.
- Devuelve únicamente un bloque Markdown listo para copiar y pegar en Discord.

Formato de salida obligatorio

```markdown
📊 **Título descriptivo**

### 🚨 Punto principal

- Idea clave.
- Idea clave.

### 💡 Implicaciones

- Consecuencia relevante.
- Insight importante.

### 🎯 Conclusión

- Resumen final.

[Video completo](link_placeholder)
```

Incluye siempre al final:

"Video completo" (link_placeholder)

TRANSCRIPCIÓN DEL VIDEO:
{transcript}

VIDEO_URL: {video_url}"""


def call_gemini(transcript: str, video_url: str, api_key: str) -> str:
    """Prueba MODELS_TO_TRY secuencialmente hasta que uno funcione."""
    last_err: Exception | None = None
    for model in MODELS_TO_TRY:
        try:
            return _call_gemini_single_model(model, transcript, video_url, api_key)
        except GeminiModelUnavailable as e:
            log.warning(f"Modelo {e.args[0]} no disponible (404), probando siguiente")
            last_err = e
            continue
    raise RuntimeError(
        f"Todos los modelos Gemini fallaron. Probados: {MODELS_TO_TRY}. Último error: {last_err}"
    )


def _call_gemini_single_model(model: str, transcript: str, video_url: str, api_key: str) -> str:
    """Llama a Gemini con UN modelo, preservando la lógica interna de length/http retries."""
    MAX_CHARS = 1900
    MAX_LENGTH_RETRIES = 3

    base_prompt = SUMMARIZER_PROMPT.format(transcript=transcript, video_url=video_url)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    reinforce = ""     # acumulamos refuerzos entre length_attempt para no perderlos

    for length_attempt in range(1, MAX_LENGTH_RETRIES + 1):
        prompt = base_prompt + reinforce
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048},
        }

        for http_attempt in range(1, 4):
            try:
                import requests
                resp = requests.post(url, json=payload, timeout=120)
                resp.raise_for_status()
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini sin candidatos")
                parts = candidates[0].get("content", {}).get("parts", [])
                result = parts[0].get("text", "") if parts else ""
                if "link_placeholder" in result:
                    result = result.replace("link_placeholder", video_url)

                char_count = len(result)
                if char_count <= MAX_CHARS:
                    return result

                if length_attempt >= MAX_LENGTH_RETRIES:
                    raise RuntimeError(
                        f"Resumen demasiado largo tras {MAX_LENGTH_RETRIES} intentos: "
                        f"{char_count} chars (límite {MAX_CHARS})"
                    )

                log.warning(
                    f"Summary too long ({char_count} chars), "
                    f"retry {length_attempt}/{MAX_LENGTH_RETRIES}"
                )
                reinforce += (
                    f"\n\n⚠️ IMPORTANTE: El resumen anterior tenía {char_count} "
                    f"caracteres, pero el límite es {MAX_CHARS}. Reduce drásticamente: "
                    f"elimina redundancias, acorta las secciones y sé más conciso. "
                    f"NO superes {MAX_CHARS} caracteres en total."
                )
                # Salir del bucle HTTP para reintentar con el prompt reforzado
                break

            except requests.exceptions.HTTPError as e:
                code = e.response.status_code
                if code == 404:
                    raise GeminiModelUnavailable(model) from e
                if code == 429 and http_attempt < 3:
                    wait = 10 * (2 ** (http_attempt - 1))
                    log.warning(f"Gemini rate limit, reintento en {wait}s")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"Gemini {code}: {str(e)[:200]}")
            except RuntimeError:
                raise  # Propagar errores nuestros (demasiado largo, etc.)
            except Exception as e:
                if http_attempt < 3:
                    wait = 10 * (2 ** (http_attempt - 1))
                    log.warning(f"Gemini error, reintento en {wait}s: {str(e)[:100]}")
                    time.sleep(wait)
                    continue
                raise RuntimeError(str(e))

    raise RuntimeError("Gemini falló tras todos los intentos con este modelo")
