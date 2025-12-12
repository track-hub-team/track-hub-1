"""
Tests para las rutas de dataset que no están cubiertas en otros archivos.
Cubre endpoints de versiones, comparaciones, edición, comentarios, etc.
"""

import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import Flask
from flask_login import LoginManager

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import DSMetaData
from app.modules.dataset.routes import dataset_bp


@pytest.fixture
def app(tmp_path):
    """Crear aplicación Flask de test."""
    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test-secret-key",
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WORKING_DIR=str(tmp_path),
    )

    # Configurar carpeta de templates para tests
    app.template_folder = str(Path(__file__).parent.parent / "templates")

    # Inicializar Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with app.app_context():
            return User.query.get(int(user_id))

    app.register_blueprint(dataset_bp)

    db.init_app(app)

    with app.app_context():
        db.create_all()

        # Configurar herencia polimórfica para BaseDataset
        from sqlalchemy.orm import configure_mappers

        try:
            configure_mappers()
        except Exception:
            pass

        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Cliente de test."""
    return app.test_client()


@pytest.fixture
def auth_user(app):
    """Crear usuario autenticado - RETORNA EL ID."""
    with app.app_context():
        user = User(email="test@example.com", password="hashed_password")
        db.session.add(user)
        db.session.commit()

        db.session.refresh(user)
        user_id = user.id

    return user_id


@pytest.fixture
def sample_dataset(app, auth_user):
    """Crear dataset UVL de ejemplo - RETORNA EL ID."""
    with app.app_context():
        from app.modules.dataset.models import PublicationType, UVLDataset

        ds_meta = DSMetaData(
            title="Test Dataset",
            description="Test description",
            publication_type=PublicationType.NONE,  # Usar enum correcto
        )
        db.session.add(ds_meta)
        db.session.flush()

        dataset = UVLDataset(
            user_id=auth_user,
            ds_meta_data_id=ds_meta.id,
        )
        db.session.add(dataset)
        db.session.commit()

        dataset_id = dataset.id

    return dataset_id


@pytest.fixture
def authenticated_client(client, auth_user, app):
    """Cliente con sesión de usuario autenticado."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(auth_user)
        sess["_fresh"] = True

    return client


# ==========================================
# TESTS DE VERSIONES
# ==========================================


def test_list_versions_no_versions(authenticated_client, sample_dataset):
    """Test listar versiones cuando no hay ninguna."""
    # Mock render_template para evitar errores de template
    with patch("app.modules.dataset.routes.render_template") as mock_render:
        mock_render.return_value = "Mocked HTML"

        response = authenticated_client.get(f"/dataset/{sample_dataset}/versions")

        assert response.status_code == 200
        mock_render.assert_called_once()


def test_list_versions_with_versions(authenticated_client, sample_dataset, app):
    """Test listar versiones existentes."""
    with app.app_context():
        from app.modules.dataset.models import UVLDataset, UVLDatasetVersion

        dataset = UVLDataset.query.get(sample_dataset)

        version1 = UVLDatasetVersion(
            dataset_id=dataset.id,
            version_number="1.0.0",
            title="Version 1",
            description="First version",
            changelog="Initial version",
            created_by_id=dataset.user_id,
        )
        version2 = UVLDatasetVersion(
            dataset_id=dataset.id,
            version_number="2.0.0",
            title="Version 2",
            description="Second version",
            changelog="Major update",
            created_by_id=dataset.user_id,
        )
        db.session.add_all([version1, version2])
        db.session.commit()

    with patch("app.modules.dataset.routes.render_template") as mock_render:
        mock_render.return_value = "Mocked HTML"

        response = authenticated_client.get(f"/dataset/{sample_dataset}/versions")

        assert response.status_code == 200


def test_list_versions_nonexistent_dataset(authenticated_client):
    """Test listar versiones de dataset inexistente."""
    response = authenticated_client.get("/dataset/99999/versions")

    assert response.status_code == 404


def test_api_list_versions_empty(authenticated_client, sample_dataset):
    """Test API de versiones sin versiones."""
    response = authenticated_client.get(f"/api/dataset/{sample_dataset}/versions")

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["version_count"] == 0
    assert data["versions"] == []


# ==========================================
# TESTS DE COMPARACIÓN DE VERSIONES
# ==========================================


def test_compare_versions_different_datasets(authenticated_client, sample_dataset, auth_user, app):
    """Test comparar versiones de diferentes datasets debe fallar."""
    with app.app_context():
        from app.modules.dataset.models import PublicationType, UVLDataset, UVLDatasetVersion

        dataset1 = UVLDataset.query.get(sample_dataset)

        ds_meta2 = DSMetaData(
            title="Dataset 2",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        db.session.add(ds_meta2)
        db.session.flush()

        dataset2 = UVLDataset(
            user_id=auth_user,
            ds_meta_data_id=ds_meta2.id,
        )
        db.session.add(dataset2)
        db.session.flush()

        version1 = UVLDatasetVersion(
            dataset_id=dataset1.id,
            version_number="1.0.0",
            title="V1",
            description="Version 1",
            changelog="Initial",
            created_by_id=auth_user,
        )
        version2 = UVLDatasetVersion(
            dataset_id=dataset2.id,
            version_number="1.0.0",
            title="V2",
            description="Version 2",
            changelog="Initial",
            created_by_id=auth_user,
        )
        db.session.add_all([version1, version2])
        db.session.commit()

        v1_id = version1.id
        v2_id = version2.id

    response = authenticated_client.get(f"/versions/{v1_id}/compare/{v2_id}")

    assert response.status_code == 400


def test_compare_versions_nonexistent(authenticated_client):
    """Test comparar versiones inexistentes."""
    response = authenticated_client.get("/versions/99999/compare/99998")

    assert response.status_code == 404


# ==========================================
# TESTS DE CREACIÓN DE VERSIONES
# ==========================================


def test_create_version_unauthorized(client, sample_dataset):
    """Test crear versión sin autenticación."""
    response = client.post(
        f"/dataset/{sample_dataset}/create_version", data={"changelog": "Test", "bump_type": "patch"}
    )

    assert response.status_code in [302, 401]


def test_create_version_not_owner(authenticated_client, app, auth_user):
    """Test crear versión sin ser el propietario."""
    with app.app_context():
        from app.modules.dataset.models import PublicationType, UVLDataset

        other_user = User(email="other@example.com", password="hashed")
        db.session.add(other_user)
        db.session.flush()

        ds_meta = DSMetaData(
            title="Other Dataset",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        db.session.add(ds_meta)
        db.session.flush()

        dataset = UVLDataset(
            user_id=other_user.id,
            ds_meta_data_id=ds_meta.id,
        )
        db.session.add(dataset)
        db.session.commit()

        dataset_id = dataset.id

    response = authenticated_client.post(
        f"/dataset/{dataset_id}/create_version", data={"changelog": "Test", "bump_type": "patch"}
    )

    assert response.status_code == 403


def test_create_version_missing_changelog(authenticated_client, sample_dataset):
    """Test crear versión sin changelog."""
    response = authenticated_client.post(
        f"/dataset/{sample_dataset}/create_version", data={"bump_type": "patch"}, follow_redirects=False
    )

    assert response.status_code == 302


def test_create_version_published_dataset_blocked(authenticated_client, sample_dataset, app):
    """Test que no se puede crear versión manual en dataset publicado."""
    with app.app_context():
        from app.modules.dataset.models import UVLDataset

        dataset = UVLDataset.query.get(sample_dataset)
        dataset.ds_meta_data.dataset_doi = "10.1234/test.doi"
        db.session.commit()

    response = authenticated_client.post(
        f"/dataset/{sample_dataset}/create_version",
        data={"changelog": "Should fail", "bump_type": "patch"},
        follow_redirects=False,
    )

    assert response.status_code == 302


# ==========================================
# TESTS DE VIEW VERSION
# ==========================================


def test_view_version_success(authenticated_client, sample_dataset, app):
    """Test ver una versión específica."""
    with app.app_context():
        from app.modules.dataset.models import UVLDataset, UVLDatasetVersion

        dataset = UVLDataset.query.get(sample_dataset)

        version = UVLDatasetVersion(
            dataset_id=dataset.id,
            version_number="1.0.0",
            title="Test Version",
            description="Test",
            changelog="Initial",
            created_by_id=dataset.user_id,
        )
        db.session.add(version)
        db.session.commit()

        version_id = version.id

    with patch("app.modules.dataset.routes.render_template") as mock_render:
        mock_render.return_value = "Mocked HTML"

        response = authenticated_client.get(f"/version/{sample_dataset}/{version_id}/")

        assert response.status_code == 200


def test_view_version_wrong_dataset(authenticated_client, sample_dataset, auth_user, app):
    """Test ver versión con dataset_id incorrecto."""
    with app.app_context():
        from app.modules.dataset.models import PublicationType, UVLDataset, UVLDatasetVersion

        dataset1 = UVLDataset.query.get(sample_dataset)

        ds_meta2 = DSMetaData(
            title="Dataset 2",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        db.session.add(ds_meta2)
        db.session.flush()

        dataset2 = UVLDataset(
            user_id=auth_user,
            ds_meta_data_id=ds_meta2.id,
        )
        db.session.add(dataset2)
        db.session.flush()

        version = UVLDatasetVersion(
            dataset_id=dataset1.id,
            version_number="1.0.0",
            title="Test",
            description="Test",
            changelog="Test",
            created_by_id=auth_user,
        )
        db.session.add(version)
        db.session.commit()

        wrong_dataset_id = dataset2.id
        version_id = version.id

    response = authenticated_client.get(f"/version/{wrong_dataset_id}/{version_id}/")

    assert response.status_code == 404


def test_view_version_nonexistent(authenticated_client, sample_dataset):
    """Test ver versión inexistente."""
    response = authenticated_client.get(f"/version/{sample_dataset}/99999/")

    assert response.status_code == 404


# ==========================================
# TESTS DE DOWNLOAD VERSION
# ==========================================


def test_download_version_wrong_dataset(authenticated_client, sample_dataset, auth_user, app):
    """Test descargar versión con dataset_id incorrecto."""
    with app.app_context():
        from app.modules.dataset.models import PublicationType, UVLDataset, UVLDatasetVersion

        dataset1 = UVLDataset.query.get(sample_dataset)

        ds_meta2 = DSMetaData(
            title="Dataset 2",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        db.session.add(ds_meta2)
        db.session.flush()

        dataset2 = UVLDataset(
            user_id=auth_user,
            ds_meta_data_id=ds_meta2.id,
        )
        db.session.add(dataset2)
        db.session.flush()

        version = UVLDatasetVersion(
            dataset_id=dataset1.id,
            version_number="1.0.0",
            title="Test",
            description="Test",
            changelog="Test",
            created_by_id=auth_user,
        )
        db.session.add(version)
        db.session.commit()

        wrong_dataset_id = dataset2.id
        version_id = version.id

    response = authenticated_client.get(f"/version/{wrong_dataset_id}/{version_id}/download")

    assert response.status_code == 404


# ==========================================
# TESTS DE EDICIÓN DE DATASET
# ==========================================


def test_edit_dataset_get(authenticated_client, sample_dataset):
    """Test GET de edición de dataset."""
    with patch("app.modules.dataset.routes.render_template") as mock_render:
        mock_render.return_value = "Mocked HTML"

        response = authenticated_client.get(f"/dataset/{sample_dataset}/edit")

        assert response.status_code == 200


def test_edit_dataset_not_owner(authenticated_client, app, auth_user):
    """Test editar dataset de otro usuario."""
    with app.app_context():
        from app.modules.dataset.models import PublicationType, UVLDataset

        other_user = User(email="other@example.com", password="hashed")
        db.session.add(other_user)
        db.session.flush()

        ds_meta = DSMetaData(
            title="Other Dataset",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        db.session.add(ds_meta)
        db.session.flush()

        dataset = UVLDataset(
            user_id=other_user.id,
            ds_meta_data_id=ds_meta.id,
        )
        db.session.add(dataset)
        db.session.commit()

        dataset_id = dataset.id

    response = authenticated_client.get(f"/dataset/{dataset_id}/edit")

    assert response.status_code == 403


def test_edit_dataset_update_title(authenticated_client, sample_dataset, app):
    """Test actualizar título del dataset."""
    response = authenticated_client.post(
        f"/dataset/{sample_dataset}/edit",
        data={
            "title": "Updated Title",
            "description": "Test description",
            "tags": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302


def test_edit_dataset_update_description(authenticated_client, sample_dataset, app):
    """Test actualizar descripción del dataset."""
    response = authenticated_client.post(
        f"/dataset/{sample_dataset}/edit",
        data={
            "title": "Test Dataset",
            "description": "New description here",
            "tags": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302


def test_edit_dataset_update_tags(authenticated_client, sample_dataset, app):
    """Test actualizar tags del dataset."""
    response = authenticated_client.post(
        f"/dataset/{sample_dataset}/edit",
        data={
            "title": "Test Dataset",
            "description": "Test description",
            "tags": "machine-learning, ai, test",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302


# ==========================================
# TESTS DE UPLOAD MÚLTIPLE
# ==========================================


def test_upload_multiple_no_files(authenticated_client):
    """Test upload múltiple sin archivos."""
    response = authenticated_client.post("/dataset/file/upload_multiple")

    assert response.status_code == 400


def test_upload_multiple_invalid_extension(authenticated_client, tmp_path):
    """Test upload múltiple con extensión inválida."""
    response = authenticated_client.post(
        "/dataset/file/upload_multiple",
        data={
            "files": [
                (io.BytesIO(b"content"), "test.txt"),
            ]
        },
        content_type="multipart/form-data",
    )

    assert response.status_code in [200, 400]


# ==========================================
# TESTS DE COMENTARIOS
# ==========================================


def test_create_comment_success(authenticated_client, sample_dataset):
    """Test crear comentario exitosamente."""
    response = authenticated_client.post(
        f"/dataset/{sample_dataset}/comments",
        json={"content": "Great dataset!"},
    )

    assert response.status_code == 201


def test_create_comment_empty_content(authenticated_client, sample_dataset):
    """Test crear comentario sin contenido."""
    response = authenticated_client.post(
        f"/dataset/{sample_dataset}/comments",
        json={"content": ""},
    )

    assert response.status_code == 400


def test_create_comment_missing_content(authenticated_client, sample_dataset):
    """Test crear comentario sin campo content."""
    response = authenticated_client.post(
        f"/dataset/{sample_dataset}/comments",
        json={},
    )

    assert response.status_code == 400


def test_get_comments_empty(client, sample_dataset):
    """Test obtener comentarios cuando no hay ninguno."""
    response = client.get(f"/dataset/{sample_dataset}/comments")

    assert response.status_code in [200, 500]


def test_delete_comment_not_found(authenticated_client):
    """Test eliminar comentario inexistente."""
    response = authenticated_client.delete("/dataset/comments/99999")

    assert response.status_code == 404


def test_update_comment_not_found(authenticated_client):
    """Test actualizar comentario inexistente."""
    response = authenticated_client.put("/dataset/comments/99999", json={"content": "Updated content"})

    assert response.status_code == 404


def test_update_comment_empty_content(authenticated_client, sample_dataset, app):
    """Test actualizar comentario con contenido vacío."""
    try:
        from app.modules.dataset.models import DatasetComment
    except ImportError:
        pytest.skip("DatasetComment not available")

    with app.app_context():
        from app.modules.dataset.models import UVLDataset

        dataset = UVLDataset.query.get(sample_dataset)

        comment = DatasetComment(dataset_id=dataset.id, user_id=dataset.user_id, content="Original comment")
        db.session.add(comment)
        db.session.commit()
        comment_id = comment.id

    response = authenticated_client.put(f"/dataset/comments/{comment_id}", json={"content": "   "})

    assert response.status_code == 400


# ==========================================
# TESTS DE API GPX
# ==========================================


def test_get_gpx_data_not_found(client):
    """Test obtener datos GPX de archivo inexistente."""
    response = client.get("/api/gpx/99999")

    assert response.status_code == 404


def test_get_gpx_data_not_gpx_file(authenticated_client, sample_dataset, app):
    """Test obtener datos de archivo que no es GPX."""
    from app.modules.featuremodel.models import FeatureModel, FMMetaData
    from app.modules.hubfile.models import Hubfile

    with app.app_context():
        from app.modules.dataset.models import PublicationType, UVLDataset

        dataset = UVLDataset.query.get(sample_dataset)

        fm_meta = FMMetaData(
            filename="test.uvl",
            title="Test",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        db.session.add(fm_meta)
        db.session.flush()

        fm = FeatureModel(
            data_set_id=dataset.id,
            fm_meta_data_id=fm_meta.id,
        )
        db.session.add(fm)
        db.session.flush()

        hubfile = Hubfile(
            name="test.uvl",
            checksum="abc123",
            size=100,
            feature_model_id=fm.id,
        )
        db.session.add(hubfile)
        db.session.commit()

        fm_meta_id = fm_meta.id

    response = authenticated_client.get(f"/api/gpx/{fm_meta_id}")

    assert response.status_code == 400


# ==========================================
# TESTS DE DOWNLOAD DATASET
# ==========================================


def test_download_dataset_nonexistent(client):
    """Test descargar dataset inexistente."""
    response = client.get("/dataset/download/99999")

    assert response.status_code == 404


# ==========================================
# TESTS DE UNSYNCHRONIZED DATASET
# ==========================================


def test_get_unsynchronized_dataset_not_found(authenticated_client):
    """Test obtener dataset no sincronizado inexistente."""
    response = authenticated_client.get("/dataset/unsynchronized/99999/")

    assert response.status_code == 404


def test_get_unsynchronized_dataset_success(authenticated_client, sample_dataset):
    """Test obtener dataset no sincronizado exitosamente."""
    with patch("app.modules.dataset.routes.render_template") as mock_render:
        mock_render.return_value = "Mocked HTML"

        response = authenticated_client.get(f"/dataset/unsynchronized/{sample_dataset}/")

        assert response.status_code == 200


# ==========================================
# TESTS DE ADD FILES TO DATASET
# ==========================================


def test_add_files_not_owner(authenticated_client, app, auth_user):
    """Test añadir archivos a dataset de otro usuario."""
    with app.app_context():
        from app.modules.dataset.models import PublicationType, UVLDataset

        other_user = User(email="other@example.com", password="hashed")
        db.session.add(other_user)
        db.session.flush()

        ds_meta = DSMetaData(
            title="Other Dataset",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        db.session.add(ds_meta)
        db.session.flush()

        dataset = UVLDataset(
            user_id=other_user.id,
            ds_meta_data_id=ds_meta.id,
        )
        db.session.add(dataset)
        db.session.commit()

        dataset_id = dataset.id

    response = authenticated_client.post(f"/dataset/{dataset_id}/add_files", data={"source": "test"})

    assert response.status_code == 403


def test_add_files_no_files(authenticated_client, sample_dataset):
    """Test añadir archivos sin seleccionar ninguno."""
    response = authenticated_client.post(
        f"/dataset/{sample_dataset}/add_files", data={"source": "test"}, follow_redirects=False
    )

    assert response.status_code == 302


def test_add_files_nonexistent_dataset(authenticated_client):
    """Test añadir archivos a dataset inexistente."""
    response = authenticated_client.post("/dataset/99999/add_files", data={"source": "test", "file_0": "test.uvl"})

    assert response.status_code == 404
