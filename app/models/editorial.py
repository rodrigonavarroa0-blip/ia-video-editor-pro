"""Modelos de datos para análisis editorial, decisiones y control de calidad (§22, §23)."""

from enum import Enum

from pydantic import BaseModel, Field


class SilenceSeverity(str, Enum):
    KEEP = "keep"
    EVALUATE = "evaluate"
    CUT_SUGGESTED = "cut_suggested"
    CUT_AGGRESSIVE = "cut_aggressive"


class SilenceInterval(BaseModel):
    """Intervalo de silencio detectado en el audio."""
    start: float
    end: float
    duration: float
    severity: SilenceSeverity = SilenceSeverity.CUT_SUGGESTED
    db_level: float = -40.0


class SceneBoundary(BaseModel):
    """Cambio de plano / corte de cámara detectado en el video."""
    start: float
    end: float
    duration: float
    score: float = Field(default=0.8, ge=0.0, le=1.0)


class ActionType(str, Enum):
    KEEP = "keep"
    CUT = "cut"
    ZOOM = "zoom"
    ZOOM_IN = "zoom_in"
    BROLL = "broll"
    B_ROLL = "b_roll"
    SPEED = "speed"
    SPEED_UP = "speed_up"
    EMPHASIZE = "emphasize"


# Alias para compatibilidad
EditAction = ActionType


class EditDecision(BaseModel):
    """Decisión editorial unitaria sobre un rango temporal del video."""
    id: int | None = None
    start: float | None = None
    end: float | None = None
    source_in: float | None = None
    source_out: float | None = None
    target_duration: float = 0.0
    action: ActionType = ActionType.KEEP
    reason: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    hook_score: float | None = None
    retention_score: float | None = None
    zoom_scale: float | None = 1.15
    applied: bool = True

    def model_post_init(self, __context):
        # Sincronizar start/end con source_in/source_out
        if self.source_in is None and self.start is not None:
            self.source_in = self.start
        elif self.start is None and self.source_in is not None:
            self.start = self.source_in

        if self.source_out is None and self.end is not None:
            self.source_out = self.end
        elif self.end is None and self.source_out is not None:
            self.end = self.source_out


class EditorialPlan(BaseModel):
    """Plan editorial global generado por el motor de análisis."""
    version: int = 1
    project_id: str
    source_media_path: str | None = ""
    source_duration_seconds: float | None = 0.0
    target_format: str = "9:16"
    target_profile: str = "social"
    pacing_mode: str | None = "social"
    decisions: list[EditDecision] = Field(default_factory=list)
    target_duration_seconds: float = 0.0
    estimated_final_duration_seconds: float | None = None
    hook_score: float = 0.0
    retention_score: float = 0.0
    redundancy_score: float = 0.0
    overall_hook_score: float | None = None
    overall_retention_score: float | None = None
    total_cuts_count: int = 0
    total_zooms_count: int = 0
    summary: str = ""
    suggested_broll_keywords: list[str] = Field(default_factory=list)

    def model_post_init(self, __context):
        if self.estimated_final_duration_seconds is None:
            self.estimated_final_duration_seconds = self.target_duration_seconds
        if self.overall_hook_score is None:
            self.overall_hook_score = self.hook_score
        if self.overall_retention_score is None:
            self.overall_retention_score = self.retention_score


class QualityStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class QualityIssue(BaseModel):
    """Problema detectado durante la verificación técnica."""
    category: str  # e.g., "audio_clipping", "black_frames", "sync", "safe_area"
    severity: str  # "info", "warning", "error"
    timestamp_seconds: float | None = None
    message: str


class QualityReport(BaseModel):
    """Reporte de control de calidad previo a la exportación final."""
    status: QualityStatus = QualityStatus.PASS
    professional_edit_score: float = Field(default=95.0, ge=0.0, le=100.0)
    audio_score: float = 95.0
    pacing_score: float = 90.0
    visual_stability_score: float = 95.0
    issues: list[QualityIssue] = Field(default_factory=list)
    can_render: bool = True
