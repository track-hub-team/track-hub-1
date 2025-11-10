# tests/test_unit.py

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from app.modules.auth.models import User
from app.modules.community.models import (
    Community,
    CommunityCurator,
    CommunityDataset,
    CommunityRequest,
)
from app.modules.community.repositories import (
    CommunityCuratorRepository,
    CommunityDatasetRepository,
    CommunityRequestRepository,
)
from app.modules.community.services import CommunityService

# ------------------------------
# MODELOS
# ------------------------------


def test_serialize_user_none():
    """_serialize_user debe manejar None correctamente."""
    assert Community._serialize_user(None) is None


def test_community_repr_and_to_dict():
    community = Community(
        id=1,
        name="Test Community",
        slug="test-community",
        description="Description",
        creator_id=42,
        created_at=datetime(2025, 1, 1),
        updated_at=datetime(2025, 1, 2),
        logo_path="logo.png",
        curators=[],
        datasets=[],
    )
    repr_str = repr(community)
    assert "Test Community" in repr_str

    dict_data = community.to_dict()
    assert dict_data["name"] == "Test Community"
    assert dict_data["datasets_count"] == 0
    assert dict_data["curators"] == []


def test_community_curator_and_is_curator():
    user = User(id=1, email="test@test.com")
    curator = CommunityCurator(community_id=10, user_id=user.id)
    curator.user = user
    community = Community(id=10, name="Test", slug="test", description="desc", creator_id=2, curators=[curator])

    assert community.is_curator(user.id) is True
    assert community.get_curators_list() == [user]


def test_community_dataset_to_dict():
    cd = CommunityDataset(community_id=1, dataset_id=2)
    repr_str = repr(cd)
    assert "community_id=1" in repr_str

    dict_data = cd.to_dict()
    assert dict_data["community_id"] == 1
    assert dict_data["dataset_id"] == 2


def test_community_request_methods_and_to_dict():
    requester = User(id=1, email="req@test.com")
    reviewed_by = User(id=2, email="rev@test.com")
    request = CommunityRequest(
        id=1, community_id=10, dataset_id=20, requester=requester, status=CommunityRequest.STATUS_PENDING
    )

    # is_pending
    assert request.is_pending() is True

    # approve
    request.approve(curator_id=reviewed_by.id, comment="ok")
    assert request.status == CommunityRequest.STATUS_APPROVED
    assert request.reviewed_by_id == reviewed_by.id
    assert request.review_comment == "ok"
    assert request.reviewed_at is not None

    # reject
    request.status = CommunityRequest.STATUS_PENDING
    request.reject(curator_id=reviewed_by.id, comment="no")
    assert request.status == CommunityRequest.STATUS_REJECTED
    assert request.review_comment == "no"

    # to_dict con dataset=None y reviewed_by=None
    request.dataset = None
    request.reviewed_by = None
    data = request.to_dict()
    assert data["dataset"] is None
    assert data["reviewed_by"] is None


# ------------------------------
# SERVICIOS
# ------------------------------


@pytest.fixture
def community_service():
    return CommunityService()


@patch("app.modules.community.services.CommunityRepository")
@patch("app.modules.community.services.CommunityCuratorRepository")
@patch("app.modules.community.services.CommunityDatasetRepository")
@patch("app.modules.community.services.db.session")
def test_create_community_success(mock_db_session, mock_dataset_repo, mock_curator_repo, mock_repo, community_service):
    # slug único
    mock_repo.return_value.get_by_slug.return_value = None
    mock_repo.return_value.create.return_value = Community(
        id=1, name="Test", slug="test-slug", description="desc", creator_id=42
    )

    service = CommunityService()
    service.repository = mock_repo.return_value
    service.curator_repository = mock_curator_repo.return_value
    service.dataset_repository = mock_dataset_repo.return_value

    community, error = service.create_community(name="Test", description="desc", creator_id=42)
    assert error is None
    assert community.name == "Test"
    mock_curator_repo.return_value.create.assert_called_once_with(community_id=community.id, user_id=42)
    mock_db_session.commit.assert_called_once()


@patch("app.modules.community.services.CommunityRepository")
@patch("app.modules.community.services.db.session")
def test_create_community_slug_duplicate(mock_db_session, mock_repo):
    # Simula que el slug base ya existe → se genera slug-1
    existing = Community(id=2, slug="test-slug")
    mock_repo.return_value.get_by_slug.side_effect = [existing, None]
    mock_repo.return_value.create.return_value = Community(
        id=1, name="Test", slug="test-slug-1", description="desc", creator_id=42
    )

    service = CommunityService()
    service.repository = mock_repo.return_value
    service.curator_repository = CommunityCuratorRepository()
    service.dataset_repository = CommunityDatasetRepository()

    community, error = service.create_community(name="Test", description="desc", creator_id=42)
    assert error is None
    assert community.slug == "test-slug-1"


@patch("app.modules.community.services.CommunityRepository")
@patch("app.modules.community.services.db.session")
def test_create_community_exception(mock_db_session, mock_repo):
    mock_repo.return_value.get_by_slug.return_value = None
    mock_repo.return_value.create.side_effect = Exception("DB error")
    service = CommunityService()
    service.repository = mock_repo.return_value
    service.curator_repository = CommunityCuratorRepository()
    service.dataset_repository = CommunityDatasetRepository()

    community, error = service.create_community(name="Test", description="desc", creator_id=42)
    assert community is None
    assert "DB error" in error


@patch("app.modules.community.services.CommunityRepository")
def test_get_all_communities(mock_repo, community_service):
    mock_repo.return_value.get_all_with_datasets_count.return_value = ["c1", "c2"]
    service = CommunityService()
    service.repository = mock_repo.return_value

    result = service.get_all()
    assert result == ["c1", "c2"]

    mock_repo.return_value.search_by_name_or_description.return_value = ["search_result"]
    result = service.get_all(query="search")
    assert result == ["search_result"]


@patch("app.modules.community.services.CommunityDatasetRepository")
def test_get_community_datasets(mock_dataset_repo, community_service):
    cd1 = Mock()
    cd1.dataset = "dataset1"
    cd2 = Mock()
    cd2.dataset = "dataset2"
    mock_dataset_repo.return_value.get_community_datasets.return_value = [cd1, cd2]

    service = CommunityService()
    service.dataset_repository = mock_dataset_repo.return_value

    datasets = service.get_community_datasets(1)
    assert datasets == ["dataset1", "dataset2"]


@patch("app.modules.community.services.CommunityCuratorRepository")
def test_is_curator_service(mock_curator_repo, community_service):
    mock_curator_repo.return_value.is_curator.return_value = True
    service = CommunityService()
    service.curator_repository = mock_curator_repo.return_value
    assert service.is_curator(1, 42) is True


# ------------------------------
# REPOSITORIOS
# ------------------------------


def test_community_curator_repository_is_curator_true_and_false():
    repo = CommunityCuratorRepository()
    repo.get_by_community_and_user = Mock(return_value=CommunityCurator())
    assert repo.is_curator(1, 2) is True

    repo.get_by_community_and_user = Mock(return_value=None)
    assert repo.is_curator(1, 2) is False


def test_community_dataset_repository_dataset_in_community():
    repo = CommunityDatasetRepository()
    repo.get_by_community_and_dataset = Mock(return_value=CommunityDataset())
    assert repo.dataset_in_community(1, 1) is True

    repo.get_by_community_and_dataset = Mock(return_value=None)
    assert repo.dataset_in_community(1, 1) is False


def test_community_request_repository_has_pending_request(test_app):
    with test_app.app_context():
        repo = CommunityRequestRepository()
        repo.model = Mock()
        repo.model.query = Mock()

        # Para True
        repo.model.query.filter_by.return_value.first.return_value = CommunityRequest(
            status=CommunityRequest.STATUS_PENDING
        )
        assert repo.has_pending_request(1, 2) is True

        # Para False
        repo.model.query.filter_by.return_value.first.return_value = None
        assert repo.has_pending_request(1, 2) is False
