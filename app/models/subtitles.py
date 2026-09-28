"""Modelos de datos para estilos y configuración de subtítulos cinéticos."""

from enum import Enum

from pydantic import BaseModel


class SubtitlePreset(str, Enum):
    HORMOZI = "hormozi"
    MINIMAL = "minimal"
    BOLD_POP = "bold_pop"
    CINEMA = "cinema"


class SubtitleStyleConfig(BaseModel):
    """Configuración tipográfica y de animación para subtítulos ASS."""
    preset: SubtitlePreset = SubtitlePreset.HORMOZI
    font_name: str = "Impact"
    font_size: int = 52
    primary_color: str = "&H00FFFFFF"     # Blanco (&HAABBGGRR)
    highlight_color: str = "&H0000FFFF"   # Amarillo oro
    secondary_color: str = "&H0000FF00"   # Verde neón (opcional)
    outline_color: str = "&H00000000"     # Negro puro
    back_color: str = "&H80000000"        # Sombra semi-transparente
    outline_width: float = 4.0
    shadow_width: float = 2.0
    bold: bool = True
    italic: bool = False
    alignment: int = 2                    # 2 = Bottom Center, 5 = Middle Center
    margin_l: int = 30
    margin_r: int = 30
    margin_v: int = 140                   # Espacio de seguridad vertical
    uppercase: bool = True
    max_words_per_line: int = 3
    play_res_x: int = 1080
    play_res_y: int = 1920
