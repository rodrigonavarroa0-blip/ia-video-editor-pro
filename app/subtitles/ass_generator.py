"""Generador de subtítulos cinéticos en formato Advanced SubStation Alpha (.ass) (§30, §31)."""

from pathlib import Path
from typing import ClassVar

from app.core.logger import render_logger
from app.models.subtitles import SubtitlePreset, SubtitleStyleConfig
from app.models.transcript import TranscriptDocument, WordTimestamp


class ASSGenerator:
    """Genera scripts ASS v4.00+ con tipografía cinética y resaltado fonético palabra por palabra."""

    PRESETS: ClassVar[dict[SubtitlePreset, SubtitleStyleConfig]] = {
        SubtitlePreset.HORMOZI: SubtitleStyleConfig(
            preset=SubtitlePreset.HORMOZI,
            font_name="Impact",
            font_size=60,
            primary_color="&H00FFFFFF",     # Blanco
            highlight_color="&H0000FFFF",   # Amarillo oro
            outline_color="&H00000000",     # Negro
            outline_width=4.5,
            shadow_width=2.5,
            uppercase=True,
            max_words_per_line=3,
            margin_v=240,
            alignment=2,
        ),
        SubtitlePreset.MINIMAL: SubtitleStyleConfig(
            preset=SubtitlePreset.MINIMAL,
            font_name="Arial",
            font_size=42,
            primary_color="&H00FFFFFF",
            highlight_color="&H0000FFFF",
            outline_color="&H00000000",
            outline_width=2.0,
            shadow_width=0.0,
            uppercase=False,
            max_words_per_line=5,
            margin_v=140,
            alignment=2,
        ),
        SubtitlePreset.BOLD_POP: SubtitleStyleConfig(
            preset=SubtitlePreset.BOLD_POP,
            font_name="Arial Black",
            font_size=54,
            primary_color="&H00FFFFFF",
            highlight_color="&H0000FF00",   # Verde neón
            outline_color="&H00000000",
            outline_width=3.5,
            shadow_width=2.0,
            uppercase=True,
            max_words_per_line=3,
            margin_v=200,
            alignment=2,
        ),
        SubtitlePreset.CINEMA: SubtitleStyleConfig(
            preset=SubtitlePreset.CINEMA,
            font_name="Times New Roman",
            font_size=38,
            primary_color="&H00FFFFFF",
            highlight_color="&H00FFFFFF",
            outline_color="&H00000000",
            outline_width=1.5,
            shadow_width=1.0,
            uppercase=False,
            max_words_per_line=6,
            margin_v=90,
            alignment=2,
        ),
    }

    @classmethod
    def format_timestamp(cls, seconds: float) -> str:
        """Convierte segundos a formato ASS estándar H:MM:SS.cs (centisegundos)."""
        sec = max(0.0, float(seconds))
        hours = int(sec // 3600)
        minutes = int((sec % 3600) // 60)
        secs = int(sec % 60)
        centis = round((sec - int(sec)) * 100)
        if centis >= 100:
            centis = 99
        return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

    @classmethod
    def get_style_config(cls, preset_name: str) -> SubtitleStyleConfig:
        """Obtiene la configuración del estilo predefinido."""
        try:
            p = SubtitlePreset(preset_name.lower())
            return cls.PRESETS.get(p, cls.PRESETS[SubtitlePreset.HORMOZI])
        except ValueError:
            return cls.PRESETS[SubtitlePreset.HORMOZI]

    @classmethod
    def generate_ass(
        cls,
        transcript: TranscriptDocument,
        output_file: Path,
        style_config: SubtitleStyleConfig | None = None,
    ) -> Path:
        """
        Genera el archivo .ass con efectos cinéticos sincronizados a nivel de centésima de segundo.
        """
        cfg = style_config or cls.PRESETS[SubtitlePreset.HORMOZI]
        out_path = Path(output_file).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        render_logger.info(f"Generando subtítulos ASS cinéticos ({cfg.preset.value}) en: {out_path.name}")

        format_line = (
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
        )
        style_line = (
            f"Style: Default,{cfg.font_name},{cfg.font_size},{cfg.primary_color},{cfg.highlight_color},"
            f"{cfg.outline_color},{cfg.back_color},{1 if cfg.bold else 0},{1 if cfg.italic else 0},0,0,"
            f"100,100,0,0,1,{cfg.outline_width},{cfg.shadow_width},{cfg.alignment},"
            f"{cfg.margin_l},{cfg.margin_r},{cfg.margin_v},1"
        )

        # 1. Cabecera Script Info
        lines = [
            "[Script Info]",
            "Title: IA Video Editor Pro Kinetic Subtitles",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            f"PlayResX: {cfg.play_res_x}",
            f"PlayResY: {cfg.play_res_y}",
            "",
            "[V4+ Styles]",
            format_line,
            style_line,
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]

        # 2. Agrupar palabras en chunks cinéticos
        all_words = transcript.all_words
        if not all_words and transcript.segments:
            # Reconstruir all_words a partir de los segmentos si está vacío
            for seg in transcript.segments:
                all_words.extend(seg.words)

        if not all_words:
            render_logger.warning("No hay palabras en la transcripción para generar subtítulos ASS.")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            return out_path

        chunks = cls._group_words_into_chunks(all_words, max_words=cfg.max_words_per_line)

        # 3. Generar eventos de diálogo con iluminación activa
        for chunk in chunks:
            if not chunk:
                continue

            for active_idx, active_word in enumerate(chunk):
                w_start = cls.format_timestamp(active_word.start)
                # La palabra activa brilla hasta su final o hasta que empiece la siguiente
                if active_idx < len(chunk) - 1:
                    w_end = cls.format_timestamp(chunk[active_idx + 1].start)
                else:
                    w_end = cls.format_timestamp(active_word.end + 0.10)

                # Construir el texto del chunk con la palabra activa iluminada
                formatted_words = []
                for idx, w in enumerate(chunk):
                    raw_text = w.word.strip()
                    if cfg.uppercase:
                        raw_text = raw_text.upper()

                    # Escapar llaves ASS
                    raw_text = raw_text.replace("{", "(").replace("}", ")")

                    if idx == active_idx:
                        # Palabra activa resaltada en highlight_color con pop sutil
                        formatted_words.append(
                            f"{{\\c{cfg.highlight_color}&\\t(0,80,\\fscx108\\fscy108)}}{raw_text}{{\\r}}"
                        )
                    else:
                        formatted_words.append(raw_text)

                dialogue_text = " ".join(formatted_words)
                lines.append(f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{dialogue_text}")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        render_logger.info(f"Subtítulos ASS generados exitosamente ({len(chunks)} bloques cinéticos).")
        return out_path

    @classmethod
    def _group_words_into_chunks(
        cls,
        words: list[WordTimestamp],
        max_words: int = 3,
        max_pause_sec: float = 0.45,
    ) -> list[list[WordTimestamp]]:
        """Agrupa las palabras en bloques cortos respetando pausas y puntuación."""
        chunks: list[list[WordTimestamp]] = []
        current_chunk: list[WordTimestamp] = []

        for i, w in enumerate(words):
            current_chunk.append(w)

            is_full = len(current_chunk) >= max_words
            has_long_pause = False
            if i < len(words) - 1 and (words[i + 1].start - w.end) >= max_pause_sec:
                has_long_pause = True

            has_sentence_end = w.word.rstrip().endswith((".", "!", "?", "...", ":"))

            if is_full or has_long_pause or has_sentence_end:
                chunks.append(current_chunk)
                current_chunk = []

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
