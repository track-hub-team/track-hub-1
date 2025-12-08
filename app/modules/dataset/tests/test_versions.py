from datetime import datetime

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login
from app.modules.dataset.models import BaseDataset, DatasetVersion, DSMetaData, PublicationType


@pytest.fixture
def user(test_client, clean_database):
    user = User(email="testversions@test.com")
    user.set_password("password")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def metadata(test_client):
    metadata = DSMetaData(
        title="Test Dataset", description="Test dataset for version testing", publication_type=PublicationType.NONE
    )
    db.session.add(metadata)
    db.session.commit()
    return metadata


@pytest.fixture
def dataset(user, metadata):
    dataset = BaseDataset(
        user_id=user.id,
        ds_meta_data_id=metadata.id,
        dataset_kind="uvl",
        created_at=datetime.utcnow(),
    )
    db.session.add(dataset)
    db.session.commit()
    return dataset


@pytest.fixture
def versions(dataset, user):
    v1 = DatasetVersion(
        dataset_id=dataset.id,
        version_number="0.0.1",
        title="Initial version",
        changelog="Auto generated",
        files_snapshot={"model1.uvl": {"size": 123}},
        created_by_id=user.id,
    )
    v2 = DatasetVersion(
        dataset_id=dataset.id,
        version_number="0.0.2",
        title="Fix #1",
        changelog="Changed X",
        files_snapshot={"model1.uvl": {"size": 130}},
        created_by_id=user.id,
    )
    db.session.add_all([v1, v2])
    db.session.commit()
    return [v1, v2]


def test_list_versions(test_client, dataset, versions):
    res = test_client.get(f"/dataset/{dataset.id}/versions")
    assert res.status_code == 200
    html = res.data.decode()

    assert "v0.0.2" in html
    assert "v0.0.1" in html

    assert "View version" in html


def test_view_version(test_client, dataset, versions):
    v = versions[0]
    res = test_client.get(f"/version/{dataset.id}/{v.id}/")
    assert res.status_code == 200
    html = res.data.decode()

    assert v.version_number in html
    assert v.title in html
    assert v.changelog in html


def fake_zip(*args, **kwargs):
    import tempfile

    f = tempfile.NamedTemporaryFile(delete=False)
    f.write(b"test zip content")
    f.close()
    return f.name


def test_download_version_zip(test_client, dataset, versions, monkeypatch):
    from app.modules.dataset import services

    monkeypatch.setattr(services.VersionService, "build_version_zip", fake_zip)

    v = versions[0]
    res = test_client.get(f"/version/{dataset.id}/{v.id}/download")

    assert res.status_code == 200
    assert res.headers["Content-Type"] == "application/zip"
    assert res.headers["Content-Disposition"].startswith("attachment")
    assert b"test zip content" in res.data


def test_first_version_has_view_button(test_client, dataset, versions):
    res = test_client.get(f"/dataset/{dataset.id}/versions")
    html = res.data.decode()

    assert "View version" in html


def test_first_version_has_no_compare(test_client, dataset, versions):
    res = test_client.get(f"/dataset/{dataset.id}/versions")
    html = res.data.decode()

    assert html.count("Compare with previous") == 1


def test_create_version(test_client, dataset, user):
    login(test_client, "testversions@test.com", "password")

    data = {"bump_type": "patch", "changelog": "Test changes"}
    res = test_client.post(f"/dataset/{dataset.id}/create_version", data=data, follow_redirects=True)

    assert res.status_code == 200
    new_version = DatasetVersion.query.filter_by(changelog="Test changes").first()
    assert new_version is not None


def test_publish_dataset_unauthorized(test_client, dataset):
    """Test que usuario no autenticado no puede publicar"""
    res = test_client.post(f"/dataset/{dataset.id}/publish")
    assert res.status_code == 400


def test_publish_dataset_already_published(test_client, dataset, user):
    """Test que no se puede publicar un dataset ya publicado"""
    from app.modules.conftest import logout

    dataset.ds_meta_data.dataset_doi = "10.1234/test"
    dataset.ds_meta_data.tags = "test,tags"
    db.session.commit()

    logout(test_client)
    login(test_client, "testversions@test.com", "password")
    res = test_client.post(f"/dataset/{dataset.id}/publish")
    assert res.status_code == 400
    data = res.get_json()
    assert "already published" in data["message"]


def test_publish_dataset_no_deposition(test_client, dataset, user):
    """Test que no se puede publicar sin deposition_id"""
    from app.modules.conftest import logout

    logout(test_client)
    login(test_client, "testversions@test.com", "password")
    res = test_client.post(f"/dataset/{dataset.id}/publish")
    assert res.status_code == 400
    data = res.get_json()
    assert "not uploaded to Zenodo" in data["message"]


def test_publish_dataset_success(test_client, dataset, user, monkeypatch):
    """Test publicación exitosa de dataset"""
    dataset.ds_meta_data.deposition_id = 123
    db.session.commit()

    class MockZenodoService:
        def publish_deposition(self, deposition_id):
            return {"doi": "10.9999/fakenodo.test123"}

        def get_doi(self, deposition_id):
            return "10.9999/fakenodo.test123"

    from app.modules.conftest import logout
    from app.modules.dataset import routes

    monkeypatch.setattr(routes, "zenodo_service", MockZenodoService())

    logout(test_client)
    login(test_client, "testversions@test.com", "password")
    res = test_client.post(f"/dataset/{dataset.id}/publish")

    assert res.status_code == 200
    data = res.get_json()
    assert data["doi"] == "10.9999/fakenodo.test123"
    assert "successfully" in data["message"]

    db.session.refresh(dataset)
    assert dataset.ds_meta_data.dataset_doi == "10.9999/fakenodo.test123"


def test_cannot_create_version_after_publish(test_client, dataset, user):
    """Test que no se pueden crear versiones después de publicar"""
    from app.modules.conftest import logout

    dataset.ds_meta_data.dataset_doi = "10.1234/test"
    dataset.ds_meta_data.tags = "test,tags"
    db.session.commit()

    logout(test_client)
    login(test_client, "testversions@test.com", "password")
    data = {"bump_type": "patch", "changelog": "Should fail"}
    res = test_client.post(f"/dataset/{dataset.id}/create_version", data=data, follow_redirects=False)

    assert res.status_code == 302


def test_uvl_statistics_calculation(test_client, user, metadata):
    """Test que las estadísticas UVL se calculan correctamente"""
    from app.modules.dataset.models import UVLDataset
    from app.modules.featuremodel.models import FeatureModel, FMMetaData
    from app.modules.hubfile.models import Hubfile

    dataset = UVLDataset(user_id=user.id, ds_meta_data_id=metadata.id, created_at=datetime.utcnow())
    db.session.add(dataset)
    db.session.commit()

    fm_meta = FMMetaData(
        filename="test.uvl", title="Test Model", description="Test", publication_type=PublicationType.NONE
    )
    db.session.add(fm_meta)
    db.session.commit()

    feature_model = FeatureModel(data_set_id=dataset.id, fm_meta_data_id=fm_meta.id)
    db.session.add(feature_model)
    db.session.commit()

    file = Hubfile(name="test.uvl", checksum="abc123", size=100, feature_model_id=feature_model.id)
    db.session.add(file)
    db.session.commit()

    assert len(dataset.feature_models) == 1


def test_model_count_in_version(test_client, dataset, user):
    """Test que el conteo de modelos funciona en versiones"""
    from app.modules.dataset.models import UVLDataset
    from app.modules.featuremodel.models import FeatureModel, FMMetaData

    uvl_dataset = UVLDataset(user_id=user.id, ds_meta_data_id=dataset.ds_meta_data_id, created_at=datetime.utcnow())
    db.session.add(uvl_dataset)
    db.session.commit()

    for i in range(3):
        fm_meta = FMMetaData(
            filename=f"model{i}.uvl", title=f"Model {i}", description="Test", publication_type=PublicationType.NONE
        )
        db.session.add(fm_meta)
        db.session.commit()

        feature_model = FeatureModel(data_set_id=uvl_dataset.id, fm_meta_data_id=fm_meta.id)
        db.session.add(feature_model)

    db.session.commit()

    from app.modules.conftest import logout

    logout(test_client)
    login(test_client, "testversions@test.com", "password")
    data = {"bump_type": "patch", "changelog": "Test version"}
    res = test_client.post(f"/dataset/{uvl_dataset.id}/create_version", data=data, follow_redirects=True)

    assert res.status_code == 200

    version = DatasetVersion.query.filter_by(dataset_id=uvl_dataset.id).first()
    assert version is not None
    assert version.model_count == 3
