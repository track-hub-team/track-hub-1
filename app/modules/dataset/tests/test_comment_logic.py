import pytest
from flask import Flask

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import DSMetaData, UVLDataset
from app.modules.dataset.repositories import CommentRepository
from app.modules.dataset.routes import dataset_bp
from app.modules.dataset.services import CommentService
from app.modules.profile.models import UserProfile


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Configurar aplicación Flask para tests."""
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test",
        LOGIN_DISABLED=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    app.register_blueprint(dataset_bp)

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Cliente de pruebas Flask."""
    return app.test_client()


@pytest.fixture
def user(app):
    """Usuario de prueba."""
    with app.app_context():
        user = User(email="test@example.com")
        user.set_password("test1234")
        db.session.add(user)

        profile = UserProfile(user=user, name="Test User", surname="Surname")
        db.session.add(profile)

        db.session.commit()
        user_id = user.id

    return user_id


@pytest.fixture
def user2(app):
    """Segundo usuario para tests de permisos."""
    with app.app_context():
        user = User(email="other@example.com")
        user.set_password("test1234")
        db.session.add(user)

        profile = UserProfile(user=user, name="Other User", surname="Surname")
        db.session.add(profile)

        db.session.commit()
        user_id = user.id

    return user_id


@pytest.fixture
def dataset(app, user):
    """Dataset de prueba."""
    with app.app_context():
        ds_meta_data = DSMetaData(title="Test Dataset", description="Test description", publication_type="none")
        db.session.add(ds_meta_data)

        dataset = UVLDataset(user_id=user, ds_meta_data=ds_meta_data)
        db.session.add(dataset)

        db.session.commit()
        dataset_id = dataset.id

    return dataset_id


@pytest.fixture
def comment_repository():
    """Repositorio de comentarios."""
    return CommentRepository()


@pytest.fixture
def comment_service():
    """Servicio de comentarios."""
    return CommentService()


# ==========================================
# TESTS DEL REPOSITORIO
# ==========================================


def test_create_comment(app, dataset, user, comment_repository):
    """Test crear comentario básico."""
    with app.app_context():
        comment = comment_repository.create(dataset_id=dataset, user_id=user, content="Test comment")

        assert comment.id is not None
        assert comment.dataset_id == dataset
        assert comment.user_id == user
        assert comment.content == "Test comment"


def test_get_by_dataset(app, dataset, user, comment_repository):
    """Test obtener comentarios de un dataset."""
    with app.app_context():
        comment_repository.create(dataset_id=dataset, user_id=user, content="Comment 1")
        comment_repository.create(dataset_id=dataset, user_id=user, content="Comment 2")

        comments = comment_repository.get_by_dataset(dataset)

        assert len(comments) == 2


def test_delete_comment(app, dataset, user, comment_repository):
    """Test eliminar comentario."""
    with app.app_context():
        comment = comment_repository.create(dataset_id=dataset, user_id=user, content="To delete")
        comment_id = comment.id

        result = comment_repository.delete(comment_id)

        assert result is True
        assert comment_repository.get_by_id(comment_id) is None


def test_count_by_dataset(app, dataset, user, comment_repository):
    """Test contar comentarios de un dataset."""
    with app.app_context():
        comment_repository.create(dataset_id=dataset, user_id=user, content="Comment 1")
        comment_repository.create(dataset_id=dataset, user_id=user, content="Comment 2")

        count = comment_repository.count_by_dataset(dataset)

        assert count == 2


# ==========================================
# TESTS DEL SERVICIO - VALIDACIONES
# ==========================================


def test_create_comment_success(app, dataset, user, comment_service):
    """Test crear comentario con datos válidos."""
    with app.app_context():
        result = comment_service.create_comment(dataset_id=dataset, user_id=user, content="Valid comment")

        assert result is not None
        assert result["content"] == "Valid comment"
        assert result["user_id"] == user


def test_create_comment_empty_content(app, dataset, user, comment_service):
    """Test crear comentario con contenido vacío debe fallar."""
    with app.app_context():
        with pytest.raises(ValueError, match="cannot be empty"):
            comment_service.create_comment(dataset_id=dataset, user_id=user, content="")


def test_create_comment_whitespace_only(app, dataset, user, comment_service):
    """Test crear comentario solo con espacios debe fallar."""
    with app.app_context():
        with pytest.raises(ValueError, match="cannot be empty"):
            comment_service.create_comment(dataset_id=dataset, user_id=user, content="   \n\t   ")


def test_create_comment_too_long(app, dataset, user, comment_service):
    """Test crear comentario demasiado largo debe fallar."""
    with app.app_context():
        long_content = "a" * 1001

        with pytest.raises(ValueError, match="too long"):
            comment_service.create_comment(dataset_id=dataset, user_id=user, content=long_content)


def test_create_comment_dataset_not_found(app, user, comment_service):
    """Test crear comentario en dataset inexistente debe fallar."""
    with app.app_context():
        with pytest.raises(ValueError, match="not found"):
            comment_service.create_comment(dataset_id=99999, user_id=user, content="Test comment")


def test_create_comment_xss_sanitization(app, dataset, user, comment_service):
    """Test sanitización de contenido HTML/XSS."""
    with app.app_context():
        malicious_content = '<script>alert("XSS")</script>Hello'

        result = comment_service.create_comment(dataset_id=dataset, user_id=user, content=malicious_content)

        assert "<script>" not in result["content"]
        assert "&lt;script&gt;" in result["content"]


# ==========================================
# TESTS DEL SERVICIO - PERMISOS
# ==========================================


def test_delete_comment_owner(app, dataset, user, comment_repository, comment_service):
    """Test eliminar comentario siendo el autor debe funcionar."""
    with app.app_context():
        comment = comment_repository.create(dataset_id=dataset, user_id=user, content="My comment")

        result = comment_service.delete_comment(comment.id, user)

        assert result is True


def test_delete_comment_not_owner(app, dataset, user, user2, comment_repository, comment_service):
    """Test eliminar comentario de otro usuario debe fallar."""
    with app.app_context():
        comment = comment_repository.create(dataset_id=dataset, user_id=user, content="User 1 comment")

        with pytest.raises(PermissionError, match="your own comments"):
            comment_service.delete_comment(comment.id, user2)


def test_update_comment_owner(app, dataset, user, comment_repository, comment_service):
    """Test actualizar comentario siendo el autor debe funcionar."""
    with app.app_context():
        comment = comment_repository.create(dataset_id=dataset, user_id=user, content="Original content")

        result = comment_service.update_comment(comment.id, user, "Updated content")

        assert result["content"] == "Updated content"


def test_update_comment_not_owner(app, dataset, user, user2, comment_repository, comment_service):
    """Test actualizar comentario de otro usuario debe fallar."""
    with app.app_context():
        comment = comment_repository.create(dataset_id=dataset, user_id=user, content="User 1 comment")

        with pytest.raises(PermissionError, match="your own comments"):
            comment_service.update_comment(comment.id, user2, "Hacked content")


# ==========================================
# TESTS DE ENDPOINTS
# ==========================================


def test_create_comment_endpoint_authenticated(client, app, dataset, user, monkeypatch):
    """Test crear comentario vía endpoint autenticado."""
    with app.app_context():
        import app.modules.dataset.routes as routes_mod

        class DummyUser:
            id = user
            is_authenticated = True

        monkeypatch.setattr(routes_mod, "current_user", DummyUser())

        resp = client.post(
            f"/dataset/{dataset}/comments",
            json={"content": "Test comment via API"},
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert data["comment"]["content"] == "Test comment via API"


def test_get_comments_endpoint_public(client, app, dataset, user, comment_repository):
    """Test listar comentarios es público (no requiere auth)."""
    with app.app_context():
        comment_repository.create(dataset_id=dataset, user_id=user, content="Comment 1")
        comment_repository.create(dataset_id=dataset, user_id=user, content="Comment 2")

        resp = client.get(f"/dataset/{dataset}/comments")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert len(data["comments"]) == 2


def test_delete_comment_endpoint_owner(client, app, dataset, user, comment_repository, monkeypatch):
    """Test eliminar comentario vía endpoint siendo el autor."""
    with app.app_context():
        comment = comment_repository.create(dataset_id=dataset, user_id=user, content="To delete")

        import app.modules.dataset.routes as routes_mod

        class DummyUser:
            id = user
            is_authenticated = True

        monkeypatch.setattr(routes_mod, "current_user", DummyUser())

        resp = client.delete(f"/dataset/comments/{comment.id}")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True


def test_delete_comment_endpoint_not_owner(client, app, dataset, user, user2, comment_repository, monkeypatch):
    """Test eliminar comentario ajeno vía endpoint debe fallar."""
    with app.app_context():
        comment = comment_repository.create(dataset_id=dataset, user_id=user, content="User 1 comment")

        import app.modules.dataset.routes as routes_mod

        class DummyUser:
            id = user2
            is_authenticated = True

        monkeypatch.setattr(routes_mod, "current_user", DummyUser())

        resp = client.delete(f"/dataset/comments/{comment.id}")

        assert resp.status_code == 403
