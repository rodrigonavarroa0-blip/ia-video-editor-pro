"""Tests unitarios para el servidor HTTP bridge de la UI (app.server.bridge)."""

import json
import threading
from http.server import HTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

from app.server.bridge import IVABridgeRequestHandler


@pytest.fixture
def bridge_server_url(tmp_path: Path):
    """Levanta un servidor bridge en un puerto efímero para pruebas."""
    IVABridgeRequestHandler.ui_dist_dir = tmp_path / "dist"
    IVABridgeRequestHandler.ui_dist_dir.mkdir(parents=True, exist_ok=True)
    (IVABridgeRequestHandler.ui_dist_dir / "index.html").write_text("<html><body>IVA UI</body></html>")

    server = HTTPServer(("127.0.0.1", 0), IVABridgeRequestHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()
    server.server_close()


def test_bridge_get_status(bridge_server_url: str):
    """Valida el endpoint GET /api/status."""
    with urlopen(f"{bridge_server_url}/api/status") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["app_name"] == "IA Video Editor Pro"
        assert "optimal_encoder" in data


def test_bridge_serve_static_ui(bridge_server_url: str):
    """Valida el servicio de la aplicación web."""
    with urlopen(f"{bridge_server_url}/") as resp:
        assert resp.status == 200
        content = resp.read().decode("utf-8")
        assert "IVA UI" in content
