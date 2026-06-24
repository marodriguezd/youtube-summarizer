#!/usr/bin/env python3
"""
summarizer.py — Resume transcripciones con Gemini 3.1 Flash-Lite vía REST API directa.
No requiere google-generativeai (evita dependencia de cryptography).
"""

import time
import logging

log = logging.getLogger("summarizer")

GEMINI_MODEL = "gemini-3.1-flash-lite-preview"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

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
    MAX_CHARS = 1900
    MAX_LENGTH_RETRIES = 3

    prompt = SUMMARIZER_PROMPT.format(transcript=transcript, video_url=video_url)
    url = GEMINI_URL + "?key=" + api_key

    for length_attempt in range(1, MAX_LENGTH_RETRIES + 1):
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
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

                # Demasiado largo — reintentar con prompt más estricto
                if length_attempt >= MAX_LENGTH_RETRIES:
                    raise RuntimeError(
                        f"Resumen demasiado largo tras {MAX_LENGTH_RETRIES} intentos: "
                        f"{char_count} chars (límite {MAX_CHARS})"
                    )

                log.warning(
                    f"Summary too long ({char_count} chars), "
                    f"retry {length_attempt}/{MAX_LENGTH_RETRIES}"
                )
                prompt += (
                    f"\n\n⚠️ IMPORTANTE: El resumen anterior tenía {char_count} "
                    f"caracteres, pero el límite es {MAX_CHARS}. Reduce drásticamente: "
                    f"elimina redundancias, acorta las secciones y sé más conciso. "
                    f"NO superes {MAX_CHARS} caracteres en total."
                )
                # Salir del bucle HTTP para reintentar con el prompt reforzado
                break

            except requests.exceptions.HTTPError as e:
                code = e.response.status_code
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

    raise RuntimeError("Gemini falló tras todos los intentos")
