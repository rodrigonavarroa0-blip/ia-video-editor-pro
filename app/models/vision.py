"""Modelos de datos para visión computacional, seguimiento facial y reencuadre."""

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Caja delimitadora normalizada (0.0 a 1.0)."""
    x_min: float
    y_min: float
    width: float
    height: float


class FaceTrackPoint(BaseModel):
    """Punto temporal de detección facial."""
    timestamp: float
    bbox: BoundingBox
    center_x: float
    center_y: float
    confidence: float = 1.0
    is_speaking: bool = True


class FaceTrack(BaseModel):
    """Seguimiento temporal completo de un sujeto en el video."""
    track_id: int
    points: list[FaceTrackPoint] = Field(default_factory=list)
    average_confidence: float = 1.0


class ReframeKeyframe(BaseModel):
    """Keyframe de posición para smart reframing (16:9 a 9:16)."""
    timestamp: float
    crop_x: float = Field(..., description="Posición horizontal normalizada del recorte (0.0 a 1.0)")
    crop_y: float = Field(..., description="Posición vertical normalizada del recorte (0.0 a 1.0)")
    crop_width: float
    crop_height: float
    scale: float = 1.0
