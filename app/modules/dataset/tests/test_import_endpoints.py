import io
import sys
import types
import zipfile
from pathlib import Path

import pytest
from flask import Flask

import app.modules.dataset.routes as routes_mod
from app.modules.dataset.fetchers.base import FetchError
from app.modules.dataset.fetchers.github import GithubFetcher
from app.modules.dataset.fetchers.zip import ZipFetcher
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


# ==========================================
# TESTS ORIGINALES DE IMPORT ENDPOINTS
# ==========================================


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


# ==========================================
# TESTS DE ZIP FETCHER
# ==========================================


def test_zip_fetcher_supports():
    """Test detección de archivos ZIP."""
    fetcher = ZipFetcher()

    assert fetcher.supports("file.zip") is True
    assert fetcher.supports("FILE.ZIP") is True
    assert fetcher.supports("archive.Zip") is True
    assert fetcher.supports("file.tar.gz") is False
    assert fetcher.supports("file.uvl") is False
    assert fetcher.supports("not-a-zip") is False


def test_zip_fetcher_valid_zip_with_uvl(tmp_path):
    """Test extraer ZIP válido con archivos UVL."""
    fetcher = ZipFetcher()

    # Crear ZIP con archivos UVL
    zip_path = tmp_path / "valid.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("model1.uvl", "features:\n  Root")
        zf.writestr("model2.uvl", "features:\n  Root2")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    result = fetcher.fetch(str(zip_path), str(dest_root))

    # Verificar que se extrajeron los archivos
    assert result is not None
    result_path = Path(result)
    assert result_path.exists()

    # Verificar que los archivos .uvl están presentes
    uvl_files = list(result_path.glob("**/*.uvl"))
    assert len(uvl_files) >= 1


def test_zip_fetcher_valid_zip_with_gpx(tmp_path):
    """Test extraer ZIP válido con archivos GPX."""
    fetcher = ZipFetcher()

    # Crear ZIP con archivos GPX
    zip_path = tmp_path / "tracks.zip"
    gpx_content = """<?xml version="1.0"?>
    <gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
        <trk><name>Track</name></trk>
    </gpx>"""

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("track1.gpx", gpx_content)
        zf.writestr("track2.gpx", gpx_content)

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    result = fetcher.fetch(str(zip_path), str(dest_root))

    assert result is not None
    result_path = Path(result)
    assert result_path.exists()

    gpx_files = list(result_path.glob("**/*.gpx"))
    assert len(gpx_files) >= 1


def test_zip_fetcher_too_many_entries(tmp_path):
    """Test ZIP con demasiadas entradas debe fallar."""
    fetcher = ZipFetcher()

    # Crear ZIP con más de MAX_ZIP_ENTRIES
    zip_path = tmp_path / "huge.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for i in range(501):  # Más del límite de 500
            zf.writestr(f"file{i}.uvl", "features: Root")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    with pytest.raises(FetchError, match="too many entries"):
        fetcher.fetch(str(zip_path), str(dest_root))


def test_zip_fetcher_path_traversal_attack(tmp_path):
    """Test protección contra path traversal en ZIP."""
    fetcher = ZipFetcher()

    # Crear ZIP con paths peligrosos
    zip_path = tmp_path / "malicious.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        # Intentar salir del directorio de extracción
        zf.writestr("../../../etc/passwd.uvl", "malicious content")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    with pytest.raises(FetchError, match="Unsafe path"):
        fetcher.fetch(str(zip_path), str(dest_root))


def test_zip_fetcher_invalid_zip_file(tmp_path):
    """Test archivo ZIP corrupto."""
    fetcher = ZipFetcher()

    # Crear archivo que no es ZIP
    fake_zip = tmp_path / "fake.zip"
    fake_zip.write_text("This is not a zip file")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    with pytest.raises(FetchError, match="Invalid ZIP file"):
        fetcher.fetch(str(fake_zip), str(dest_root))


def test_zip_fetcher_file_not_found(tmp_path):
    """Test ZIP inexistente."""
    fetcher = ZipFetcher()

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    with pytest.raises(FetchError, match="ZIP file not found"):
        fetcher.fetch(str(tmp_path / "nonexistent.zip"), str(dest_root))


def test_zip_fetcher_no_supported_files(tmp_path):
    """Test ZIP sin archivos soportados (.uvl/.gpx)."""
    fetcher = ZipFetcher()

    # Crear ZIP con archivos no soportados
    zip_path = tmp_path / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("readme.txt", "No UVL or GPX files here")
        zf.writestr("image.png", b"\x89PNG")
        zf.writestr("document.pdf", b"%PDF")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    with pytest.raises(FetchError, match="no supported files"):
        fetcher.fetch(str(zip_path), str(dest_root))


def test_zip_fetcher_mixed_content(tmp_path):
    """Test ZIP con archivos soportados y no soportados."""
    fetcher = ZipFetcher()

    # Crear ZIP mixto
    zip_path = tmp_path / "mixed.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("model.uvl", "features: Root")
        zf.writestr("readme.txt", "Documentation")
        zf.writestr("image.png", b"\x89PNG")

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    result = fetcher.fetch(str(zip_path), str(dest_root))

    # Debe extraer solo el .uvl
    result_path = Path(result)
    assert result_path.exists()

    uvl_files = list(result_path.glob("**/*.uvl"))
    assert len(uvl_files) >= 1

    # No debe extraer archivos no soportados
    txt_files = list(result_path.glob("**/*.txt"))
    png_files = list(result_path.glob("**/*.png"))
    assert len(txt_files) == 0
    assert len(png_files) == 0


def test_zip_fetcher_nested_directories(tmp_path):
    """Test ZIP con estructura de directorios anidados."""
    fetcher = ZipFetcher()

    zip_path = tmp_path / "nested.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("folder1/model1.uvl", "features: Root1")
        zf.writestr("folder1/subfolder/model2.uvl", "features: Root2")
        zf.writestr(
            "folder2/model3.gpx",
            """<?xml version="1.0"?>
        <gpx version="1.1"><trk><name>T</name></trk></gpx>""",
        )

    dest_root = tmp_path / "dest"
    dest_root.mkdir()

    result = fetcher.fetch(str(zip_path), str(dest_root))

    result_path = Path(result)
    assert result_path.exists()

    # Verificar que se extrajeron todos los archivos soportados
    uvl_files = list(result_path.glob("**/*.uvl"))
    gpx_files = list(result_path.glob("**/*.gpx"))

    assert len(uvl_files) >= 1
    assert len(gpx_files) >= 1


# ==========================================
# TESTS DE GITHUB FETCHER
# ==========================================


def test_github_fetcher_supports():
    """Test detección de URLs de GitHub."""
    fetcher = GithubFetcher()

    assert fetcher.supports("https://github.com/user/repo") is True
    assert fetcher.supports("https://github.com/user/repo.git") is True
    assert fetcher.supports("https://github.com/org/project") is True
    assert fetcher.supports("https://gitlab.com/user/repo") is False
    assert fetcher.supports("https://bitbucket.org/user/repo") is False
    assert fetcher.supports("not-a-url") is False
    assert fetcher.supports("https://example.com") is False


def test_github_parse_simple_url():
    """Test parseo de URL simple de GitHub."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/user/repository")

    assert owner == "user"
    assert repo == "repository"
    assert branch is None
    assert subpath is None


def test_github_parse_url_with_git_extension():
    """Test parseo de URL con .git."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/user/repository.git")

    assert owner == "user"
    assert repo == "repository"
    assert branch is None
    assert subpath is None


def test_github_parse_url_with_branch():
    """Test parseo de URL con branch específica."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/user/repo/tree/develop")

    assert owner == "user"
    assert repo == "repo"
    assert branch == "develop"
    assert subpath is None


def test_github_parse_url_with_subpath():
    """Test parseo de URL con subpath."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/user/repo/tree/main/folder/subfolder")

    assert owner == "user"
    assert repo == "repo"
    assert branch == "main"
    assert subpath == "folder/subfolder"


def test_github_parse_url_with_master_branch():
    """Test parseo de URL con branch master."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/organization/project/tree/master")

    assert owner == "organization"
    assert repo == "project"
    assert branch == "master"
    assert subpath is None


def test_github_parse_invalid_url():
    """Test parseo de URL inválida (solo un segmento)."""
    fetcher = GithubFetcher()

    result = fetcher._parse_github_url("https://github.com/onlyuser")

    # Debe retornar None o valores vacíos
    assert result is None or result == (None, None, None, None)


def test_github_parse_non_github_url():
    """Test parseo de URL que no es GitHub."""
    fetcher = GithubFetcher()

    result = fetcher._parse_github_url("https://gitlab.com/user/repo")

    assert result is None or result == (None, None, None, None)


def test_github_parse_empty_url():
    """Test parseo de URL vacía."""
    fetcher = GithubFetcher()

    result = fetcher._parse_github_url("")

    assert result is None or result == (None, None, None, None)


def test_github_fetcher_invalid_url(tmp_path):
    """Test fetch con URL inválida."""
    fetcher = GithubFetcher()

    with pytest.raises(FetchError, match="URL de github no encontrada"):
        fetcher.fetch("https://github.com/invalid", str(tmp_path))


def test_github_fetcher_clone_error(tmp_path, monkeypatch):
    """Test error al clonar repositorio."""
    from git import GitCommandError

    def mock_clone_error(*args, **kwargs):
        raise GitCommandError("clone", "Repository not found")

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone_error)

    with pytest.raises(FetchError, match="No se pudo clonar"):
        fetcher.fetch("https://github.com/user/nonexistent-repo", str(tmp_path))


def test_github_fetcher_successful_clone(tmp_path, monkeypatch):
    """Test clonación exitosa de repositorio."""
    cloned = {}

    def mock_clone(*args, **kwargs):
        # Simular clonación exitosa
        clone_url = args[0]
        dest_dir = Path(args[1])

        cloned["url"] = clone_url
        cloned["dest"] = dest_dir

        # Crear directorio simulado con archivos
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "model.uvl").write_text("features: Root")

        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result = fetcher.fetch("https://github.com/user/repo", str(tmp_path))

    assert result is not None
    assert cloned["url"] == "https://github.com/user/repo.git"
    assert "user__repo" in str(cloned["dest"])


def test_github_fetcher_clone_with_branch(tmp_path, monkeypatch):
    """Test clonación con branch específica."""
    cloned = {}

    def mock_clone(*args, **kwargs):
        clone_url = args[0]
        dest_dir = Path(args[1])
        branch = kwargs.get("branch")

        cloned["url"] = clone_url
        cloned["branch"] = branch

        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "model.uvl").write_text("features: Root")

        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result = fetcher.fetch("https://github.com/user/repo/tree/develop", str(tmp_path))

    assert result is not None
    assert cloned["branch"] == "develop"


def test_github_fetcher_subpath_not_exists(tmp_path, monkeypatch):
    """Test subpath inexistente en repositorio."""

    def mock_clone(*args, **kwargs):
        # Simular clonación pero sin crear el subpath
        dest_dir = Path(args[1])
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "other.uvl").write_text("features: Root")
        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    with pytest.raises(FetchError, match="subcarpeta solicitada no existe"):
        fetcher.fetch("https://github.com/user/repo/tree/main/nonexistent/path", str(tmp_path))


def test_github_fetcher_subpath_exists(tmp_path, monkeypatch):
    """Test clonación con subpath válido."""

    def mock_clone(*args, **kwargs):
        dest_dir = Path(args[1])
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Crear subpath
        subdir = dest_dir / "models" / "uvl"
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "model.uvl").write_text("features: Root")

        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result = fetcher.fetch("https://github.com/user/repo/tree/main/models/uvl", str(tmp_path))

    assert result is not None
    result_path = Path(result)
    assert result_path.exists()
    assert "models" in str(result_path) or "uvl" in str(result_path)
