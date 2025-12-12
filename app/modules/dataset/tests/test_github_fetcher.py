"""
Tests específicos para el GitHubFetcher.
Cubre parseo de URLs, clonación, manejo de branches y subpaths.
"""

import sys
import types
from pathlib import Path

import pytest

from app.modules.dataset.fetchers.base import FetchError
from app.modules.dataset.fetchers.github import GithubFetcher


def ensure_dummy_git():
    """Asegurar que git está disponible para tests."""
    if "git" in sys.modules:
        return

    gitmod = types.ModuleType("git")

    class DummyRepo:
        @staticmethod
        def clone_from(*args, **kwargs):
            return None

    class DummyGitCommandError(Exception):
        def __init__(self, command, message):
            self.command = command
            self.message = message
            super().__init__(f"{command}: {message}")

    gitmod.Repo = DummyRepo
    gitmod.GitCommandError = DummyGitCommandError
    sys.modules["git"] = gitmod


ensure_dummy_git()


# ==========================================
# TESTS DE DETECCIÓN DE URLS
# ==========================================


def test_github_fetcher_supports_github_urls():
    """Test que detecta correctamente URLs de GitHub."""
    fetcher = GithubFetcher()

    assert fetcher.supports("https://github.com/user/repo") is True
    assert fetcher.supports("https://github.com/user/repo.git") is True
    assert fetcher.supports("https://github.com/org/project") is True


def test_github_fetcher_supports_case_sensitive():
    """Test que supports es case-sensitive con el dominio."""
    fetcher = GithubFetcher()

    # La implementación es case-sensitive, mayúsculas no son soportadas
    assert fetcher.supports("https://GITHUB.COM/user/repo") is False
    assert fetcher.supports("https://GitHub.com/user/repo") is False


def test_github_fetcher_rejects_non_github_urls():
    """Test que rechaza URLs que no son de GitHub."""
    fetcher = GithubFetcher()

    assert fetcher.supports("https://gitlab.com/user/repo") is False
    assert fetcher.supports("https://bitbucket.org/user/repo") is False
    assert fetcher.supports("https://example.com") is False
    assert fetcher.supports("not-a-url") is False
    assert fetcher.supports("") is False


def test_github_fetcher_supports_handles_exceptions():
    """Test que supports maneja excepciones correctamente."""
    fetcher = GithubFetcher()

    # URL None o mal formada
    assert fetcher.supports(None) is False
    assert fetcher.supports(123) is False


# ==========================================
# TESTS DE PARSEO DE URLS
# ==========================================


def test_parse_simple_github_url():
    """Test parseo de URL simple de GitHub."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/username/repository")

    assert owner == "username"
    assert repo == "repository"
    assert branch is None
    assert subpath is None


def test_parse_github_url_with_git_extension():
    """Test parseo de URL con extensión .git."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/user/myproject.git")

    assert owner == "user"
    assert repo == "myproject"
    assert branch is None
    assert subpath is None


def test_parse_github_url_with_branch():
    """Test parseo de URL con branch específica."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/user/repo/tree/develop")

    assert owner == "user"
    assert repo == "repo"
    assert branch == "develop"
    assert subpath is None


def test_parse_github_url_with_main_branch():
    """Test parseo de URL con branch main."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/organization/project/tree/main")

    assert owner == "organization"
    assert repo == "project"
    assert branch == "main"
    assert subpath is None


def test_parse_github_url_with_master_branch():
    """Test parseo de URL con branch master."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/org/app/tree/master")

    assert owner == "org"
    assert repo == "app"
    assert branch == "master"
    assert subpath is None


def test_parse_github_url_with_subpath():
    """Test parseo de URL con subpath (carpeta específica)."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/user/repo/tree/main/folder/subfolder")

    assert owner == "user"
    assert repo == "repo"
    assert branch == "main"
    assert subpath == "folder/subfolder"


def test_parse_github_url_with_deep_subpath():
    """Test parseo de URL con subpath profundo."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url(
        "https://github.com/user/repo/tree/develop/src/models/uvl/examples"
    )

    assert owner == "user"
    assert repo == "repo"
    assert branch == "develop"
    assert subpath == "src/models/uvl/examples"


def test_parse_github_url_invalid_too_few_segments():
    """Test parseo de URL inválida (muy pocos segmentos)."""
    fetcher = GithubFetcher()

    result = fetcher._parse_github_url("https://github.com/onlyuser")

    # Debe retornar None para todos los valores
    assert result is None or result == (None, None, None, None)


def test_parse_github_url_empty():
    """Test parseo de URL vacía."""
    fetcher = GithubFetcher()

    result = fetcher._parse_github_url("")

    assert result is None or result == (None, None, None, None)


def test_parse_non_github_url():
    """Test parseo de URL que no es de GitHub."""
    fetcher = GithubFetcher()

    result = fetcher._parse_github_url("https://gitlab.com/user/repo")

    assert result is None or result == (None, None, None, None)


def test_parse_github_url_with_query_params():
    """Test parseo de URL con query params (debe ignorarlos)."""
    fetcher = GithubFetcher()

    owner, repo, branch, subpath = fetcher._parse_github_url("https://github.com/user/repo?tab=readme")

    assert owner == "user"
    assert repo == "repo"


# ==========================================
# TESTS DE FETCH - ERRORES
# ==========================================


def test_fetch_with_invalid_url(tmp_path):
    """Test fetch con URL inválida debe lanzar FetchError."""
    fetcher = GithubFetcher()

    with pytest.raises(FetchError, match="URL de github no encontrada"):
        fetcher.fetch("https://github.com/invalid", str(tmp_path))


def test_fetch_with_empty_url(tmp_path):
    """Test fetch con URL vacía debe lanzar FetchError."""
    fetcher = GithubFetcher()

    with pytest.raises(FetchError, match="URL de github no encontrada"):
        fetcher.fetch("", str(tmp_path))


def test_fetch_with_non_github_url(tmp_path):
    """Test fetch con URL no-GitHub debe lanzar FetchError."""
    fetcher = GithubFetcher()

    with pytest.raises(FetchError, match="URL de github no encontrada"):
        fetcher.fetch("https://gitlab.com/user/repo", str(tmp_path))


def test_fetch_clone_error(tmp_path, monkeypatch):
    """Test que maneja errores de clonación correctamente."""
    from git import GitCommandError

    def mock_clone_error(*args, **kwargs):
        raise GitCommandError("clone", "fatal: repository not found")

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone_error)

    with pytest.raises(FetchError, match="No se pudo clonar"):
        fetcher.fetch("https://github.com/user/nonexistent-repo", str(tmp_path))


def test_fetch_clone_authentication_error(tmp_path, monkeypatch):
    """Test manejo de error de autenticación al clonar."""
    from git import GitCommandError

    def mock_clone_auth_error(*args, **kwargs):
        raise GitCommandError("clone", "Authentication failed")

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone_auth_error)

    with pytest.raises(FetchError, match="No se pudo clonar"):
        fetcher.fetch("https://github.com/private/repo", str(tmp_path))


def test_fetch_subpath_not_exists(tmp_path, monkeypatch):
    """Test que detecta cuando el subpath no existe."""

    def mock_clone(*args, **kwargs):
        dest_dir = Path(args[1])
        dest_dir.mkdir(parents=True, exist_ok=True)
        # Crear algunos archivos pero no el subpath solicitado
        (dest_dir / "README.md").write_text("# Project")
        (dest_dir / "other_folder").mkdir()
        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    with pytest.raises(FetchError, match="subcarpeta solicitada no existe"):
        fetcher.fetch("https://github.com/user/repo/tree/main/nonexistent/path", str(tmp_path))


# ==========================================
# TESTS DE FETCH - CASOS EXITOSOS
# ==========================================


def test_fetch_successful_clone(tmp_path, monkeypatch):
    """Test clonación exitosa de repositorio."""
    cloned_data = {}

    def mock_clone(*args, **kwargs):
        clone_url = args[0]
        dest_dir = Path(args[1])

        cloned_data["url"] = clone_url
        cloned_data["dest"] = dest_dir
        cloned_data["kwargs"] = kwargs

        # Simular repositorio clonado
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "model.uvl").write_text("features:\n  Root")
        (dest_dir / "README.md").write_text("# Project")

        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result = fetcher.fetch("https://github.com/user/repo", str(tmp_path))

    assert result is not None
    assert cloned_data["url"] == "https://github.com/user/repo.git"
    assert "user__repo" in str(cloned_data["dest"])
    assert Path(result).exists()


def test_fetch_with_branch(tmp_path, monkeypatch):
    """Test clonación con branch específica."""
    cloned_data = {}

    def mock_clone(*args, **kwargs):
        clone_url = args[0]
        dest_dir = Path(args[1])
        branch = kwargs.get("branch")

        cloned_data["url"] = clone_url
        cloned_data["branch"] = branch

        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "model.uvl").write_text("features:\n  Root")

        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result = fetcher.fetch("https://github.com/user/repo/tree/develop", str(tmp_path))

    assert result is not None
    assert cloned_data["branch"] == "develop"


def test_fetch_with_subpath_exists(tmp_path, monkeypatch):
    """Test clonación con subpath que existe."""

    def mock_clone(*args, **kwargs):
        dest_dir = Path(args[1])
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Crear estructura con subpath
        subdir = dest_dir / "models" / "uvl"
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "model1.uvl").write_text("features:\n  Root1")
        (subdir / "model2.uvl").write_text("features:\n  Root2")

        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result = fetcher.fetch("https://github.com/user/repo/tree/main/models/uvl", str(tmp_path))

    assert result is not None
    result_path = Path(result)
    assert result_path.exists()

    # Verificar que retorna el subpath correcto
    assert "models" in str(result_path) or "uvl" in str(result_path)


def test_fetch_with_branch_and_subpath(tmp_path, monkeypatch):
    """Test clonación con branch y subpath."""
    cloned_data = {}

    def mock_clone(*args, **kwargs):
        dest_dir = Path(args[1])
        branch = kwargs.get("branch")

        cloned_data["branch"] = branch

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Crear subpath
        subdir = dest_dir / "src" / "features"
        subdir.mkdir(parents=True, exist_ok=True)
        (subdir / "feature.uvl").write_text("features:\n  Feature")

        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result = fetcher.fetch("https://github.com/user/repo/tree/develop/src/features", str(tmp_path))

    assert result is not None
    assert cloned_data["branch"] == "develop"

    result_path = Path(result)
    assert result_path.exists()


def test_fetch_creates_unique_directory_name(tmp_path, monkeypatch):
    """Test que crea nombres de directorio únicos basados en owner y repo."""

    def mock_clone(*args, **kwargs):
        dest_dir = Path(args[1])
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "file.uvl").write_text("content")
        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result1 = fetcher.fetch("https://github.com/user1/repo1", str(tmp_path))
    result2 = fetcher.fetch("https://github.com/user2/repo2", str(tmp_path))

    # Deben ser directorios diferentes
    assert result1 != result2
    assert "user1__repo1" in str(result1)
    assert "user2__repo2" in str(result2)


def test_fetch_with_git_extension_removes_it(tmp_path, monkeypatch):
    """Test que elimina la extensión .git de los nombres de repo."""
    cloned_data = {}

    def mock_clone(*args, **kwargs):
        dest_dir = Path(args[1])
        cloned_data["dest_name"] = dest_dir.name

        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "file.uvl").write_text("content")
        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result = fetcher.fetch("https://github.com/user/myrepo.git", str(tmp_path))

    # El nombre no debe contener .git
    assert result is not None
    assert ".git" not in cloned_data["dest_name"]
    assert "user__myrepo" in cloned_data["dest_name"]


# ==========================================
# TESTS DE CASOS EDGE
# ==========================================


def test_fetch_with_uppercase_github_url(tmp_path):
    """Test que URLs con mayúsculas en el dominio no son soportadas."""
    fetcher = GithubFetcher()

    # La implementación es case-sensitive, debe fallar
    with pytest.raises(FetchError, match="URL de github no encontrada"):
        fetcher.fetch("https://GITHUB.COM/user/repo", str(tmp_path))


def test_fetch_with_trailing_slash(tmp_path, monkeypatch):
    """Test que maneja URLs con slash final."""

    def mock_clone(*args, **kwargs):
        dest_dir = Path(args[1])
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "file.uvl").write_text("content")
        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    result = fetcher.fetch("https://github.com/user/repo/", str(tmp_path))

    assert result is not None


def test_fetch_with_special_characters_in_names(tmp_path, monkeypatch):
    """Test que maneja nombres con caracteres especiales."""

    def mock_clone(*args, **kwargs):
        dest_dir = Path(args[1])
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "file.uvl").write_text("content")
        return None

    fetcher = GithubFetcher()

    import git

    monkeypatch.setattr(git.Repo, "clone_from", mock_clone)

    # Nombres con guiones y underscores son comunes en GitHub
    result = fetcher.fetch("https://github.com/my-org/my_project-v2", str(tmp_path))

    assert result is not None
    assert "my-org__my_project-v2" in str(result)
