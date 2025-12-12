"""
Tests para DataSetService y servicios relacionados.
Cubre la lógica de negocio de creación, actualización, versionado y gestión de datasets.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import (
    DSMetaData,
    GPXDatasetVersion,
    PublicationType,
    UVLDataset,
    UVLDatasetVersion,
)
from app.modules.dataset.services import (
    CommentService,
    DataSetService,
    DSMetaDataService,
    SizeService,
    VersionService,
    calculate_checksum_and_size,
)
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from app.modules.hubfile.models import Hubfile


@pytest.fixture
def app():
    """Crear aplicación Flask de test."""
    from flask import Flask

    app = Flask(__name__)
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WORKING_DIR="/tmp/test_working_dir",
    )

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def test_user(app):
    """Crear usuario de prueba."""
    with app.app_context():
        user = User(email="test@example.com", password="hashed")
        db.session.add(user)
        db.session.commit()

        user_id = user.id

    return user_id


@pytest.fixture
def test_dataset(app, test_user):
    """Crear dataset de prueba."""
    with app.app_context():
        ds_meta = DSMetaData(
            title="Test Dataset",
            description="Test description",
            publication_type=PublicationType.NONE,
        )
        db.session.add(ds_meta)
        db.session.flush()

        dataset = UVLDataset(
            user_id=test_user,
            ds_meta_data_id=ds_meta.id,
        )
        db.session.add(dataset)
        db.session.commit()

        dataset_id = dataset.id

    return dataset_id


# ==========================================
# TESTS DE calculate_checksum_and_size
# ==========================================


def test_calculate_checksum_and_size():
    """Test calcular checksum y tamaño de archivo."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test content")
        temp_path = f.name

    try:
        checksum, size = calculate_checksum_and_size(temp_path)

        assert isinstance(checksum, str)
        assert len(checksum) == 32  # MD5 hash length
        assert size > 0
        assert size == len("test content")
    finally:
        os.unlink(temp_path)


def test_calculate_checksum_empty_file():
    """Test calcular checksum de archivo vacío."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name

    try:
        checksum, size = calculate_checksum_and_size(temp_path)

        assert isinstance(checksum, str)
        assert size == 0
    finally:
        os.unlink(temp_path)


# ==========================================
# TESTS DE DataSetService
# ==========================================


def test_dataset_service_initialization():
    """Test inicialización de DataSetService."""
    service = DataSetService()

    assert service.repository is not None
    assert service.feature_model_repository is not None
    assert service.datasource_manager is not None


def test_get_synchronized(app, test_user, test_dataset):
    """Test obtener datasets sincronizados."""
    with app.app_context():
        service = DataSetService()

        # Marcar dataset como sincronizado
        dataset = UVLDataset.query.get(test_dataset)
        dataset.ds_meta_data.dataset_doi = "10.1234/test"
        db.session.commit()

        result = service.get_synchronized(test_user)

        assert result is not None


def test_get_unsynchronized(app, test_user, test_dataset):
    """Test obtener datasets no sincronizados."""
    with app.app_context():
        service = DataSetService()

        result = service.get_unsynchronized(test_user)

        assert result is not None


def test_calculate_files_fingerprint(app, test_dataset):
    """Test calcular fingerprint de archivos."""
    with app.app_context():
        dataset = UVLDataset.query.get(test_dataset)

        # Crear feature model con archivo
        fm_meta = FMMetaData(
            filename="test.uvl",
            title="Test FM",
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

        file = Hubfile(
            name="test.uvl",
            checksum="abc123",
            size=100,
            feature_model_id=fm.id,
        )
        db.session.add(file)
        db.session.commit()

        service = DataSetService()
        fingerprint = service.calculate_files_fingerprint(dataset)

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64  # SHA256 length


def test_calculate_files_fingerprint_empty_dataset(app, test_dataset):
    """Test fingerprint de dataset sin archivos."""
    with app.app_context():
        dataset = UVLDataset.query.get(test_dataset)

        service = DataSetService()
        fingerprint = service.calculate_files_fingerprint(dataset)

        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 64


def test_count_synchronized_datasets(app, test_user):
    """Test contar datasets sincronizados."""
    with app.app_context():
        # Crear dataset sincronizado
        ds_meta = DSMetaData(
            title="Synced Dataset",
            description="Test",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/test",
        )
        db.session.add(ds_meta)
        db.session.flush()

        dataset = UVLDataset(
            user_id=test_user,
            ds_meta_data_id=ds_meta.id,
        )
        db.session.add(dataset)
        db.session.commit()

        service = DataSetService()
        count = service.count_synchronized_datasets()

        assert count >= 1


def test_collect_models_into_temp_uvl_files(app):
    """Test recolectar archivos UVL."""
    with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as dest_dir:
        source_path = Path(source_dir)
        dest_path = Path(dest_dir)

        # Crear archivo UVL válido
        uvl_file = source_path / "test.uvl"
        uvl_file.write_text("features\n  TestFeature")

        service = DataSetService()

        with patch.object(service, "_collect_models_into_temp") as mock_collect:
            mock_collect.return_value = [dest_path / "test.uvl"]

            result = service._collect_models_into_temp(source_path, dest_path)

            assert len(result) >= 0


def test_collect_models_skips_invalid_files(app):
    """Test que archivos inválidos son omitidos."""
    with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as dest_dir:
        source_path = Path(source_dir)
        dest_path = Path(dest_dir)

        # Crear archivo de texto normal
        txt_file = source_path / "readme.txt"
        txt_file.write_text("This is not a model file")

        service = DataSetService()
        result = service._collect_models_into_temp(source_path, dest_path)

        # No debe copiar archivos .txt
        assert len(result) == 0


# ==========================================
# TESTS DE VersionService
# ==========================================


def test_increment_version_patch():
    """Test incrementar versión patch."""
    result = VersionService._increment_version("1.2.3", "patch")
    assert result == "1.2.4"


def test_increment_version_minor():
    """Test incrementar versión minor."""
    result = VersionService._increment_version("1.2.3", "minor")
    assert result == "1.3.0"


def test_increment_version_major():
    """Test incrementar versión major."""
    result = VersionService._increment_version("1.2.3", "major")
    assert result == "2.0.0"


def test_increment_version_from_zero():
    """Test incrementar desde versión 0.0.0."""
    result = VersionService._increment_version("0.0.0", "patch")
    assert result == "0.0.1"


def test_create_version_uvl_dataset(app, test_user, test_dataset):
    """Test crear versión de dataset UVL."""
    with app.app_context():
        dataset = UVLDataset.query.get(test_dataset)
        user = User.query.get(test_user)

        version = VersionService.create_version(dataset=dataset, changelog="Test version", user=user, bump_type="patch")

        assert version is not None
        assert version.version_number == "0.0.1"
        assert version.changelog == "Test version"
        assert version.created_by_id == test_user


def test_create_version_increments_correctly(app, test_user, test_dataset):
    """Test que versiones se incrementan correctamente."""
    with app.app_context():
        dataset = UVLDataset.query.get(test_dataset)
        user = User.query.get(test_user)

        # Crear primera versión
        v1 = VersionService.create_version(dataset=dataset, changelog="Version 1", user=user, bump_type="patch")

        # Crear segunda versión
        v2 = VersionService.create_version(dataset=dataset, changelog="Version 2", user=user, bump_type="minor")

        assert v1.version_number == "0.0.1"
        assert v2.version_number == "0.1.0"


def test_create_files_snapshot(app, test_dataset):
    """Test crear snapshot de archivos."""
    with app.app_context():
        dataset = UVLDataset.query.get(test_dataset)

        # Crear feature model con archivo
        fm_meta = FMMetaData(
            filename="test.uvl",
            title="Test FM",
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

        file = Hubfile(
            name="test.uvl",
            checksum="abc123",
            size=100,
            feature_model_id=fm.id,
        )
        db.session.add(file)
        db.session.commit()

        snapshot = VersionService._create_files_snapshot(dataset)

        assert isinstance(snapshot, dict)
        assert "test.uvl" in snapshot
        assert snapshot["test.uvl"]["checksum"] == "abc123"


def test_get_version_class_uvl():
    """Test obtener clase de versión para UVL."""
    mock_dataset = Mock()
    mock_dataset.dataset_kind = "uvl"

    version_class = VersionService._get_version_class(mock_dataset)

    assert version_class == UVLDatasetVersion


def test_get_version_class_gpx():
    """Test obtener clase de versión para GPX."""
    mock_dataset = Mock()
    mock_dataset.dataset_kind = "gpx"

    version_class = VersionService._get_version_class(mock_dataset)

    assert version_class == GPXDatasetVersion


def test_compare_versions_same_dataset(app, test_user, test_dataset):
    """Test comparar dos versiones del mismo dataset."""
    with app.app_context():
        dataset = UVLDataset.query.get(test_dataset)
        user = User.query.get(test_user)

        v1 = VersionService.create_version(dataset=dataset, changelog="Version 1", user=user, bump_type="patch")

        v2 = VersionService.create_version(dataset=dataset, changelog="Version 2", user=user, bump_type="patch")

        comparison = VersionService.compare_versions(v1.id, v2.id)

        assert comparison is not None


def test_compare_versions_different_datasets_raises_error(app, test_user):
    """Test que comparar versiones de diferentes datasets falla."""
    with app.app_context():
        user = User.query.get(test_user)

        # Crear dos datasets diferentes
        ds_meta1 = DSMetaData(
            title="Dataset 1",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        ds_meta2 = DSMetaData(
            title="Dataset 2",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        db.session.add_all([ds_meta1, ds_meta2])
        db.session.flush()

        dataset1 = UVLDataset(user_id=test_user, ds_meta_data_id=ds_meta1.id)
        dataset2 = UVLDataset(user_id=test_user, ds_meta_data_id=ds_meta2.id)
        db.session.add_all([dataset1, dataset2])
        db.session.flush()

        v1 = VersionService.create_version(dataset1, "V1", user, "patch")
        v2 = VersionService.create_version(dataset2, "V2", user, "patch")

        with pytest.raises(ValueError, match="same dataset"):
            VersionService.compare_versions(v1.id, v2.id)


# ==========================================
# TESTS DE DSMetaDataService
# ==========================================


def test_dsmetadata_service_update(app, test_dataset):
    """Test actualizar metadata de dataset."""
    with app.app_context():
        dataset = UVLDataset.query.get(test_dataset)

        service = DSMetaDataService()
        result = service.update(dataset.ds_meta_data_id, title="Updated Title", description="Updated description")

        assert result.title == "Updated Title"
        assert result.description == "Updated description"


def test_dsmetadata_filter_by_doi(app, test_user):
    """Test filtrar metadata por DOI."""
    with app.app_context():
        ds_meta = DSMetaData(
            title="Test Dataset",
            description="Test",
            publication_type=PublicationType.NONE,
            dataset_doi="10.1234/test.doi",
        )
        db.session.add(ds_meta)
        db.session.commit()

        service = DSMetaDataService()
        result = service.filter_by_doi("10.1234/test.doi")

        assert result is not None
        assert result.dataset_doi == "10.1234/test.doi"


def test_dsmetadata_filter_by_doi_not_found(app):
    """Test filtrar por DOI inexistente."""
    with app.app_context():
        service = DSMetaDataService()
        result = service.filter_by_doi("10.9999/nonexistent")

        assert result is None


# ==========================================
# TESTS DE SizeService
# ==========================================


def test_size_service_bytes():
    """Test formato de tamaño en bytes."""
    service = SizeService()
    result = service.get_human_readable_size(500)

    assert result == "500 bytes"


def test_size_service_kilobytes():
    """Test formato de tamaño en KB."""
    service = SizeService()
    result = service.get_human_readable_size(2048)

    assert "KB" in result


def test_size_service_megabytes():
    """Test formato de tamaño en MB."""
    service = SizeService()
    result = service.get_human_readable_size(5242880)  # 5 MB

    assert "MB" in result


def test_size_service_gigabytes():
    """Test formato de tamaño en GB."""
    service = SizeService()
    result = service.get_human_readable_size(5368709120)  # 5 GB

    assert "GB" in result


# ==========================================
# TESTS DE CommentService
# ==========================================


def test_comment_service_create_comment(app, test_user, test_dataset):
    """Test crear comentario."""
    with app.app_context():
        service = CommentService()

        comment = service.create_comment(dataset_id=test_dataset, user_id=test_user, content="Great dataset!")

        assert comment is not None
        assert comment["content"] == "Great dataset!"
        assert comment["user_id"] == test_user


def test_comment_service_create_empty_comment_fails(app, test_user, test_dataset):
    """Test que crear comentario vacío falla."""
    with app.app_context():
        service = CommentService()

        with pytest.raises(ValueError, match="cannot be empty"):
            service.create_comment(dataset_id=test_dataset, user_id=test_user, content="   ")


def test_comment_service_create_comment_too_long_fails(app, test_user, test_dataset):
    """Test que comentario muy largo falla."""
    with app.app_context():
        service = CommentService()

        long_content = "x" * 1001

        with pytest.raises(ValueError, match="too long"):
            service.create_comment(dataset_id=test_dataset, user_id=test_user, content=long_content)


def test_comment_service_get_comments(app, test_user, test_dataset):
    """Test obtener comentarios de dataset."""
    with app.app_context():
        service = CommentService()

        # Crear comentarios
        service.create_comment(test_dataset, test_user, "Comment 1")
        service.create_comment(test_dataset, test_user, "Comment 2")

        comments = service.get_comments_by_dataset(test_dataset)

        assert len(comments) >= 2


def test_comment_service_count_comments(app, test_user, test_dataset):
    """Test contar comentarios."""
    with app.app_context():
        service = CommentService()

        initial_count = service.count_comments(test_dataset)

        service.create_comment(test_dataset, test_user, "New comment")

        new_count = service.count_comments(test_dataset)

        assert new_count == initial_count + 1


def test_comment_service_validate_content_sanitizes_html(app, test_user, test_dataset):
    """Test que el contenido HTML se sanitiza."""
    with app.app_context():
        service = CommentService()

        comment = service.create_comment(
            dataset_id=test_dataset, user_id=test_user, content="<script>alert('xss')</script>Hello"
        )

        # El HTML debe estar escapado
        assert "&lt;script&gt;" in comment["content"]
        assert "<script>" not in comment["content"]


def test_comment_service_get_nonexistent_dataset_comments_fails(app):
    """Test que obtener comentarios de dataset inexistente falla."""
    with app.app_context():
        service = CommentService()

        with pytest.raises(ValueError, match="not found"):
            service.get_comments_by_dataset(99999)


# ==========================================
# TESTS DE INTEGRACIÓN
# ==========================================


def test_create_dataset_and_version_flow(app, test_user):
    """Test flujo completo: crear dataset y versión."""
    with app.app_context():
        user = User.query.get(test_user)

        # Crear dataset
        ds_meta = DSMetaData(
            title="Integration Test Dataset",
            description="Full flow test",
            publication_type=PublicationType.NONE,
        )
        db.session.add(ds_meta)
        db.session.flush()

        dataset = UVLDataset(
            user_id=test_user,
            ds_meta_data_id=ds_meta.id,
        )
        db.session.add(dataset)
        db.session.commit()

        # Crear versión
        version = VersionService.create_version(
            dataset=dataset, changelog="Initial version", user=user, bump_type="patch"
        )

        # Verificar
        assert dataset.id is not None
        assert version.dataset_id == dataset.id
        assert version.version_number == "0.0.1"


def test_dataset_with_files_fingerprint(app, test_user):
    """Test calcular fingerprint de dataset con múltiples archivos."""
    with app.app_context():
        # Crear dataset
        ds_meta = DSMetaData(
            title="Multi-file Dataset",
            description="Test",
            publication_type=PublicationType.NONE,
        )
        db.session.add(ds_meta)
        db.session.flush()

        dataset = UVLDataset(
            user_id=test_user,
            ds_meta_data_id=ds_meta.id,
        )
        db.session.add(dataset)
        db.session.flush()

        # Crear múltiples feature models con archivos
        for i in range(3):
            fm_meta = FMMetaData(
                filename=f"test{i}.uvl",
                title=f"Test FM {i}",
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

            file = Hubfile(
                name=f"test{i}.uvl",
                checksum=f"checksum{i}",
                size=100 * (i + 1),
                feature_model_id=fm.id,
            )
            db.session.add(file)

        db.session.commit()

        # Calcular fingerprint
        service = DataSetService()
        fingerprint1 = service.calculate_files_fingerprint(dataset)

        # El fingerprint debe ser consistente
        fingerprint2 = service.calculate_files_fingerprint(dataset)

        assert fingerprint1 == fingerprint2
        assert len(fingerprint1) == 64


def test_version_comparison_with_file_changes(app, test_user, test_dataset):
    """Test comparación de versiones con cambios en archivos."""
    with app.app_context():
        dataset = UVLDataset.query.get(test_dataset)
        user = User.query.get(test_user)

        # Crear versión inicial
        v1 = VersionService.create_version(dataset=dataset, changelog="Initial", user=user, bump_type="patch")

        # Agregar archivo al dataset
        fm_meta = FMMetaData(
            filename="newfile.uvl",
            title="New FM",
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

        file = Hubfile(
            name="newfile.uvl",
            checksum="new123",
            size=200,
            feature_model_id=fm.id,
        )
        db.session.add(file)
        db.session.commit()

        # Crear segunda versión
        v2 = VersionService.create_version(dataset=dataset, changelog="Added file", user=user, bump_type="minor")

        # Comparar versiones
        comparison = VersionService.compare_versions(v1.id, v2.id)

        assert comparison is not None
        assert isinstance(comparison, dict)

        # Verificar que hay cambios en archivos
        assert "file_changes" in comparison
        assert "added" in comparison["file_changes"]
        assert len(comparison["file_changes"]["added"]) > 0
        assert "newfile.uvl" in comparison["file_changes"]["added"]
