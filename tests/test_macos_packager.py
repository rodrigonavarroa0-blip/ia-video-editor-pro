"""Tests unitarios para el motor de empaquetado macOS (.app y .dmg)."""

import stat
from pathlib import Path

from app.packaging.macos_packager import MacOSPackager


def test_build_app_bundle_structure(tmp_path: Path):
    """Valida la generación de la estructura de bundle macOS (.app)."""
    out_dir = tmp_path / "release_test"
    app_bundle = MacOSPackager.build_app_bundle(out_dir, app_name="TestApp", version="1.0.0")

    assert app_bundle.exists()
    assert (app_bundle / "Contents" / "Info.plist").exists()
    assert (app_bundle / "Contents" / "MacOS" / "iva_launcher").exists()
    assert (app_bundle / "Contents" / "Resources" / "ui").exists()

    # Validar permisos de ejecución en iva_launcher
    launcher = app_bundle / "Contents" / "MacOS" / "iva_launcher"
    mode = launcher.stat().st_mode
    assert bool(mode & stat.S_IXUSR)

    # Validar Info.plist
    plist_text = (app_bundle / "Contents" / "Info.plist").read_text(encoding="utf-8")
    assert "com.iavideoeditor.pro" in plist_text
    assert "<string>TestApp</string>" in plist_text


def test_create_dmg_archive(tmp_path: Path):
    """Valida la creación de la imagen de disco .dmg con hash SHA-256."""
    out_dir = tmp_path / "dmg_test"
    app_bundle = MacOSPackager.build_app_bundle(out_dir, app_name="DMGApp")

    dmg_path = out_dir / "DMGApp.dmg"
    meta = MacOSPackager.create_dmg(app_bundle, dmg_path, volume_name="DMG Test")

    assert Path(meta["dmg_path"]).exists()
    assert meta["file_size_bytes"] > 0
    assert len(meta["sha256"]) == 64
