"""Motor editorial determinista y heurístico local (Zero Crash / Offline Fallback)."""

import re

from app.core.logger import ai_logger
from app.models.analysis import AnalysisResult
from app.models.editorial import (
    EditAction,
    EditDecision,
    EditorialPlan,
    SilenceInterval,
    SilenceSeverity,
)
from app.models.transcript import TranscriptDocument

# Vocabulario ampliado de palabras de enganche (16 → 52 palabras)
# Incluye modismos de redes sociales, términos de urgencia y patrones de storytelling
HOOK_KEYWORDS_ES = {
    # Urgencia y exclusividad
    "secreto", "revelado", "exclusivo", "confidencial", "prohibido",
    # Negatividad de alto impacto
    "error", "nunca", "jamás", "evita", "peligro", "cuidado", "atención", "alerta",
    # Curiosidad y descubrimiento
    "truco", "hack", "cómo", "por qué", "sabías", "descubre", "aprende",
    # Positividad y transformación
    "increíble", "brutal", "bestial", "épico", "viral", "tremendo",
    # Acción directa
    "mira", "ojo", "escucha", "imagina", "piensa", "hazlo",
    # Siempre / nunca más
    "siempre", "antes de", "después de", "solución",
    # Cantidades de impacto
    "gratis", "fácil", "rápido", "inmediato",
    # Pronombres directos
    "tú", "todos", "nadie", "alguien",
    # Redes sociales
    "trending", "viral", "top", "número uno",
}

HOOK_KEYWORDS_EN = {
    "secret", "revealed", "exclusive", "hack", "never", "always", "look",
    "imagine", "warning", "danger", "incredible", "amazing", "viral",
    "easy", "free", "fast", "instant", "you", "nobody", "everyone",
    "before", "after", "solution", "trick", "discover", "learn",
}

# Patrones regex para detección de impacto numérico (ej. "3 razones", "10 errores")
IMPACT_NUMBER_PATTERN = re.compile(
    r"\b(\d{1,2})\s+(razones?|errores?|formas?|trucos?|secretos?|pasos?|tips?|"
    r"reasons?|mistakes?|ways?|tricks?|secrets?|steps?)\b",
    re.IGNORECASE
)

# Umbral de duración mínima para considerar una pausa como "dramática" (intencional)
DRAMATIC_PAUSE_MAX_SEC = 0.8  # ≤ 0.8s = pausa dramática → NO cortar
DEAD_SILENCE_MIN_SEC = 1.5    # ≥ 1.5s = silencio muerto → cortar agresivamente


def calculate_hook_score(transcript: TranscriptDocument | None, initial_window_sec: float = 5.0) -> float:
    """
    Calcula el Hook Score (0.0 a 1.0) evaluando los primeros 5 segundos del video (§17).

    Mejoras vs v1:
    - Vocabulario expandido (16 → 52 keywords)
    - Detección de preguntas retóricas (¿? y patrones de interrogación implícita)
    - Detección de números de alto impacto ("3 errores que...")
    - Pondera velocidad del habla en los primeros 2s (hook de alta energía)
    """
    if not transcript or not transcript.all_words:
        return 0.50

    initial_words = [w for w in transcript.all_words if w.start <= initial_window_sec]
    if not initial_words:
        return 0.40

    initial_text = " ".join(w.word for w in initial_words).lower()
    score = 0.50

    # 1. Presencia de preguntas (directas o retóricas)
    if "?" in initial_text or "¿" in initial_text:
        score += 0.20
    elif any(initial_text.startswith(kw) for kw in ["cómo", "por qué", "qué pasa", "sabes qué", "adivina"]):
        score += 0.12  # Pregunta retórica implícita

    # 2. Presencia de palabras gancho (ES + EN)
    all_hook_kw = HOOK_KEYWORDS_ES | HOOK_KEYWORDS_EN
    found_keywords = sum(1 for kw in all_hook_kw if kw in initial_text)
    score += min(0.25, found_keywords * 0.07)

    # 3. Detección de números de impacto ("10 errores", "3 secretos")
    if IMPACT_NUMBER_PATTERN.search(initial_text):
        score += 0.12

    # 4. Velocidad del habla ALTA en los primeros 2s = energía inmediata
    first_2s_words = [w for w in initial_words if w.start <= 2.0]
    if len(first_2s_words) >= 3:
        duration_2s = max(0.5, (first_2s_words[-1].end - first_2s_words[0].start))
        wpm_2s = len(first_2s_words) / (duration_2s / 60.0)
        if wpm_2s >= 160:
            score += 0.08  # Alta energía de apertura
        elif wpm_2s < 80:
            score -= 0.10  # Apertura lenta = baja retención

    # 5. Densidad de habla global en la ventana inicial (130-190 WPM = óptimo)
    duration = max(0.5, initial_words[-1].end - initial_words[0].start)
    wpm = len(initial_words) / (duration / 60.0)
    if 130 <= wpm <= 190:
        score += 0.08
    elif wpm < 90:
        score -= 0.12

    return round(max(0.10, min(1.0, score)), 2)


def calculate_redundancy_score(transcript: TranscriptDocument | None) -> float:
    """Calcula el índice de redundancia léxica y repetición (0.0 = conciso, 1.0 = muy redundante) (§19)."""
    if not transcript or transcript.word_count == 0:
        return 0.0

    fillers_count = sum(1 for w in transcript.all_words if w.is_filler)
    words = [w.word.lower() for w in transcript.all_words if len(w.word) >= 3]

    repeated_words_count = (len(words) - len(set(words))) if words else 0
    redundancy = (fillers_count + repeated_words_count) / transcript.word_count

    return round(max(0.0, min(1.0, redundancy)), 2)


def calculate_retention_score(
    transcript: TranscriptDocument | None,
    silence_intervals: list[SilenceInterval],
    total_duration: float,
) -> float:
    """Calcula la puntuación de retención estimada basada en fluidez y ritmo (§18)."""
    if total_duration <= 0:
        return 0.50

    # Solo los silencios muertos (>DEAD_SILENCE_MIN_SEC) penalizan la retención
    # Las pausas dramáticas cortas son técnica narrativa legítima
    dead_silence_dur = sum(
        s.duration for s in silence_intervals
        if s.severity in [SilenceSeverity.CUT_AGGRESSIVE, SilenceSeverity.CUT_SUGGESTED]
        and s.duration >= DEAD_SILENCE_MIN_SEC
    )

    dead_ratio = dead_silence_dur / total_duration
    base_retention = 0.85 - (dead_ratio * 0.60)

    if transcript and transcript.word_count > 0:
        overall_wpm = transcript.word_count / (total_duration / 60.0)
        if 130 <= overall_wpm <= 180:
            base_retention += 0.10
        elif overall_wpm < 100:
            base_retention -= 0.15

    return round(max(0.20, min(1.0, base_retention)), 2)


def extract_broll_keywords(transcript: TranscriptDocument | None, max_keywords: int = 5) -> list[str]:
    """Extrae palabras clave sustantivas relevantes para B-Roll contextual."""
    if not transcript or not transcript.all_words:
        return ["cinematic", "dynamic", "focus"]

    stopwords = {
        "este", "esta", "estos", "estas", "para", "como", "pero", "porque",
        "cuando", "donde", "quien", "hacer", "tener", "estar", "bueno", "todo",
        "más", "menos", "muy", "poco", "algo", "nada", "cada", "todo", "ello"
    }

    candidates: dict[str, int] = {}
    for w in transcript.all_words:
        clean = re.sub(r"[^\w]", "", w.word).lower()
        if len(clean) >= 5 and clean not in stopwords and not w.is_filler:
            candidates[clean] = candidates.get(clean, 0) + 1

    sorted_kw = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
    return [k for k, _ in sorted_kw[:max_keywords]] or ["background", "visual", "action"]


def _has_hook_energy(words: list, start_t: float, end_t: float) -> bool:
    """
    Determina si un segmento contiene palabras de alta energía o impacto.
    Segmentos con keywords de hook reciben ZOOM automático para mayor énfasis visual.
    """
    segment_words = [w for w in words if start_t <= w.start <= end_t]
    if not segment_words:
        return False
    segment_text = " ".join(w.word for w in segment_words).lower()
    all_hook_kw = HOOK_KEYWORDS_ES | HOOK_KEYWORDS_EN
    return any(kw in segment_text for kw in all_hook_kw) or bool(IMPACT_NUMBER_PATTERN.search(segment_text))


def _append_keep_or_zoom(
    decisions: list[EditDecision],
    start_t: float,
    end_t: float,
    reason_prefix: str = "Segmento vocal",
    transcript_words: list | None = None,
) -> None:
    """
    Divide un segmento largo (> 4.5s) en un plano normal y un zoom punch-in para dinamismo.
    Versión mejorada: aplica ZOOM también en segmentos cortos con alta energía semántica.
    """
    dur = round(end_t - start_t, 3)
    if dur <= 0.05:
        return

    words = transcript_words or []

    if dur > 4.5:
        # Segmentos largos: dividir en keep + zoom independientemente del contenido
        half_point = round(start_t + (dur / 2.0), 3)
        decisions.append(
            EditDecision(
                id=len(decisions) + 1,
                source_in=start_t,
                source_out=half_point,
                target_duration=round(half_point - start_t, 3),
                action=EditAction.KEEP,
                reason=f"{reason_prefix} (Plano normal)",
                confidence=0.95,
            )
        )
        decisions.append(
            EditDecision(
                id=len(decisions) + 1,
                source_in=half_point,
                source_out=end_t,
                target_duration=round(end_t - half_point, 3),
                action=EditAction.ZOOM_IN,
                zoom_scale=1.15,
                reason="Punch-in digital (1.15x) para retención visual y cambio de plano",
                confidence=0.90,
            )
        )
    elif _has_hook_energy(words, start_t, end_t):
        # Segmentos cortos con energía semántica alta → ZOOM automático
        decisions.append(
            EditDecision(
                id=len(decisions) + 1,
                source_in=start_t,
                source_out=end_t,
                target_duration=dur,
                action=EditAction.ZOOM_IN,
                zoom_scale=1.15,
                reason=f"{reason_prefix} con keyword de alto impacto (zoom semántico 1.15x)",
                confidence=0.88,
            )
        )
    else:
        decisions.append(
            EditDecision(
                id=len(decisions) + 1,
                source_in=start_t,
                source_out=end_t,
                target_duration=dur,
                action=EditAction.KEEP,
                reason=f"{reason_prefix} continuo",
                confidence=0.95,
            )
        )


class HeuristicEditor:
    """Genera decisiones de edición y un plan estructurado determinista basado en reglas."""

    @classmethod
    def generate_plan(
        cls,
        analysis: AnalysisResult,
        target_profile: str = "social",
        target_duration: float | None = None,
    ) -> EditorialPlan:
        """
        Genera un EditorialPlan estructurado aplicando reglas de ritmo, silencios y dinamismo.

        Mejoras v2:
        - Distingue pausas dramáticas intencionales (≤0.8s) de silencios muertos (≥1.5s)
        - Zoom semántico automático en segmentos con keywords de alto impacto
        - Muletillas solo se cortan si duran ≥ 0.20s (evitar micro-cortes artefactuales)
        """
        total_duration = analysis.media_info.duration_seconds if analysis.media_info else 0.0
        transcript_words = analysis.transcript.all_words if analysis.transcript else []

        ai_logger.info(f"Generando plan editorial heurístico para: {analysis.project_id} (duración: {total_duration:.2f}s)")

        # 1. Identificar intervalos a cortar
        cut_ranges: list[tuple[float, float, str]] = []

        for s in analysis.silence_intervals:
            # Solo cortar silencios MUERTOS (≥ 1.5s) — preservar pausas dramáticas cortas
            if s.severity == SilenceSeverity.CUT_AGGRESSIVE and s.duration >= DEAD_SILENCE_MIN_SEC:
                c_in = round(s.start + 0.04, 3)
                c_out = round(s.end - 0.04, 3)
                if c_out > c_in:
                    cut_ranges.append((c_in, c_out, f"Silencio muerto de {s.duration:.2f}s ({s.severity.value})"))
            elif s.severity == SilenceSeverity.CUT_SUGGESTED and s.duration >= DEAD_SILENCE_MIN_SEC:
                c_in = round(s.start + 0.06, 3)
                c_out = round(s.end - 0.06, 3)
                if c_out > c_in:
                    cut_ranges.append((c_in, c_out, f"Pausa larga de {s.duration:.2f}s ({s.severity.value})"))
            # Pausas ≤ 0.8s → pausa dramática intencional → conservar sin cortar

        # 2. Identificar muletillas aisladas de duración significativa (≥ 0.20s)
        if analysis.transcript:
            for w in analysis.transcript.all_words:
                if w.is_filler and (w.end - w.start) >= 0.20:
                    cut_ranges.append((w.start, w.end, f"Muletilla verbal: '{w.word}'"))

        # 3. Fusionar rangos de corte solapados
        cut_ranges.sort(key=lambda x: x[0])
        merged_cuts: list[tuple[float, float, str]] = []
        for c_start, c_end, reason in cut_ranges:
            if not merged_cuts:
                merged_cuts.append((c_start, c_end, reason))
            else:
                prev_start, prev_end, prev_reason = merged_cuts[-1]
                if c_start <= prev_end:
                    merged_cuts[-1] = (prev_start, max(prev_end, c_end), f"{prev_reason} + {reason}")
                else:
                    merged_cuts.append((c_start, c_end, reason))

        # 4. Construir lista ordenada de EditDecision (KEEP, CUT, ZOOM_IN)
        decisions: list[EditDecision] = []
        current_time = 0.0

        for c_start, c_end, reason in merged_cuts:
            # Segmento previo para mantener
            if c_start > current_time:
                _append_keep_or_zoom(
                    decisions, current_time, c_start,
                    reason_prefix="Segmento vocal",
                    transcript_words=transcript_words,
                )

            # Decisión de corte
            decisions.append(
                EditDecision(
                    id=len(decisions) + 1,
                    source_in=round(c_start, 3),
                    source_out=round(c_end, 3),
                    target_duration=0.0,
                    action=EditAction.CUT,
                    reason=reason,
                    confidence=0.90,
                )
            )
            current_time = c_end

        # Segmento final remanente
        if current_time < total_duration:
            _append_keep_or_zoom(
                decisions, current_time, total_duration,
                reason_prefix="Cierre",
                transcript_words=transcript_words,
            )

        # Si no hubo cortes necesarios en todo el video
        if not decisions:
            _append_keep_or_zoom(
                decisions, 0.0, total_duration,
                reason_prefix="Contenido íntegro",
                transcript_words=transcript_words,
            )

        # Métricas editoriales
        hook_score = calculate_hook_score(analysis.transcript)
        redundancy_score = calculate_redundancy_score(analysis.transcript)
        retention_score = calculate_retention_score(analysis.transcript, analysis.silence_intervals, total_duration)
        broll_keywords = extract_broll_keywords(analysis.transcript)

        final_duration = sum(d.target_duration for d in decisions if d.action != EditAction.CUT)

        plan = EditorialPlan(
            project_id=analysis.project_id,
            source_media_path=analysis.source_media_path,
            source_duration_seconds=total_duration,
            target_profile=target_profile,
            target_duration_seconds=round(final_duration, 3),
            hook_score=hook_score,
            retention_score=retention_score,
            redundancy_score=redundancy_score,
            total_cuts_count=sum(1 for d in decisions if d.action == EditAction.CUT),
            total_zooms_count=sum(1 for d in decisions if d.action == EditAction.ZOOM_IN),
            summary=(
                f"Plan editorial {target_profile}: {len(decisions)} decisiones, "
                f"reducción de {total_duration:.1f}s a {final_duration:.1f}s "
                f"(Hook: {hook_score:.2f}, Retención: {retention_score:.2f})."
            ),
            decisions=decisions,
            suggested_broll_keywords=broll_keywords,
        )

        ai_logger.info(f"Plan editorial heurístico finalizado: {len(decisions)} decisiones (Duración estimada: {final_duration:.2f}s)")
        return plan
