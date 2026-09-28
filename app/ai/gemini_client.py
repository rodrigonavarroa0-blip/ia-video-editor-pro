"""Cliente para inferencia editorial avanzada con Google Gemini 3.7 Flash."""

import json
import os
import time

from app.core.config import config
from app.core.logger import ai_logger
from app.models.analysis import AnalysisResult
from app.models.editorial import EditorialPlan

# Import a nivel de módulo para evitar overhead por llamada
# Protegido con try/except para entornos sin la dependencia instalada
try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    genai = None
    genai_types = None
    _GENAI_AVAILABLE = False

_GEMINI_RETRY_ATTEMPTS = 3
_GEMINI_RETRY_BASE_DELAY_SEC = 1.5  # Backoff: 1.5s, 3s, 6s


class GeminiEditorialClient:
    """Invoca el modelo Gemini 3.7 Flash con JSON Schema Structured Output para decisiones editoriales."""

    @classmethod
    def is_available(cls) -> bool:
        """Verifica si existe una API key y la librería google-genai está instalada."""
        if not _GENAI_AVAILABLE:
            return False
        api_key = os.environ.get("GEMINI_API_KEY") or config.get("ai.gemini_api_key")
        return bool(api_key and str(api_key).strip())

    @classmethod
    def generate_editorial_plan(
        cls,
        analysis: AnalysisResult,
        target_profile: str = "social",
        target_duration: float | None = None,
    ) -> EditorialPlan | None:
        """
        Envía los metadatos de análisis (transcripción, silencios, escenas) a Gemini 3.7 Flash
        y recibe un EditorialPlan fuertemente tipado.

        Incluye retry con exponential backoff (3 intentos) para errores de red transitorios.
        """
        api_key = os.environ.get("GEMINI_API_KEY") or config.get("ai.gemini_api_key")
        if not api_key or not _GENAI_AVAILABLE:
            ai_logger.info("GEMINI_API_KEY no configurada o google-genai no disponible. Recurriendo a motor heurístico local.")
            return None

        system_instruction = (
            "Eres el Director Editorial y Editor de Video Profesional de IA Video Editor Pro. "
            "Tu objetivo es crear un plan de edición (EditorialPlan) de máximo enganche, ritmo dinámico "
            "y retención para plataformas como TikTok, Reels y YouTube Shorts.\n"
            "Reglas obligatorias:\n"
            "1. Analiza el gancho (Hook) de los primeros 3 a 5 segundos y asigna un hook_score (0.0 a 1.0).\n"
            "2. Elimina silencios muertos (>1.5s), pausas incómodas y muletillas redundantes.\n"
            "   CONSERVA pausas dramáticas cortas (≤0.8s) que son técnica narrativa intencional.\n"
            "3. Mantén los bloques con alto contenido de valor y añade dinamismo con cortes limpios o ZOOM_IN.\n"
            "4. Aplica ZOOM_IN automáticamente en segmentos con palabras de alto impacto o cifras numéricas.\n"
            "5. Sugiere palabras clave relevantes para B-Roll contextual.\n"
            "6. Debes retornar exclusivamente un JSON conforme al esquema provisto sin formato markdown exterior."
        )

        # Preparar resumen de análisis en formato compacto
        transcript_text = analysis.transcript.text if analysis.transcript else ""
        words_count = analysis.transcript.word_count if analysis.transcript else 0
        duration = analysis.media_info.duration_seconds if analysis.media_info else 0.0

        prompt_payload = {
            "project_id": analysis.project_id,
            "target_profile": target_profile,
            "media_duration_seconds": duration,
            "word_count": words_count,
            "transcript": transcript_text[:4000],  # Truncar para no exceder context window
            "silence_intervals": [
                {"start": s.start, "end": s.end, "duration": s.duration, "severity": s.severity.value}
                for s in analysis.silence_intervals[:30]
            ],
            "scene_boundaries": [
                {"start": sc.start, "end": sc.end, "duration": sc.duration}
                for sc in analysis.scenes[:30]
            ],
        }

        prompt_text = (
            f"Analiza la siguiente información audiovisual y genera el EditorialPlan estructurado:\n\n"
            f"{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
        )

        model_name = config.get("ai.model", "gemini-3.7-flash")

        for attempt in range(_GEMINI_RETRY_ATTEMPTS):
            try:
                ai_logger.info(f"Enviando solicitud editorial a Gemini ({model_name}), intento {attempt + 1}/{_GEMINI_RETRY_ATTEMPTS}...")

                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_text,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=EditorialPlan,
                        temperature=0.3,
                    ),
                )

                if response.text:
                    plan_data = json.loads(response.text)
                    plan = EditorialPlan.model_validate(plan_data)
                    ai_logger.info(
                        f"Plan editorial generado exitosamente con Gemini "
                        f"(Hook: {plan.hook_score}, Retención: {plan.retention_score})"
                    )
                    return plan

            except Exception as e:
                error_str = str(e)
                is_retryable = any(kw in error_str.lower() for kw in [
                    "timeout", "connection", "network", "rate", "503", "429", "502", "500"
                ])

                if is_retryable and attempt < _GEMINI_RETRY_ATTEMPTS - 1:
                    delay = _GEMINI_RETRY_BASE_DELAY_SEC * (2 ** attempt)
                    ai_logger.warning(
                        f"Error temporal de Gemini (intento {attempt + 1}): {e}. "
                        f"Reintentando en {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    ai_logger.warning(
                        f"Fallo definitivo en llamada a Gemini tras {attempt + 1} intentos ({e}). "
                        f"Recurriendo al motor heurístico local."
                    )
                    return None

        return None
