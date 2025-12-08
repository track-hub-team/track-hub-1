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
    v = versions[0]  # v0.0.1
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
