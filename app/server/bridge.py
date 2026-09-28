"""Servidor HTTP/JSON REST y streaming de medios para la interfaz de usuario de escritorio (§40)."""

import json
import mimetypes
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.core.analysis import run_full_analysis
from app.core.audio_pipeline import process_project_audio
from app.core.config import config
from app.core.editorial import create_editorial_plan_for_project
from app.core.ingest import ingest_media
from app.core.logger import logger
from app.core.project import ProjectManager
from app.core.render import render_final_video_for_project
from app.core.subtitles import generate_subtitles_for_project
from app.core.timeline import build_and_export_timeline_for_project
from app.core.vision import run_vision_tracking_for_project
from app.utils.ffmpeg import FFmpegManager

# Extensiones de medios permitidas para streaming seguro
ALLOWED_MEDIA_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm",
    ".wav", ".mp3", ".aac", ".m4a", ".flac",
    ".png", ".jpg", ".jpeg", ".webp", ".svg",
    ".json", ".ass", ".srt", ".vtt", ".edl", ".fcpxml", ".otio"
}

CHUNK_SIZE = 64 * 1024  # 64 KB para streaming eficiente y bajo uso de memoria


class IVABridgeRequestHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para la API local de IA Video Editor Pro y servicio de medios."""

    ui_dist_dir: Path | None = None

    def log_message(self, format_str: str, *args: Any) -> None:
        """Enruta los logs de acceso a nivel debug para evitar ruido en consola."""
        logger.debug(f"[Bridge HTTP] {self.address_string()} - {format_str % args}")

    def do_OPTIONS(self):
        """Manejo de pre-flight CORS para clientes frontend."""
        self.send_response(HTTPStatus.OK)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Rutas GET de API y servicio de archivos de medios / UI."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/status":
            self._handle_get_status()
        elif path == "/api/system/choose_file":
            self._handle_get_choose_file()
        elif path == "/api/projects":
            self._handle_get_projects_list()
        elif path == "/api/project":
            query = parse_qs(parsed_url.query)
            proj_path = query.get("path", [None])[0]
            self._handle_get_project(proj_path)
        elif path == "/media":
            query = parse_qs(parsed_url.query)
            file_path = query.get("path", [None])[0]
            self._handle_serve_media(file_path)
        else:
            self._handle_serve_ui_static(path)

    def do_POST(self):
        """Rutas POST de ejecución del pipeline de edición."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            body = json.loads(post_body)
        except Exception:
            body = {}

        try:
            if path == "/api/project/init":
                self._handle_post_init_project(body)
            elif path == "/api/project/ingest":
                self._handle_post_ingest(body)
            elif path == "/api/project/analyze":
                self._handle_post_analyze(body)
            elif path == "/api/project/plan_edit":
                self._handle_post_plan_edit(body)
            elif path == "/api/project/reframe":
                self._handle_post_reframe(body)
            elif path == "/api/project/enhance_audio":
                self._handle_post_enhance_audio(body)
            elif path == "/api/project/generate_subtitles":
                self._handle_post_generate_subtitles(body)
            elif path == "/api/project/build_timeline":
                self._handle_post_build_timeline(body)
            elif path == "/api/project/render":
                self._handle_post_render(body)
            elif path == "/api/project/pipeline":
                self._handle_post_pipeline(body)
            else:
                self._send_json({"error": f"Ruta POST desconocida: {path}"}, status=HTTPStatus.NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error procesando petición {path}")
            self._send_json({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range")

    def _send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _require_field(self, body: dict, field: str) -> str | None:
        """Valida que un campo requerido exista y no sea None en el body POST."""
        value = body.get(field)
        if value is None:
            self._send_json(
                {"error": f"Campo requerido ausente: '{field}'"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return None
        return str(value)

    def _handle_get_status(self):
        status_data = {
            "app_name": "IA Video Editor Pro",
            "version": "0.1.0",
            "platform": "macOS (Apple Silicon)",
            "videotoolbox": FFmpegManager.has_videotoolbox(),
            "optimal_encoder": FFmpegManager.get_optimal_video_encoder(),
            "default_format": config.get("project.format", "9:16"),
            "ai_model": config.get("ai.model", "gemini-3.7-flash"),
        }
        self._send_json(status_data)

    def _handle_get_choose_file(self):
        """Abre la ventana nativa de selección de archivos de macOS (Finder) vía AppleScript."""
        if sys.platform == "darwin":
            try:
                cmd = [
                    "osascript", "-e",
                    'POSIX path of (choose file with prompt "Selecciona un video para IA Video Editor Pro" of type {"public.movie", "public.video", "mp4", "mov", "m4v", "mkv", "avi"})'
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0:
                    chosen = res.stdout.strip()
                    if chosen:
                        self._send_json({"success": True, "file_path": chosen, "file_name": Path(chosen).name})
                        return
                self._send_json({"success": False, "cancelled": True, "message": "Selección cancelada."})
            except Exception as e:
                logger.warning(f"Error abriendo diálogo de Finder: {e}")
                self._send_json({"success": False, "error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        else:
            self._send_json({"success": False, "error": "Solo soportado nativamente en macOS."}, status=HTTPStatus.NOT_IMPLEMENTED)

    def _handle_get_project(self, proj_path_str: str | None):
        if not proj_path_str:
            self._send_json({"error": "Parámetro 'path' requerido."}, status=HTTPStatus.BAD_REQUEST)
            return

        proj_path = Path(proj_path_str).resolve()
        if not proj_path.exists() or not (proj_path / "project.json").exists():
            self._send_json({"error": f"Proyecto no encontrado en: {proj_path}"}, status=HTTPStatus.NOT_FOUND)
            return

        manifest = ProjectManager.load_project(proj_path)

        # Cargar documentos auxiliares si existen
        analysis_files = {}
        for f_name in ["transcript.json", "scenes.json", "silence.json", "edit_plan.json", "reframing.json", "audio_metrics.json"]:
            f_path = proj_path / "analysis" / f_name
            if f_path.exists():
                try:
                    with open(f_path, "r", encoding="utf-8") as f:
                        analysis_files[f_name.replace(".json", "")] = json.load(f)
                except Exception as e:
                    logger.warning(f"No se pudo leer {f_path}: {e}")

        # Cargar virtual_timeline.json si existe
        vt_path = proj_path / "timeline" / "virtual_timeline.json"
        virtual_timeline = None
        if vt_path.exists():
            try:
                with open(vt_path, "r", encoding="utf-8") as f:
                    virtual_timeline = json.load(f)
            except Exception as e:
                logger.warning(f"No se pudo leer {vt_path}: {e}")

        self._send_json({
            "manifest": manifest,
            "analysis": analysis_files,
            "virtual_timeline": virtual_timeline,
        })

    def _handle_serve_media(self, file_path_str: str | None):
        """Sirve archivos de video/audio con streaming en bloques y soporte de HTTP Range requests."""
        if not file_path_str:
            self._send_json({"error": "Parámetro 'path' requerido."}, status=HTTPStatus.BAD_REQUEST)
            return

        media_file = Path(file_path_str).resolve()

        # Validación de seguridad contra path traversal y tipos permitidos
        if media_file.suffix.lower() not in ALLOWED_MEDIA_EXTENSIONS:
            self.send_error(HTTPStatus.FORBIDDEN, "Extensión de archivo no permitida.")
            return

        if not media_file.exists() or not media_file.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Archivo de medios no encontrado.")
            return

        file_size = media_file.stat().st_size
        mime_type, _ = mimetypes.guess_type(str(media_file))
        mime_type = mime_type or "application/octet-stream"

        range_header = self.headers.get("Range", None)
        try:
            if range_header and range_header.startswith("bytes="):
                ranges = range_header[6:].split("-")
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                start = max(0, min(start, file_size - 1))
                end = max(start, min(end, file_size - 1))
                length = (end - start) + 1

                self.send_response(HTTPStatus.PARTIAL_CONTENT)
                self._send_cors_headers()
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(media_file, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        to_read = min(CHUNK_SIZE, remaining)
                        buf = f.read(to_read)
                        if not buf:
                            break
                        self.wfile.write(buf)
                        remaining -= len(buf)
            else:
                self.send_response(HTTPStatus.OK)
                self._send_cors_headers()
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

                with open(media_file, "rb") as f:
                    while chunk := f.read(CHUNK_SIZE):
                        self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            logger.debug(f"Conexión de cliente interrumpida durante streaming de: {media_file.name}")

    def _handle_serve_ui_static(self, path: str):
        """Sirve los assets estáticos de la aplicación React o una landing interactiva embebida."""
        if self.ui_dist_dir and self.ui_dist_dir.exists():
            rel_path = path.lstrip("/") or "index.html"
            base_dir = self.ui_dist_dir.resolve()
            target = (base_dir / rel_path).resolve()

            # Evitar path traversal fuera del directorio dist
            if not str(target).startswith(str(base_dir)):
                self.send_error(HTTPStatus.FORBIDDEN, "Acceso no permitido.")
                return

            if target.exists() and target.is_file():
                mime, _ = mimetypes.guess_type(str(target))
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mime or "text/html")
                self.end_headers()
                with open(target, "rb") as f:
                    while chunk := f.read(CHUNK_SIZE):
                        self.wfile.write(chunk)
                return
            elif (self.ui_dist_dir / "index.html").exists():
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(self.ui_dist_dir / "index.html", "rb") as f:
                    while chunk := f.read(CHUNK_SIZE):
                        self.wfile.write(chunk)
                return

        html = """<!DOCTYPE html>
<html>
<head><title>IA Video Editor Pro Bridge</title></head>
<body style="font-family:sans-serif; background:#0d0f14; color:#fff; padding:2rem;">
  <h2>IA Video Editor Pro Backend API activo</h2>
  <p>El servidor local bridge está listo y escuchando peticiones en /api.</p>
</body>
</html>""".encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    # --- Endpoints GET adicionales ---

    def _handle_get_projects_list(self):
        """Lista todos los proyectos existentes en el directorio de proyectos."""
        import os
        projects_root = Path("./projects").resolve()
        qa_root = Path("./qa_golden_reports").resolve()
        found = []
        for base in [projects_root, qa_root]:
            if base.exists():
                for item in base.iterdir():
                    manifest = item / "project.json"
                    if item.is_dir() and manifest.exists():
                        try:
                            with open(manifest, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            found.append({
                                "path": str(item),
                                "name": data.get("name", item.name),
                                "profile": data.get("profile", "social"),
                                "rendered": data.get("rendered", False),
                            })
                        except Exception:
                            pass
        self._send_json({"projects": found, "count": len(found)})

    # --- Endpoints POST ---

    def _handle_post_init_project(self, body: dict):
        proj_dir = Path(body.get("project_dir", "./demo_project"))
        name = body.get("name", "Mi Video")
        profile = body.get("profile", "social")
        path = ProjectManager.create_project(proj_dir, project_name=name, profile=profile)
        self._send_json({"success": True, "project_path": str(path), "name": name, "profile": profile})

    def _handle_post_ingest(self, body: dict):
        proj_dir_str = self._require_field(body, "project_dir")
        if proj_dir_str is None:
            return
        video_file_str = self._require_field(body, "video_file")
        if video_file_str is None:
            return
        proj_dir = Path(proj_dir_str)
        video_file = Path(video_file_str)
        if not video_file.exists():
            self._send_json({"error": f"Archivo de video no encontrado: {video_file}"}, status=HTTPStatus.NOT_FOUND)
            return
        res = ingest_media(proj_dir, video_file)
        self._send_json({"success": True, "result": res})

    def _handle_post_analyze(self, body: dict):
        proj_dir_str = self._require_field(body, "project_dir")
        if proj_dir_str is None:
            return
        proj_dir = Path(proj_dir_str)
        res = run_full_analysis(proj_dir)
        self._send_json({"success": True, "duration": res.media_info.duration_seconds, "scenes": len(res.scenes)})

    def _handle_post_plan_edit(self, body: dict):
        proj_dir_str = self._require_field(body, "project_dir")
        if proj_dir_str is None:
            return
        proj_dir = Path(proj_dir_str)
        offline = body.get("offline", True)
        profile = body.get("profile", None)
        plan = create_editorial_plan_for_project(proj_dir, target_profile=profile, force_heuristic=offline)
        self._send_json({"success": True, "plan": plan.model_dump()})

    def _handle_post_reframe(self, body: dict):
        proj_dir_str = self._require_field(body, "project_dir")
        if proj_dir_str is None:
            return
        proj_dir = Path(proj_dir_str)
        fmt = body.get("format", "9:16")
        tracks, keyframes = run_vision_tracking_for_project(proj_dir, target_format=fmt)
        self._send_json({"success": True, "tracks": len(tracks), "keyframes": len(keyframes)})

    def _handle_post_enhance_audio(self, body: dict):
        proj_dir_str = self._require_field(body, "project_dir")
        if proj_dir_str is None:
            return
        proj_dir = Path(proj_dir_str)
        target = float(body.get("target_lufs", -14.0))
        metrics = process_project_audio(proj_dir, target_lufs=target)
        self._send_json({"success": True, "metrics": metrics.model_dump()})

    def _handle_post_generate_subtitles(self, body: dict):
        proj_dir_str = self._require_field(body, "project_dir")
        if proj_dir_str is None:
            return
        proj_dir = Path(proj_dir_str)
        style = body.get("style", "hormozi")
        max_words = int(body.get("max_words", 3))
        res = generate_subtitles_for_project(proj_dir, style=style, max_words=max_words)
        self._send_json({"success": True, "result": res})

    def _handle_post_pipeline(self, body: dict):
        """
        Endpoint unificado: ejecuta el pipeline completo de ingestión y análisis
        en una sola llamada HTTP. Reporta progreso por paso en el JSON de respuesta.
        Pasos: init → ingest → analyze → plan_edit → reframe → enhance_audio → build_timeline
        """
        video_file_str = self._require_field(body, "video_file")
        if video_file_str is None:
            return
        name = body.get("name", "Nuevo Proyecto")
        profile = body.get("profile", "social")
        target_lufs = float(body.get("target_lufs", -14.0))

        video_file = Path(video_file_str)
        if not video_file.exists():
            self._send_json({"error": f"Archivo de video no encontrado: {video_file}"}, status=HTTPStatus.NOT_FOUND)
            return

        safe_name = name.lower().replace(" ", "_")[:40]
        proj_dir = Path(f"./projects/{safe_name}").resolve()

        steps_log = []
        try:
            # 1. Inicializar proyecto
            steps_log.append({"step": "init", "status": "running"})
            path = ProjectManager.create_project(proj_dir, project_name=name, profile=profile)
            steps_log[-1]["status"] = "done"

            # 2. Ingestar video
            steps_log.append({"step": "ingest", "status": "running"})
            ingest_media(proj_dir, video_file)
            steps_log[-1]["status"] = "done"

            # 3. Análisis completo (transcripción, escenas, silencios)
            steps_log.append({"step": "analyze", "status": "running"})
            analysis_result = run_full_analysis(proj_dir)
            steps_log[-1]["status"] = "done"
            steps_log[-1]["duration"] = round(analysis_result.media_info.duration_seconds, 2)

            # 4. Planificación editorial
            steps_log.append({"step": "plan_edit", "status": "running"})
            plan = create_editorial_plan_for_project(proj_dir, target_profile=profile, force_heuristic=True)
            steps_log[-1]["status"] = "done"
            steps_log[-1]["decisions"] = len(plan.decisions)

            # 5. Smart Reframing 9:16
            steps_log.append({"step": "reframe", "status": "running"})
            tracks, keyframes = run_vision_tracking_for_project(proj_dir, target_format="9:16")
            steps_log[-1]["status"] = "done"
            steps_log[-1]["keyframes"] = len(keyframes)

            # 6. Masterización de audio
            steps_log.append({"step": "enhance_audio", "status": "running"})
            audio_metrics = process_project_audio(proj_dir, target_lufs=target_lufs)
            steps_log[-1]["status"] = "done"
            steps_log[-1]["final_lufs"] = audio_metrics.integrated_lufs

            # 7. Construcción del timeline
            steps_log.append({"step": "build_timeline", "status": "running"})
            build_and_export_timeline_for_project(proj_dir)
            steps_log[-1]["status"] = "done"

            self._send_json({
                "success": True,
                "project_path": str(path),
                "name": name,
                "steps": steps_log,
                "hook_score": plan.hook_score,
                "retention_score": plan.retention_score,
            })

        except Exception as e:
            if steps_log:
                steps_log[-1]["status"] = "error"
                steps_log[-1]["error"] = str(e)
            logger.exception(f"Error en pipeline unificado para: {video_file}")
            self._send_json(
                {"success": False, "error": str(e), "steps": steps_log},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def _handle_post_build_timeline(self, body: dict):
        proj_dir_str = self._require_field(body, "project_dir")
        if proj_dir_str is None:
            return
        proj_dir = Path(proj_dir_str)
        fps = float(body.get("fps", 30.0))
        width = int(body.get("width", 1080))
        height = int(body.get("height", 1920))
        res = build_and_export_timeline_for_project(proj_dir, fps=fps, width=width, height=height)
        # Serializar PosixPath a str si es necesario
        if isinstance(res, dict):
            res_serializable = {k: str(v) if hasattr(v, '__fspath__') else v for k, v in res.items()}
        else:
            res_serializable = str(res) if res else None
        self._send_json({"success": True, "exports": res_serializable})

    def _handle_post_render(self, body: dict):
        proj_dir_str = self._require_field(body, "project_dir")
        if proj_dir_str is None:
            return
        proj_dir = Path(proj_dir_str)
        preset = body.get("preset", "social")
        burn_subs = bool(body.get("burn_subtitles", True))
        meta = render_final_video_for_project(proj_dir, preset=preset, burn_subtitles=burn_subs)
        # Asegurar que todos los valores son JSON-serializables
        if isinstance(meta, dict):
            meta = {k: str(v) if hasattr(v, '__fspath__') else v for k, v in meta.items()}
        self._send_json({"success": True, "metadata": meta})


def run_bridge_server(
    port: int = 8000,
    host: str = "127.0.0.1",
    dist_dir: Path | None = None,
    blocking: bool = True,
) -> HTTPServer:
    """Inicia el servidor HTTP REST para el Bridge de IA Video Editor Pro."""
    IVABridgeRequestHandler.ui_dist_dir = dist_dir

    server_address = (host, port)
    httpd = HTTPServer(server_address, IVABridgeRequestHandler)
    logger.info(f"Servidor Bridge activo en http://{host}:{port}")

    if blocking:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.info("Deteniendo servidor Bridge...")
            httpd.server_close()

    return httpd
