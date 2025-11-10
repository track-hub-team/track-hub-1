import io
import sys
import types
from pathlib import Path

import pytest
from flask import Flask

import app.modules.dataset.routes as routes_mod
from app.modules.dataset.fetchers.base import FetchError
from app.modules.dataset.routes import dataset_bp


def ensure_dummy_git():
    if "git" in sys.modules:
        return
    gitmod = types.ModuleType("git")

    class DummyRepo:
        @staticmethod
        def clone_from(*args, **kwargs):
            return None

    gitmod.Repo = DummyRepo
    sys.modules["git"] = gitmod


@pytest.fixture
def app(tmp_path, monkeypatch):
    ensure_dummy_git()

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test",
        LOGIN_DISABLED=True,
    )
    app.register_blueprint(dataset_bp)

    class DummyUser:
        id = 1
        is_authenticated = True

        def temp_folder(self):
            p = tmp_path / "user_temp"
            p.mkdir(parents=True, exist_ok=True)
            return str(p)

    routes_mod.current_user = DummyUser()

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _multipart(field_name, filename, data_bytes: bytes):
    return {field_name: (io.BytesIO(data_bytes), filename)}


def test_routes_module_importable():
    assert hasattr(routes_mod, "import_dataset")


def test_import_github_calls_service(monkeypatch, client, tmp_path):
    called = {}

    def fake_fetch_models_from_github(github_url, dest_dir, current_user):
        dest_dir = Path(dest_dir)
        called["github_url"] = github_url
        called["dest_dir"] = dest_dir
        called["user_id"] = current_user.id
        return [dest_dir / "model1.uvl", dest_dir / "model2.gpx"]

    monkeypatch.setattr(
        routes_mod.dataset_service,
        "fetch_models_from_github",
        fake_fetch_models_from_github,
    )

    temp_dir = Path(routes_mod.current_user.temp_folder())
    assert temp_dir.exists()

    resp = client.post("/dataset/import", json={"github_url": "https://example.com/foo/repo"})
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["count"] == 2
    assert sorted(data["files"]) == [
        "model1.gpx".replace(".gpx", ".gpx").replace(".uvl", ".uvl"),
        "model1.uvl".replace(".uvl", ".uvl"),
    ] or sorted(data["files"]) == ["model1.uvl", "model2.gpx"]
    assert set(data["files"]) == {"model1.uvl", "model2.gpx"}

    assert called["github_url"] == "https://example.com/foo/repo"
    assert called["dest_dir"] == temp_dir
    assert called["user_id"] == routes_mod.current_user.id

    assert temp_dir.exists()


def test_import_github_missing_url(client):
    resp = client.post("/dataset/import", json={})
    assert resp.status_code == 400
    assert "Provide 'github_url' or a ZIP file" in resp.get_json().get("message", "")


def test_import_with_both_github_and_file_is_400(client):
    resp = client.post(
        "/dataset/import",
        data={**_multipart("file", "ds.zip", b"dummy"), "github_url": "https://example.com/repo"},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "not both" in resp.get_json().get("message", "")


def test_import_zip_calls_service(monkeypatch, client, tmp_path):
    called = {}

    def fake_fetch_models_from_zip_upload(file_storage, dest_dir, current_user):
        dest_dir = Path(dest_dir)
        called["filename"] = file_storage.filename
        called["dest_dir"] = dest_dir
        called["user_id"] = current_user.id
        return [dest_dir / "zipped.uvl"]

    monkeypatch.setattr(
        routes_mod.dataset_service,
        "fetch_models_from_zip_upload",
        fake_fetch_models_from_zip_upload,
    )

    temp_dir = Path(routes_mod.current_user.temp_folder())
    assert temp_dir.exists()

    resp = client.post(
        "/dataset/import",
        data=_multipart("file", "bundle.zip", b"zip-bytes"),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200

    data = resp.get_json()
    assert data["count"] == 1
    assert data["files"] == ["zipped.uvl"]

    assert called["filename"] == "bundle.zip"
    assert called["dest_dir"] == temp_dir
    assert called["user_id"] == routes_mod.current_user.id

    assert temp_dir.exists()


def test_import_zip_service_error(monkeypatch, client):
    def fake_fetch_models_from_zip_upload(file_storage, dest_dir, current_user):
        raise FetchError("ZIP broken")

    monkeypatch.setattr(
        routes_mod.dataset_service,
        "fetch_models_from_zip_upload",
        fake_fetch_models_from_zip_upload,
    )

    resp = client.post(
        "/dataset/import",
        data=_multipart("file", "bad.zip", b"xxx"),
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    assert "ZIP broken" in resp.get_json().get("message", "")
