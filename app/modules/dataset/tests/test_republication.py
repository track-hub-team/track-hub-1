"""
Tests para el sistema de republicación con versionado de Zenodo.
Valida los tres flujos principales:
1. Primera publicación
2. Republicación sin cambios (mismo DOI)
3. Republicación con cambios (nuevo DOI, mismo conceptdoi)
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.dataset.models import BaseDataset, DSMetaData, PublicationType
from app.modules.dataset.services import DataSetService
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from app.modules.hubfile.models import Hubfile


@pytest.fixture
def user(test_client, clean_database):
    """Usuario de prueba"""
    user = User(email="republication@test.com")
    user.set_password("password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def metadata():
    """Metadatos del dataset"""
    metadata = DSMetaData(
        title="Test Republication Dataset",
        description="Testing republication flows",
        publication_type=PublicationType.NONE,
        deposition_id=12345,
        conceptrecid=None,
        tags="test,republication",
    )
    db.session.add(metadata)
    db.session.commit()
    return metadata


@pytest.fixture
def dataset(user, metadata):
    """Dataset de prueba con archivos"""
    dataset = BaseDataset(
        user_id=user.id,
        ds_meta_data_id=metadata.id,
        dataset_kind="uvl",
        created_at=datetime.utcnow(),
    )
    db.session.add(dataset)
    db.session.commit()

    fm_metadata = FMMetaData(
        filename="model1.uvl",
        title="Test Model",
        description="Test",
        publication_type=PublicationType.NONE,
    )
    db.session.add(fm_metadata)
    db.session.flush()  # Obtener el ID

    feature_model = FeatureModel(data_set_id=dataset.id, fm_meta_data_id=fm_metadata.id)
    db.session.add(feature_model)
    db.session.flush()  # Obtener el ID antes de crear el archivo

    file = Hubfile(name="model1.uvl", checksum="abc123", size=1024, feature_model_id=feature_model.id)
    db.session.add(file)

    db.session.commit()
    return dataset


def test_first_publication(test_client, user, dataset):
    """Test: Primera publicación crea v1 y guarda conceptrecid"""
    login(test_client, "republication@test.com", "password")

    with patch("app.modules.dataset.routes.zenodo_service") as mock_zenodo:
        mock_zenodo.publish_deposition.return_value = {}
        mock_zenodo.get_doi.return_value = "10.9999/fakenodo.999.v1"
        mock_zenodo.get_conceptrecid.return_value = 999

        response = test_client.post(f"/dataset/{dataset.id}/publish")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "published successfully" in data["message"]
        assert data["doi"] == "10.9999/fakenodo.999.v1"

        # Verificar que se guardó el DOI y conceptrecid
        db.session.refresh(dataset.ds_meta_data)
        assert dataset.ds_meta_data.dataset_doi == "10.9999/fakenodo.999.v1"
        assert dataset.ds_meta_data.conceptrecid == 999
        assert dataset.ds_meta_data.files_fingerprint is not None

    logout(test_client)


def test_republication_without_changes(test_client, user, dataset):
    """Test: Republicación sin cambios en archivos mantiene el mismo DOI"""
    dataset.ds_meta_data.dataset_doi = "10.9999/fakenodo.999.v1"
    dataset.ds_meta_data.conceptrecid = 999

    service = DataSetService()
    initial_fingerprint = service.calculate_files_fingerprint(dataset)
    dataset.ds_meta_data.files_fingerprint = initial_fingerprint
    db.session.commit()

    login(test_client, "republication@test.com", "password")

    with patch("app.modules.dataset.routes.zenodo_service") as mock_zenodo:
        mock_zenodo.publish_deposition.return_value = {}
        mock_zenodo.get_doi.return_value = "10.9999/fakenodo.999.v1"  # Mismo DOI
        mock_zenodo.get_conceptrecid.return_value = 999

        response = test_client.post(f"/dataset/{dataset.id}/publish")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "re-published successfully" in data["message"]
        assert data["doi"] == "10.9999/fakenodo.999.v1"  # Sin incremento de versión

        # Verificar que el fingerprint no cambió
        db.session.refresh(dataset.ds_meta_data)
        assert dataset.ds_meta_data.files_fingerprint == initial_fingerprint

    logout(test_client)


def test_republication_with_changes(test_client, user, dataset):
    """Test: Republicación con cambios en archivos crea nueva versión (v2)"""
    # Simular que ya fue publicado con v1
    dataset.ds_meta_data.dataset_doi = "10.9999/fakenodo.999.v1"
    dataset.ds_meta_data.conceptrecid = 999

    # Guardar fingerprint inicial
    service = DataSetService()
    initial_fingerprint = service.calculate_files_fingerprint(dataset)
    dataset.ds_meta_data.files_fingerprint = initial_fingerprint
    db.session.commit()

    # Añadir un nuevo archivo (simulando cambios)
    new_fm_metadata = FMMetaData(
        filename="model2.uvl",
        title="New Model",
        description="Added feature",
        publication_type=PublicationType.NONE,
    )
    db.session.add(new_fm_metadata)
    db.session.flush()

    new_feature_model = FeatureModel(data_set_id=dataset.id, fm_meta_data_id=new_fm_metadata.id)
    db.session.add(new_feature_model)
    db.session.flush()

    new_file = Hubfile(name="model2.uvl", checksum="def456", size=2048, feature_model_id=new_feature_model.id)
    db.session.add(new_file)
    db.session.commit()

    # Calcular nuevo fingerprint (debería ser diferente)
    new_fingerprint = service.calculate_files_fingerprint(dataset)
    assert new_fingerprint != initial_fingerprint, "Fingerprint should change when files are added"

    login(test_client, "republication@test.com", "password")

    # Mock: Fakenodo detecta cambios y crea v2
    with patch("app.modules.dataset.routes.zenodo_service") as mock_zenodo:
        mock_zenodo.publish_deposition.return_value = {}
        mock_zenodo.get_doi.return_value = "10.9999/fakenodo.999.v2"  # Nueva versión
        mock_zenodo.get_conceptrecid.return_value = 999  # Mismo conceptrecid

        response = test_client.post(f"/dataset/{dataset.id}/publish")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "re-published successfully" in data["message"]
        assert data["doi"] == "10.9999/fakenodo.999.v2"  # Versión incrementada

        # Verificar que se actualizó el DOI y el fingerprint
        db.session.refresh(dataset.ds_meta_data)
        assert dataset.ds_meta_data.dataset_doi == "10.9999/fakenodo.999.v2"
        assert dataset.ds_meta_data.conceptrecid == 999  # Se mantiene
        assert dataset.ds_meta_data.files_fingerprint == new_fingerprint

    logout(test_client)


def test_calculate_fingerprint(dataset):
    """Test: Fingerprint se calcula correctamente"""
    service = DataSetService()
    fingerprint = service.calculate_files_fingerprint(dataset)

    # Debe ser un hash SHA256 (64 caracteres hexadecimales)
    assert len(fingerprint) == 64
    assert all(c in "0123456789abcdef" for c in fingerprint)

    # Calcular de nuevo debe dar el mismo resultado
    fingerprint2 = service.calculate_files_fingerprint(dataset)
    assert fingerprint == fingerprint2


def test_fingerprint_changes_with_files(dataset):
    """Test: Fingerprint cambia cuando cambian los archivos"""
    service = DataSetService()
    fingerprint1 = service.calculate_files_fingerprint(dataset)

    # Añadir archivo
    new_fm_metadata = FMMetaData(
        filename="model3.uvl",
        title="Another Model",
        description="Test",
        publication_type=PublicationType.NONE,
    )
    db.session.add(new_fm_metadata)
    db.session.flush()

    new_feature_model = FeatureModel(data_set_id=dataset.id, fm_meta_data_id=new_fm_metadata.id)
    db.session.add(new_feature_model)
    db.session.flush()

    new_file = Hubfile(name="model3.uvl", checksum="xyz789", size=512, feature_model_id=new_feature_model.id)
    db.session.add(new_file)
    db.session.commit()

    fingerprint2 = service.calculate_files_fingerprint(dataset)
    assert fingerprint1 != fingerprint2


def test_publish_without_deposition(test_client, user):
    """Test: No se puede publicar sin deposition_id"""
    # Crear metadata sin deposition_id
    metadata = DSMetaData(
        title="No Deposition Test",
        description="Testing",
        publication_type=PublicationType.NONE,
        deposition_id=None,  # Sin deposition_id
        tags="test",
    )
    db.session.add(metadata)
    db.session.commit()

    dataset = BaseDataset(
        user_id=user.id,
        ds_meta_data_id=metadata.id,
        dataset_kind="uvl",
        created_at=datetime.utcnow(),
    )
    db.session.add(dataset)
    db.session.commit()

    login(test_client, "republication@test.com", "password")

    response = test_client.post(f"/dataset/{dataset.id}/publish")
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "not uploaded to Zenodo" in data["message"]

    logout(test_client)
