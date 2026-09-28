"""Modelos de datos para métricas acústicas y niveles sonoros."""


from pydantic import BaseModel, Field


class AudioMetrics(BaseModel):
    """Métricas técnicas acústicas del archivo de audio analizado."""
    integrated_lufs: float = Field(..., description="Loudness integrada en LUFS (EBU R128)")
    true_peak_db: float = Field(..., description="Pico máximo real en dBTP")
    lra_lu: float = Field(default=0.0, description="Loudness Range en LU")
    rms_db: float = Field(default=-20.0, description="Nivel RMS promedio")
    speech_energy_ratio: float = Field(default=0.8, ge=0.0, le=1.0)
    noise_floor_db: float | None = None
    target_lufs: float = -14.0
    gain_adjustment_db: float = 0.0
