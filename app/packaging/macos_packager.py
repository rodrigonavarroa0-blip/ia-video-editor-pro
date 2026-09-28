"""Motor de empaquetado de producción para macOS (.app y .dmg) (§44 y §102)."""

import hashlib
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from app.core.logger import logger
from app.utils.ffmpeg import FFmpegManager


class MacOSPackager:
    """Construye el bundle nativo IA Video Editor Pro.app y el instalador .dmg para macOS."""

    INFO_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundleDisplayName</key>
    <string>{app_name}</string>
    <key>CFBundleIdentifier</key>
    <string>com.iavideoeditor.pro</string>
    <key>CFBundleVersion</key>
    <string>{version}</string>
    <key>CFBundleShortVersionString</key>
    <string>{version}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>iva_launcher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    <key>NSMicrophoneUsageDescription</key>
    <string>IA Video Editor Pro requiere acceso al micrófono para análisis acústico.</string>
    <key>NSCameraUsageDescription</key>
    <string>IA Video Editor Pro requiere acceso a la cámara para grabación y visión computacional.</string>
</dict>
</plist>
"""

    LAUNCHER_SCRIPT_TEMPLATE = """#!/bin/bash
# Launcher nativo de IA Video Editor Pro para macOS
DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" && pwd )"
APP_DIR="$( dirname "$DIR" )"
RESOURCES_DIR="$APP_DIR/Resources"

export PATH="$RESOURCES_DIR/bin:$PATH"
export IVA_UI_DIR="$RESOURCES_DIR/ui"

echo "Iniciando IA Video Editor Pro Desktop Studio..."
# Iniciar servidor bridge local y abrir interfaz
exec python3 -m app.cli.main ui --port 8000
"""

    @classmethod
    def build_app_bundle(
        cls,
        output_dir: Path,
        app_name: str = "IA Video Editor Pro",
        version: str = "0.1.0",
    ) -> Path:
        """
        Construye la estructura de directorios estándar de una aplicación macOS (.app).
        """
        out = Path(output_dir).resolve()
        out.mkdir(parents=True, exist_ok=True)

        app_bundle = out / f"{app_name}.app"
        contents = app_bundle / "Contents"
        macos_dir = contents / "MacOS"
        resources_dir = contents / "Resources"
        frameworks_dir = contents / "Frameworks"

        # Limpiar si ya existía
        if app_bundle.exists():
            shutil.rmtree(app_bundle)

        macos_dir.mkdir(parents=True, exist_ok=True)
        resources_dir.mkdir(parents=True, exist_ok=True)
        frameworks_dir.mkdir(parents=True, exist_ok=True)

        # 1. Escribir Info.plist
        plist_path = contents / "Info.plist"
        plist_content = cls.INFO_PLIST_TEMPLATE.format(app_name=app_name, version=version)
        plist_path.write_text(plist_content, encoding="utf-8")

        # 2. Escribir script de arranque ejecutable
        launcher_path = macos_dir / "iva_launcher"
        launcher_path.write_text(cls.LAUNCHER_SCRIPT_TEMPLATE, encoding="utf-8")
        launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # 3. Copiar interfaz de usuario compilada si existe
        src_ui_dist = Path(__file__).parent.parent.parent / "ui" / "dist"
        dst_ui_dir = resources_dir / "ui"
        if src_ui_dist.exists():
            shutil.copytree(src_ui_dist, dst_ui_dir, dirs_exist_ok=True)
        else:
            dst_ui_dir.mkdir(parents=True, exist_ok=True)
            (dst_ui_dir / "index.html").write_text("<html><body>IA Video Editor Pro</body></html>")

        # 4. Enlazar binarios de FFmpeg
        bin_dir = resources_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        try:
            ffmpeg_path = FFmpegManager.get_ffmpeg_path()
            if Path(ffmpeg_path).exists():
                dst_ffmpeg = bin_dir / "ffmpeg"
                if not dst_ffmpeg.exists():
                    try:
                        os.symlink(ffmpeg_path, dst_ffmpeg)
                    except Exception:
                        shutil.copy(ffmpeg_path, dst_ffmpeg)
        except Exception as e:
            logger.warning(f"No se pudo copiar binario FFmpeg al bundle: {e}")

        logger.info(f"Bundle macOS generado exitosamente en: {app_bundle}")
        return app_bundle

    @classmethod
    def create_dmg(
        cls,
        app_bundle_path: Path,
        output_dmg_path: Path,
        volume_name: str = "IA Video Editor Pro",
    ) -> dict:
        """
        Empaqueta el bundle .app en una imagen de disco .dmg con enlace a /Applications.
        """
        app_path = Path(app_bundle_path).resolve()
        out_dmg = Path(output_dmg_path).resolve()
        out_dmg.parent.mkdir(parents=True, exist_ok=True)

        if not app_path.exists():
            raise FileNotFoundError(f"Bundle .app no encontrado: {app_path}")

        # Directorio temporal de preparación (staging)
        staging_dir = out_dmg.parent / "_dmg_staging"
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True, exist_ok=True)

        # Copiar .app al staging
        dst_app = staging_dir / app_path.name
        shutil.copytree(app_path, dst_app)

        # Crear enlace simbólico hacia /Applications
        apps_symlink = staging_dir / "Applications"
        try:
            os.symlink("/Applications", apps_symlink)
        except Exception as e:
            logger.debug(f"No se pudo crear symlink /Applications: {e}")

        # Eliminar DMG previo si existía
        if out_dmg.exists():
            out_dmg.unlink()

        # Construir DMG usando hdiutil nativo en macOS
        if sys.platform == "darwin" and shutil.which("hdiutil"):
            cmd = [
                "hdiutil", "create",
                "-volname", volume_name,
                "-srcfolder", str(staging_dir),
                "-ov",
                "-format", "UDZO",
                str(out_dmg),
            ]
            logger.info(f"Ejecutando hdiutil para crear {out_dmg.name}...")
            subprocess.run(cmd, capture_output=True, check=True)
        else:
            # Fallback multiplataforma (archivo comprimido .zip)
            logger.info("hdiutil no disponible, creando archivo distribuible comprimido...")
            shutil.make_archive(str(out_dmg.with_suffix("")), "zip", staging_dir)
            out_dmg = out_dmg.with_suffix(".zip")

        # Limpiar staging
        shutil.rmtree(staging_dir, ignore_errors=True)

        # Calcular tamaño y hash SHA-256 en bloques de 64 KB
        file_size = out_dmg.stat().st_size
        hasher = hashlib.sha256()
        with open(out_dmg, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256_hash = hasher.hexdigest()

        metadata = {
            "dmg_path": str(out_dmg),
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "volume_name": volume_name,
            "sha256": sha256_hash,
        }

        logger.info(f"Instalador macOS generado con éxito: {out_dmg.name} ({metadata['file_size_mb']} MB)")
        return metadata
