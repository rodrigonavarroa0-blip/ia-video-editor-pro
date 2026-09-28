"""Fachada unificada del motor editorial inteligente (Dual-Engine AI / Heuristic)."""


from app.ai.gemini_client import GeminiEditorialClient
from app.ai.heuristic_editor import HeuristicEditor
from app.core.logger import ai_logger
from app.models.analysis import AnalysisResult
from app.models.editorial import EditorialPlan


class EditorialEngine:
    """Orquesta la toma de decisiones editoriales combinando Gemini 3.7 Flash y Heurística Local."""

    @classmethod
    def generate_plan(
        cls,
        analysis: AnalysisResult,
        target_profile: str = "social",
        target_duration: float | None = None,
        force_heuristic: bool = False,
    ) -> EditorialPlan:
        """
        Genera un plan de edición estructurado (EditorialPlan):
        1. Si force_heuristic=False y hay GEMINI_API_KEY, solicita a Gemini 3.7 Flash.
        2. Si falla o no está disponible, utiliza el motor heurístico local determinista.
        """
        if not force_heuristic and GeminiEditorialClient.is_available():
            ai_logger.info("Intentando generar plan editorial con Gemini 3.7 Flash...")
            plan = GeminiEditorialClient.generate_editorial_plan(
                analysis=analysis,
                target_profile=target_profile,
                target_duration=target_duration,
            )
            if plan is not None:
                return plan

        ai_logger.info("Utilizando motor editorial heurístico local...")
        return HeuristicEditor.generate_plan(
            analysis=analysis,
            target_profile=target_profile,
            target_duration=target_duration,
        )
