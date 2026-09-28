"""Sistema de logs estructurados y emisión de eventos NDJSON para IA Video Editor Pro."""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

console = Console()

_channels: dict[str, logging.Logger] = {}
_default_log_dir: Path = Path(__file__).resolve().parent.parent.parent / "logs"


def get_channel_logger(
    channel_name: str = "app",
    log_dir: Path | None = None,
    log_level: int = logging.INFO,
) -> logging.Logger:
    """Obtiene o inicializa un logger específico para un canal (app, analysis, ffmpeg, ai, render)."""
    global _channels

    target_dir = Path(log_dir) if log_dir is not None else _default_log_dir
    cache_key = f"{channel_name}_{target_dir}"

    if cache_key in _channels:
        return _channels[cache_key]

    logger_name = f"iva.{channel_name}"
    channel_logger = logging.getLogger(logger_name)
    channel_logger.setLevel(log_level)
    channel_logger.handlers.clear()

    # Formateador de consola Rich
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=False,
        rich_tracebacks=True,
    )
    rich_handler.setLevel(log_level)
    channel_logger.addHandler(rich_handler)

    # Formateador de archivo de logs en logs/<channel>.log
    target_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(target_dir / f"{channel_name}.log", encoding="utf-8")
    file_formatter = logging.Formatter(
        '{"time": "%(asctime)s", "channel": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    channel_logger.addHandler(file_handler)

    _channels[cache_key] = channel_logger
    return channel_logger


def emit_ipc_event(
    event_type: str,
    payload: dict[str, Any],
    progress: float | None = None,
) -> None:
    """Emite un evento estructurado en formato NDJSON a stdout para el frontend de Tauri."""
    event_data = {
        "timestamp": time.time(),
        "event": event_type,
        "payload": payload,
    }
    if progress is not None:
        event_data["progress"] = max(0.0, min(1.0, progress))

    sys.stdout.write(f"__IVA_EVENT__:{json.dumps(event_data, ensure_ascii=False)}\n")
    sys.stdout.flush()


# Canales de log estándar
logger = get_channel_logger("app")
analysis_logger = get_channel_logger("analysis")
ffmpeg_logger = get_channel_logger("ffmpeg")
ai_logger = get_channel_logger("ai")
render_logger = get_channel_logger("render")
