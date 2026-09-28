"""Interfaz de Línea de Comandos (CLI) de IA Video Editor Pro."""

import sys
import webbrowser
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from app.analyzers.media_probe import MediaProbe
from app.analyzers.scene_detector import SceneDetector
from app.analyzers.silence_detector import SilenceDetector
from app.audio.loudness import LoudnessProcessor
from app.core.analysis import run_full_analysis
from app.core.audio_pipeline import process_project_audio
from app.core.config import config
from app.core.editorial import create_editorial_plan_for_project
from app.core.ingest import ingest_media
from app.core.logger import emit_ipc_event, logger
from app.core.project import ProjectManager
from app.core.render import render_final_video_for_project
from app.core.subtitles import burn_project_subtitles, generate_subtitles_for_project
from app.core.timeline import build_and_export_timeline_for_project
from app.core.transcription import transcribe_project
from app.core.vision import run_vision_tracking_for_project
from app.packaging.macos_packager import MacOSPackager
from app.qa.golden_runner import run_all_golden_tests
from app.server.bridge import run_bridge_server
from app.utils.ffmpeg import FFmpegManager
from app.vision.face_tracker import FaceTracker

app = typer.Typer(
    name="iva",
    help="IA Video Editor Pro — Motor de edición automatizada asistida por IA.",
    add_completion=False,
)
console = Console()

__version__ = "0.1.0"


def version_callback(value: bool):
    if value:
        console.print(f"[bold cyan]IA Video Editor Pro[/bold cyan] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        help="Muestra la versión de IA Video Editor Pro.",
        callback=version_callback,
        is_eager=True,
    ),
):
    """Punto de entrada general de la CLI."""


@app.command()
def info():
    """Muestra información del entorno técnico, hardware y perfiles disponibles."""
    table = Table(title="IA Video Editor Pro — Estado del Sistema")
    table.add_column("Componente", style="cyan", no_wrap=True)
    table.add_column("Detalle / Valor", style="green")

    table.add_row("Versión Core", f"v{__version__}")
    table.add_row("Python Runtime", f"{sys.version.split()[0]}")
    table.add_row("Plataforma", sys.platform)
    table.add_row("Apple VideoToolbox", "✓ Disponible" if FFmpegManager.has_videotoolbox() else "✗ Deshabilitado / CPU Fallback")
    table.add_row("Encoder Seleccionado", FFmpegManager.get_optimal_video_encoder())
    table.add_row("Modelo IA", str(config.get("ai.model", "gemini-3.7-flash")))
    table.add_row("Formato por defecto", str(config.get("project.format", "9:16")))
    table.add_row("Whisper Model", str(config.get("speech.model", "small")))

    console.print(table)


@app.command()
def init_project(
    project_dir: Path = typer.Argument(..., help="Ruta del directorio donde se creará el proyecto."),
    name: str = typer.Option("Mi Video", "--name", "-n", help="Nombre del proyecto."),
    profile: str = typer.Option("social", "--profile", "-p", help="Perfil de edición (social, youtube, corporate, podcast)."),
):
    """Inicializa un nuevo proyecto con la estructura no destructiva estándar."""
    try:
        path = ProjectManager.create_project(project_dir=project_dir, project_name=name, profile=profile)
        console.print(f"[bold green]✓[/bold green] Proyecto '[bold]{name}[/bold]' creado exitosamente en [cyan]{path}[/cyan]")
        emit_ipc_event("project_created", {"path": str(path), "name": name, "profile": profile}, progress=1.0)
    except Exception as e:
        console.print(f"[bold red]✗ Error al crear proyecto:[/bold red] {e}")
        logger.exception("Fallo al inicializar proyecto")
        raise typer.Exit(code=1)


@app.command()
def probe(
    file_path: Path = typer.Argument(..., help="Ruta del archivo de video o audio a inspeccionar."),
):
    """Inspecciona las propiedades técnicas de un archivo multimedia (MediaProbe)."""
    try:
        media_info = MediaProbe.probe(file_path)

        table = Table(title=f"Inspección Técnica: {media_info.file_name}")
        table.add_column("Propiedad", style="cyan", no_wrap=True)
        table.add_column("Valor", style="magenta")

        table.add_row("Ruta", media_info.file_path)
        table.add_row("Tamaño", f"{media_info.file_size_bytes / (1024 * 1024):.2f} MB")
        table.add_row("Formato Contenedor", media_info.format_name)
        table.add_row("Duración", f"{media_info.duration_seconds:.2f} s")

        if media_info.primary_video:
            v = media_info.primary_video
            table.add_row("Video Codec", v.codec_name)
            table.add_row("Resolución", f"{v.width} x {v.height} ({v.aspect_ratio})")
            table.add_row("Tasa de Cuadros (FPS)", f"{v.fps:.2f}")
            if v.pixel_format:
                table.add_row("Formato de Píxel", v.pixel_format)

        if media_info.primary_audio:
            a = media_info.primary_audio
            table.add_row("Audio Codec", a.codec_name)
            table.add_row("Sample Rate", f"{a.sample_rate} Hz")
            table.add_row("Canales de Audio", str(a.channels))

        console.print(table)
        emit_ipc_event("media_probed", media_info.model_dump(), progress=1.0)
    except Exception as e:
        console.print(f"[bold red]✗ Error durante el probing:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def ingest(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto donde se ingresará el video."),
    video_file: Path = typer.Argument(..., help="Ruta del archivo de video a ingestar."),
    no_copy: bool = typer.Option(False, "--no-copy", help="No duplicar el archivo físico si es posible vincularlo."),
):
    """Ingesta un video en el proyecto, generando proxy 720p y extrayendo audio WAV."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Iniciando ingesta...", total=100)

            def _progress_cb(stage: str, p: float):
                desc_map = {
                    "probing": "Inspeccionando metadatos técnicos...",
                    "generating_proxy": "Generando proxy 720p...",
                    "extracting_audio": "Extrayendo audio WAV (44.1kHz)...",
                    "completed": "Ingesta completada.",
                }
                progress.update(task, description=desc_map.get(stage, stage), completed=int(p * 100))

            result = ingest_media(
                project_dir=project_dir,
                source_video_path=video_file,
                copy_raw=not no_copy,
                progress_callback=_progress_cb,
            )

        console.print(Panel.fit(
            f"[bold green]✓ Ingesta completada con éxito[/bold green]\n"
            f"[cyan]Archivo:[/cyan] {result['file_name']}\n"
            f"[cyan]Proxy 720p:[/cyan] {result['proxy_path']}\n"
            f"[cyan]Audio WAV:[/cyan] {result['audio_path']}\n"
            f"[cyan]Duración:[/cyan] {result['duration_seconds']:.2f} s",
            title="Ingest Summary"
        ))
    except Exception as e:
        console.print(f"[bold red]✗ Error en la ingesta:[/bold red] {e}")
        logger.exception("Error al ingestar video")
        raise typer.Exit(code=1)


@app.command()
def transcribe(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto a transcribir."),
    model: str | None = typer.Option(None, "--model", "-m", help="Tamaño del modelo Whisper (tiny, base, small, medium)."),
    language: str | None = typer.Option(None, "--language", "-l", help="Código de idioma (es, en, etc.)."),
):
    """Transcribe el audio del proyecto con faster-whisper y genera analysis/transcript.json."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Transcribiendo audio con faster-whisper...", total=100)

            def _progress_cb(p: float):
                progress.update(task, completed=int(p * 100))

            doc = transcribe_project(
                project_dir=project_dir,
                model_size=model,
                language=language,
                progress_callback=_progress_cb,
            )

        table = Table(title=f"Transcripción — {doc.word_count} palabras ({doc.language.upper()})")
        table.add_column("ID", style="cyan", width=5)
        table.add_column("Tiempo", style="green", width=16)
        table.add_column("Texto", style="white")
        table.add_column("WPM", style="yellow", width=8)

        for seg in doc.segments[:15]:
            time_str = f"{seg.start:.2f}s - {seg.end:.2f}s"
            table.add_row(str(seg.id), time_str, seg.text, f"{seg.speech_rate_wpm:.0f}")

        if len(doc.segments) > 15:
            table.add_row("...", "...", f"y {len(doc.segments) - 15} segmentos más...", "...")

        console.print(table)
        console.print(f"[bold green]✓[/bold green] Transcripción guardada en: [cyan]{project_dir}/analysis/transcript.json[/cyan]")
    except Exception as e:
        console.print(f"[bold red]✗ Error en la transcripción:[/bold red] {e}")
        logger.exception("Error al transcribir audio")
        raise typer.Exit(code=1)


@app.command()
def detect_scenes(
    video_file: Path = typer.Argument(..., help="Ruta del archivo de video a analizar."),
    threshold: float = typer.Option(0.35, "--threshold", "-t", help="Umbral de diferencia de histograma."),
):
    """Detecta cortes de plano en un video con OpenCV."""
    try:
        scenes = SceneDetector.detect_scenes(video_file, threshold=threshold)
        table = Table(title=f"Detección de Escenas — {len(scenes)} planos")
        table.add_column("Plano #", style="cyan")
        table.add_column("Rango Temporal", style="green")
        table.add_column("Duración", style="yellow")
        table.add_column("Confianza", style="magenta")

        for idx, s in enumerate(scenes, 1):
            table.add_row(str(idx), f"{s.start:.2f}s - {s.end:.2f}s", f"{s.duration:.2f}s", f"{s.score:.2f}")

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]✗ Error detectando escenas:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def detect_silence(
    audio_file: Path = typer.Argument(..., help="Ruta del archivo de audio WAV a analizar."),
    threshold_db: float = typer.Option(-38.0, "--threshold", "-t", help="Umbral de silencio en dBFS."),
):
    """Analiza y clasifica intervalos de silencio multinivel en un archivo de audio."""
    try:
        intervals = SilenceDetector.detect_silence(audio_file, threshold_db=threshold_db)
        table = Table(title=f"Análisis de Silencios — {len(intervals)} intervalos")
        table.add_column("#", style="cyan")
        table.add_column("Rango", style="green")
        table.add_column("Duración", style="yellow")
        table.add_column("Nivel dBFS", style="white")
        table.add_column("Severidad Editorial", style="bold red")

        for idx, s in enumerate(intervals, 1):
            sev_color = {
                "keep": "[green]KEEP[/green]",
                "evaluate": "[yellow]EVALUATE[/yellow]",
                "cut_suggested": "[bold orange1]CUT_SUGGESTED[/bold orange1]",
                "cut_aggressive": "[bold red]CUT_AGGRESSIVE[/bold red]",
            }.get(s.severity.value, s.severity.value)

            table.add_row(str(idx), f"{s.start:.2f}s - {s.end:.2f}s", f"{s.duration:.2f}s", f"{s.db_level:.1f} dBFS", sev_color)

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]✗ Error detectando silencios:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def track_faces(
    video_file: Path = typer.Argument(..., help="Ruta del archivo de video a procesar con Face Tracking."),
):
    """Detecta y rastrea los rostros de los sujetos a lo largo del video."""
    try:
        with console.status("[bold cyan]Rastreando rostros con visión computacional...[/bold cyan]"):
            tracks = FaceTracker.track_faces(video_file)

        table = Table(title=f"Face Tracking — {len(tracks)} sujetos detectados")
        table.add_column("Sujeto ID", style="cyan")
        table.add_column("Fotogramas Clave", style="green")
        table.add_column("Confianza Media", style="yellow")

        for t in tracks:
            table.add_row(str(t.track_id), f"{len(t.points)} detecciones", f"{t.average_confidence:.2f}")

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]✗ Error en face tracking:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def reframe(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto a reencuadrar."),
    format: str = typer.Option("9:16", "--format", "-f", help="Formato de aspecto objetivo (9:16, 1:1, 4:5)."),
):
    """Ejecuta el pipeline de Face Tracking y Smart Reframing 9:16 generando keyframes."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Iniciando Smart Reframing...", total=100)

            def _progress_cb(stage: str, p: float):
                desc_map = {
                    "face_tracking": "Rastreando sujetos en video...",
                    "smart_reframing": "Calculando ventana dinámica 9:16 con suavizado...",
                    "completed": "Reencuadre completado.",
                }
                progress.update(task, description=desc_map.get(stage, stage), completed=int(p * 100))

            tracks, keyframes = run_vision_tracking_for_project(
                project_dir=project_dir,
                target_format=format,
                progress_callback=_progress_cb,
            )

        console.print(Panel.fit(
            f"[bold green]✓ Smart Reframing Completado Exitosamente[/bold green]\n"
            f"[cyan]Formato Objetivo:[/cyan] {format}\n"
            f"[cyan]Sujetos Rastreados:[/cyan] {len(tracks)}\n"
            f"[cyan]Keyframes 9:16 Generados:[/cyan] {len(keyframes)}\n"
            f"[cyan]Keyframes guardados en:[/cyan] {project_dir}/analysis/reframing.json",
            title="Vision Tracking Summary"
        ))
    except Exception as e:
        console.print(f"[bold red]✗ Error en Smart Reframing:[/bold red] {e}")
        logger.exception("Error al reencuadrar proyecto")
        raise typer.Exit(code=1)


@app.command()
def measure_audio(
    audio_file: Path = typer.Argument(..., help="Ruta del archivo de audio a medir."),
    target: float = typer.Option(-14.0, "--target", "-t", help="Nivel LUFS objetivo."),
):
    """Mide la sonoridad integrada (LUFS EBU R128), LRA y True Peak en dBTP."""
    try:
        metrics = LoudnessProcessor.measure_loudness(audio_file, target_lufs=target)
        table = Table(title=f"Medición Acústica EBU R128 — {audio_file.name}")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="magenta")

        table.add_row("Sonoridad Integrada (LUFS)", f"{metrics.integrated_lufs:.2f} LUFS")
        table.add_row("True Peak Máximo", f"{metrics.true_peak_db:.2f} dBTP")
        table.add_row("Rango Dinámico (LRA)", f"{metrics.lra_lu:.2f} LU")
        table.add_row("Nivel RMS", f"{metrics.rms_db:.2f} dBFS")
        table.add_row("Ajuste Necesario para Target", f"{metrics.gain_adjustment_db:+.2f} dB")

        console.print(table)
    except Exception as e:
        console.print(f"[bold red]✗ Error midiendo audio:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def enhance_audio(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto a procesar."),
    target: float = typer.Option(-14.0, "--target", "-t", help="Nivel LUFS objetivo."),
):
    """Ejecuta el pipeline de masterización de audio (High-Pass + EQ + Normalización LUFS)."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Masterizando audio...", total=100)

            def _progress_cb(stage: str, p: float):
                desc_map = {
                    "measuring_raw": "Midiendo sonoridad inicial...",
                    "voice_enhancement": "Aplicando Voice Enhancement (High-Pass 80Hz + EQ)...",
                    "loudness_normalization": "Normalizando a EBU R128 (-14 LUFS / -1 dBTP)...",
                    "completed": "Audio masterizado con éxito.",
                }
                progress.update(task, description=desc_map.get(stage, stage), completed=int(p * 100))

            metrics = process_project_audio(
                project_dir=project_dir,
                target_lufs=target,
                progress_callback=_progress_cb,
            )

        console.print(Panel.fit(
            f"[bold green]✓ Audio Masterizado Exitosamente[/bold green]\n"
            f"[cyan]Sonoridad Final:[/cyan] [bold]{metrics.integrated_lufs:.1f} LUFS[/bold]\n"
            f"[cyan]Pico Real (True Peak):[/cyan] [bold]{metrics.true_peak_db:.1f} dBTP[/bold] (Límite: -1.0 dBTP)\n"
            f"[cyan]Rango Dinámico (LRA):[/cyan] {metrics.lra_lu:.1f} LU\n"
            f"[cyan]Ganancia Aplicada:[/cyan] {metrics.gain_adjustment_db:+.1f} dB\n"
            f"[cyan]Audio Master:[/cyan] {project_dir}/cache/audio_master.wav",
            title="Audio Mastering Summary"
        ))
    except Exception as e:
        console.print(f"[bold red]✗ Error masterizando audio:[/bold red] {e}")
        logger.exception("Error al masterizar audio")
        raise typer.Exit(code=1)


@app.command()
def generate_subtitles(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto."),
    style: str = typer.Option("hormozi", "--style", "-s", help="Estilo de subtítulos (hormozi, minimal, bold_pop, cinema)."),
    max_words: int = typer.Option(3, "--max-words", "-w", help="Máximo de palabras por línea cinética."),
):
    """Genera subtítulos cinéticos (.ass) y formatos sidecar (.srt, .vtt)."""
    try:
        subs = generate_subtitles_for_project(project_dir, style=style, max_words=max_words)
        console.print(Panel.fit(
            f"[bold green]✓ Subtítulos Cinéticos Generados Exitosamente[/bold green]\n"
            f"[cyan]Estilo Visual:[/cyan] {style}\n"
            f"[cyan]ASS Cinético:[/cyan] {subs['ass']}\n"
            f"[cyan]Sidecar SRT:[/cyan] {subs['srt']}\n"
            f"[cyan]Sidecar WebVTT:[/cyan] {subs['vtt']}",
            title="Subtitles Summary"
        ))
    except Exception as e:
        console.print(f"[bold red]✗ Error generando subtítulos:[/bold red] {e}")
        logger.exception("Error al generar subtítulos")
        raise typer.Exit(code=1)


@app.command()
def burn_subtitles(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto."),
    style: str = typer.Option("hormozi", "--style", "-s", help="Estilo de subtítulos (hormozi, minimal, bold_pop, cinema)."),
):
    """Genera una vista previa del video con subtítulos cinéticos quemados."""
    try:
        with console.status("[bold cyan]Quemando subtítulos en video de previsualización...[/bold cyan]"):
            preview_video = burn_project_subtitles(project_dir, style=style)

        console.print(Panel.fit(
            f"[bold green]✓ Previsualización Subtitulada Generada[/bold green]\n"
            f"[cyan]Estilo:[/cyan] {style}\n"
            f"[cyan]Video con subtítulos quemados:[/cyan] {preview_video}",
            title="Burned Preview Ready"
        ))
    except Exception as e:
        console.print(f"[bold red]✗ Error quemando subtítulos:[/bold red] {e}")
        logger.exception("Error al quemar subtítulos")
        raise typer.Exit(code=1)


@app.command()
def build_timeline(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto."),
    fps: float = typer.Option(30.0, "--fps", help="Fotogramas por segundo del timeline."),
    width: int = typer.Option(1080, "--width", help="Ancho en píxeles del timeline."),
    height: int = typer.Option(1920, "--height", help="Alto en píxeles del timeline."),
):
    """Construye el VirtualTimeline y exporta los archivos EDL, FCPXML y OTIO."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Construyendo timeline virtual e intercambios NLE...", total=100)

            def _progress_cb(stage: str, p: float):
                desc_map = {
                    "building_virtual_timeline": "Construyendo VirtualTimeline multipista...",
                    "exporting_edl": "Exportando CMX 3600 EDL...",
                    "exporting_fcpxml": "Exportando FCPXML (Final Cut Pro / DaVinci Resolve)...",
                    "exporting_otio": "Exportando OpenTimelineIO (.otio)...",
                    "completed": "Timeline y exportaciones generadas.",
                }
                progress.update(task, description=desc_map.get(stage, stage), completed=int(p * 100))

            res = build_and_export_timeline_for_project(
                project_dir=project_dir,
                fps=fps,
                width=width,
                height=height,
                progress_callback=_progress_cb,
            )

        console.print(Panel.fit(
            f"[bold green]✓ Timeline Virtual e Integraciones NLE Generadas[/bold green]\n"
            f"[cyan]Virtual Timeline JSON:[/cyan] {res['virtual_timeline']}\n"
            f"[cyan]CMX 3600 EDL:[/cyan] {res['edl']}\n"
            f"[cyan]FCPXML (Final Cut / DaVinci):[/cyan] {res['fcpxml']}\n"
            f"[cyan]OpenTimelineIO (.otio):[/cyan] {res['otio']}",
            title="Timeline Export Summary"
        ))
    except Exception as e:
        console.print(f"[bold red]✗ Error construyendo timeline:[/bold red] {e}")
        logger.exception("Error al construir timeline")
        raise typer.Exit(code=1)


@app.command()
def render(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto a renderizar."),
    preset: str = typer.Option("social", "--preset", "-p", help="Preset de renderizado (social, master, preview)."),
    no_subs: bool = typer.Option(False, "--no-subs", help="No quemar subtítulos en el video final."),
):
    """Ejecuta el renderizado final del video conformando los cortes a RAW."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Renderizando video final con conformación a RAW...", total=100)

            def _progress_cb(stage: str, p: float):
                desc_map = {
                    "rendering_final_video": "Codificando video final acelerado por hardware...",
                    "completed": "Render final completado.",
                }
                progress.update(task, description=desc_map.get(stage, stage), completed=int(p * 100))

            metadata = render_final_video_for_project(
                project_dir=project_dir,
                preset=preset,
                burn_subtitles=not no_subs,
                progress_callback=_progress_cb,
            )

        console.print(Panel.fit(
            f"[bold green]✓ Render Final Completado Exitosamente[/bold green]\n"
            f"[cyan]Archivo Final:[/cyan] {metadata['output_file']}\n"
            f"[cyan]Resolución:[/cyan] {metadata['width']}x{metadata['height']} @ {metadata['fps']}fps\n"
            f"[cyan]Duración:[/cyan] {metadata['duration_seconds']:.2f} s\n"
            f"[cyan]Tamaño de Archivo:[/cyan] {metadata['file_size_mb']} MB\n"
            f"[cyan]Códec Video:[/cyan] {metadata['video_codec']}\n"
            f"[cyan]Subtítulos Quemados:[/cyan] {'Sí' if metadata['burned_subtitles'] else 'No'}\n"
            f"[cyan]SHA-256:[/cyan] {metadata['sha256'][:16]}...",
            title="Final Render Success"
        ))
    except Exception as e:
        console.print(f"[bold red]✗ Error en el render final:[/bold red] {e}")
        logger.exception("Error al renderizar video final")
        raise typer.Exit(code=1)


@app.command()
def golden_test(
    output_dir: Path = typer.Option(Path("./qa_golden_reports"), "--output-dir", "-o", help="Directorio donde se generarán los reportes."),
):
    """Ejecuta la suite oficial de Golden Tests con 3 videos sintéticos representativos y valida no-regresión."""
    console.print(Panel.fit(
        "[bold cyan]Iniciando Suite Oficial de Golden Tests (Sprint 11)[/bold cyan]\n"
        "Evaluando 3 arquetipos de video de referencia:\n"
        "1. Monólogo Dinámico (Hook, Zoom 1.15x, Subtítulos ASS)\n"
        "2. Discurso Dubitativo (Silencios, Fillers, EBU R128 -14 LUFS)\n"
        "3. Multi-Cámara (Cortes rápidos OpenCV, Smart Reframing, NLE universal)\n",
        title="IA Video Editor Pro — Golden Test Runner"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Ejecutando Golden Tests y validando aserciones...", total=None)
        report = run_all_golden_tests(output_dir)
        progress.update(task, completed=True)

    table = Table(title=f"Reporte de Golden Tests — {report.passed_scenarios}/{report.total_scenarios} Escenarios Superados")
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Escenario", style="white")
    table.add_column("Tiempo", style="yellow", width=10)
    table.add_column("Aserciones", style="magenta", width=12)
    table.add_column("Resultado", style="bold", width=14)

    for s in report.scenarios:
        res_str = "[green]✓ SUPERADO[/green]" if s.all_passed else "[red]✗ FALLIDO[/red]"
        as_str = f"{sum(1 for a in s.assertions if a.passed)}/{len(s.assertions)}"
        table.add_row(s.scenario_id, s.name, f"{s.execution_time_seconds:.2f}s", as_str, res_str)

    console.print(table)
    console.print(f"[bold green]✓[/bold green] Reporte Markdown generado en: [cyan]{report.report_markdown_path}[/cyan]")


@app.command()
def package(
    output_dir: Path = typer.Option(Path("./release"), "--output-dir", "-o", help="Directorio de destino para los paquetes compilados."),
    skip_dmg: bool = typer.Option(False, "--skip-dmg", help="Omitir la creación del instalador .dmg y generar solo el .app."),
):
    """Empaqueta la aplicación standalone para macOS (.app y .dmg) lista para distribución."""
    try:
        console.print(Panel.fit(
            f"[bold cyan]Iniciando Empaquetado de Producción para macOS (Sprint 12)[/bold cyan]\n"
            f"Destino: [bold]{output_dir}[/bold]\n"
            f"Arquitectura: [green]macOS Apple Silicon (ARM64) / Universal[/green]\n"
            f"Hardware Acelerado: [green]Apple VideoToolbox[/green]",
            title="IA Video Editor Pro — Packager"
        ))

        with console.status("[bold cyan]Construyendo IA Video Editor Pro.app...[/bold cyan]"):
            app_bundle = MacOSPackager.build_app_bundle(output_dir=output_dir)

        console.print(f"[bold green]✓[/bold green] Bundle macOS generado: [cyan]{app_bundle}[/cyan]")

        if not skip_dmg:
            with console.status("[bold cyan]Creando imagen de disco instalable (.dmg)...[/bold cyan]"):
                dmg_path = output_dir / "IA Video Editor Pro.dmg"
                dmg_meta = MacOSPackager.create_dmg(app_bundle_path=app_bundle, output_dmg_path=dmg_path)

            console.print(Panel.fit(
                f"[bold green]✓ Instalador macOS .dmg Generado Exitosamente[/bold green]\n\n"
                f"[cyan]Archivo:[/cyan] {dmg_meta['dmg_path']}\n"
                f"[cyan]Tamaño:[/cyan] [bold]{dmg_meta['file_size_mb']} MB[/bold]\n"
                f"[cyan]Volumen:[/cyan] {dmg_meta['volume_name']}\n"
                f"[cyan]SHA-256:[/cyan] [font_mono]{dmg_meta['sha256'][:16]}...[/font_mono]",
                title="Release Package Ready"
            ))
    except Exception as e:
        console.print(f"[bold red]✗ Error durante el empaquetado:[/bold red] {e}")
        logger.exception("Error al empaquetar aplicación")
        raise typer.Exit(code=1)


@app.command()
def ui(
    port: int = typer.Option(8000, "--port", "-p", help="Puerto HTTP para el servidor de la aplicación de escritorio."),
    no_browser: bool = typer.Option(False, "--no-browser", help="No abrir automáticamente el navegador predeterminado."),
):
    """Inicia el servidor local y abre la Interfaz de Usuario de Escritorio (Desktop UI)."""
    dist_path = Path(__file__).parent.parent.parent / "ui" / "dist"
    url = f"http://localhost:{port}"
    console.print(Panel.fit(
        f"[bold green]✓ Servidor Desktop UI de IA Video Editor Pro Iniciado[/bold green]\n\n"
        f"[cyan]URL Local:[/cyan] [bold underline]{url}[/bold underline]\n"
        f"[cyan]Directorio UI:[/cyan] {dist_path}\n"
        f"[cyan]Hardware Acelerado:[/cyan] Apple VideoToolbox / NVENC\n\n"
        f"[dim]Presiona Ctrl+C para detener el servidor.[/dim]",
        title="IA Video Editor Pro — Desktop Studio"
    ))

    if not no_browser:
        webbrowser.open(url)

    run_bridge_server(port=port, dist_dir=dist_path, blocking=True)


@app.command()
def analyze(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto a analizar completamente."),
):
    """Ejecuta el pipeline unificado de análisis (MediaProbe + Whisper + Scenes + Silence)."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Iniciando análisis integral...", total=100)

            def _progress_cb(stage: str, p: float):
                desc_map = {
                    "media_probe": "Inspeccionando propiedades técnicas...",
                    "transcription": "Transcribiendo audio fonético...",
                    "scene_detection": "Detectando cambios de plano (OpenCV)...",
                    "silence_detection": "Analizando silencios y pausas (DSP)...",
                    "completed": "Análisis completado.",
                }
                progress.update(task, description=desc_map.get(stage, stage), completed=int(p * 100))

            result = run_full_analysis(project_dir, progress_callback=_progress_cb)

        console.print(Panel.fit(
            f"[bold green]✓ Análisis unificado completado con éxito[/bold green]\n"
            f"[cyan]Duración Media:[/cyan] {result.media_info.duration_seconds:.2f} s\n"
            f"[cyan]Palabras Transcritas:[/cyan] {result.transcript.word_count if result.transcript else 0}\n"
            f"[cyan]Planos Detectados:[/cyan] {len(result.scenes)}\n"
            f"[cyan]Pausas / Silencios:[/cyan] {len(result.silence_intervals)}\n"
            f"[cyan]Resumen guardado en:[/cyan] {project_dir}/analysis/analysis_summary.json",
            title="Analysis Summary"
        ))
    except Exception as e:
        console.print(f"[bold red]✗ Error en el análisis unificado:[/bold red] {e}")
        logger.exception("Error al analizar proyecto")
        raise typer.Exit(code=1)


@app.command()
def plan_edit(
    project_dir: Path = typer.Argument(..., help="Directorio del proyecto a planificar."),
    profile: str | None = typer.Option(None, "--profile", "-p", help="Perfil editorial (social, youtube, corporate, podcast)."),
    offline: bool = typer.Option(False, "--offline", help="Forzar el motor heurístico local determinista sin invocar a Gemini."),
):
    """Genera el plan de edición inteligente (EditorialPlan) y crea analysis/edit_plan.json."""
    try:
        with console.status("[bold cyan]Generando plan editorial y decisiones de corte...[/bold cyan]"):
            plan = create_editorial_plan_for_project(
                project_dir=project_dir,
                target_profile=profile,
                force_heuristic=offline,
            )

        hook_color = "green" if plan.hook_score >= 0.7 else "yellow"
        console.print(Panel.fit(
            f"[bold green]✓ Plan Editorial Generado Exitosamente[/bold green]\n\n"
            f"[bold white]Resumen:[/bold white] {plan.summary}\n"
            f"[cyan]Hook Score (Gancho inicial):[/cyan] [{hook_color}]{plan.hook_score:.2f}[/{hook_color}]\n"
            f"[cyan]Retention Score (Retención):[/cyan] [bold green]{plan.retention_score:.2f}[/bold green]\n"
            f"[cyan]Redundancy Score (Redundancia):[/cyan] [bold]{plan.redundancy_score:.2f}[/bold]\n"
            f"[cyan]Duración Estimada Final:[/cyan] [bold yellow]{plan.target_duration_seconds:.2f} s[/bold yellow]\n"
            f"[cyan]Keywords Sugeridas B-Roll:[/cyan] {', '.join(plan.suggested_broll_keywords)}",
            title="Editorial Intelligence Report"
        ))

        table = Table(title=f"Decisiones de Edición — {len(plan.decisions)} operaciones")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Acción", style="bold", width=12)
        table.add_column("Entrada (In)", style="green", width=10)
        table.add_column("Salida (Out)", style="green", width=10)
        table.add_column("Duración", style="yellow", width=10)
        table.add_column("Motivo / Razón", style="white")

        for idx, d in enumerate(plan.decisions[:20], 1):
            act_style = {
                "keep": "[green]KEEP[/green]",
                "cut": "[bold red]CUT[/bold red]",
                "zoom_in": "[bold magenta]ZOOM_IN[/bold magenta]",
                "zoom": "[bold magenta]ZOOM[/bold magenta]",
                "speed_up": "[bold cyan]SPEED_UP[/bold cyan]",
                "b_roll": "[bold blue]B_ROLL[/bold blue]",
                "emphasize": "[bold yellow]EMPHASIZE[/bold yellow]",
            }.get(d.action.value, d.action.value)

            s_in = d.source_in if d.source_in is not None else 0.0
            s_out = d.source_out if d.source_out is not None else 0.0
            table.add_row(str(idx), act_style, f"{s_in:.2f}s", f"{s_out:.2f}s", f"{d.target_duration:.2f}s", d.reason)

        if len(plan.decisions) > 20:
            table.add_row("...", "...", "...", "...", "...", f"y {len(plan.decisions) - 20} decisiones más...")

        console.print(table)
        console.print(f"[bold green]✓[/bold green] Plan guardado en: [cyan]{project_dir}/analysis/edit_plan.json[/cyan]")
    except Exception as e:
        console.print(f"[bold red]✗ Error al planificar edición:[/bold red] {e}")
        logger.exception("Error al planificar edición")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
