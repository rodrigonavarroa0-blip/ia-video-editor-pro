"""Suite de pruebas de control de calidad hostil (QA Hostile Tests) para Sprint 10 (§107)."""

import threading
import urllib.error
from http.server import HTTPServer
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest
from typer.testing import CliRunner

from app.cli.main import app
from app.server.bridge import IVABridgeRequestHandler

runner = CliRunner()


@pytest.fixture
def qa_bridge_server(tmp_path: Path):
    IVABridgeRequestHandler.ui_dist_dir = tmp_path
    server = HTTPServer(("127.0.0.1", 0), IVABridgeRequestHandler)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{port}"

    server.shutdown()
    server.server_close()


def test_qa_media_streaming_range_request(synthetic_video: Path, qa_bridge_server: str):
    """Prueba que el streaming de video soporte cabeceras Range (HTTP 206 Partial Content)."""
    encoded_path = quote(str(synthetic_video))
    url = f"{qa_bridge_server}/media?path={encoded_path}"

    req = Request(url, headers={"Range": "bytes=0-100"})
    with urlopen(req) as resp:
        assert resp.status == 206
        assert resp.headers.get("Content-Range").startswith("bytes 0-100/")
        assert len(resp.read()) == 101


def test_qa_non_existent_project_404(qa_bridge_server: str):
    """Prueba que solicitar un proyecto inexistente devuelva 404 de forma limpia."""
    url = f"{qa_bridge_server}/api/project?path=/non/existent/path"
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urlopen(url)
    assert exc_info.value.code == 404


def test_qa_cli_ui_help():
    """Prueba el comando CLI iva ui."""
    res = runner.invoke(app, ["ui", "--help"])
    assert res.exit_code == 0
    assert "Inicia el servidor local y abre la Interfaz de Usuario de Escritorio" in res.stdout
