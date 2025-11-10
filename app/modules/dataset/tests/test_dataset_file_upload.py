import io
from pathlib import Path

import pytest
from flask import Flask

import app.modules.dataset.routes as routes_mod
from app.modules.dataset.routes import dataset_bp


def _multipart(field_name, filename, data_bytes: bytes):
    return {field_name: (io.BytesIO(data_bytes), filename)}


@pytest.fixture
def app(tmp_path, monkeypatch):
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test",
        LOGIN_DISABLED=True,
    )
    app.register_blueprint(dataset_bp)

    class DummyUser:
        id = 42
        is_authenticated = True

        def temp_folder(self):
            p = tmp_path / "user_temp"
            p.mkdir(parents=True, exist_ok=True)
            return str(p)

    routes_mod.current_user = DummyUser()

    class DummyHandler:
        def validate(self, path: str):
            return True

    class DummyDescriptor:
        def __init__(self, kind: str):
            self.handler = DummyHandler()

    monkeypatch.setattr(routes_mod, "get_allowed_extensions", lambda: [".uvl", ".gpx"])
    monkeypatch.setattr(
        routes_mod,
        "infer_kind_from_filename",
        lambda fn: "uvl" if fn.lower().endswith(".uvl") else "gpx" if fn.lower().endswith(".gpx") else "unknown",
    )
    monkeypatch.setattr(routes_mod, "get_descriptor", lambda kind: DummyDescriptor(kind))

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_upload_uvl_ok(client):
    resp = client.post(
        "/dataset/file/upload",
        data=_multipart("file", "model.uvl", b"uvl-content"),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["file_type"] == "uvl"
    name = data["filename"]
    saved = Path(routes_mod.current_user.temp_folder()) / name
    assert saved.exists()
    assert saved.read_bytes() == b"uvl-content"


def test_upload_gpx_ok(client):
    resp = client.post(
        "/dataset/file/upload",
        data=_multipart("file", "track.gpx", b"<gpx/>"),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["file_type"] == "gpx"
    name = data["filename"]
    saved = Path(routes_mod.current_user.temp_folder()) / name
    assert saved.exists()
    assert saved.read_bytes() == b"<gpx/>"


def test_upload_invalid_extension(client):
    resp = client.post(
        "/dataset/file/upload",
        data=_multipart("file", "malware.exe", b"MZ"),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "Invalid file type" in resp.get_json()["message"]


def test_upload_duplicate_names_overwrites(client):
    r1 = client.post(
        "/dataset/file/upload",
        data=_multipart("file", "dup.gpx", b"A"),
        content_type="multipart/form-data",
    )
    assert r1.status_code == 200
    name1 = r1.get_json()["filename"]

    r2 = client.post(
        "/dataset/file/upload",
        data=_multipart("file", "dup.gpx", b"B"),
        content_type="multipart/form-data",
    )
    assert r2.status_code == 200
    name2 = r2.get_json()["filename"]

    assert name1 == name2
    saved = Path(routes_mod.current_user.temp_folder()) / name1
    assert saved.exists()
    assert saved.read_bytes() == b"B"
