from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.community.models import Community, CommunityDataset, CommunityFollower, CommunityRequest
from app.modules.community.services import CommunityService
from app.modules.dataset.models import DSMetaData, GPXDataset, PublicationType

# ----------------------------
# FIXTURES
# ----------------------------


@pytest.fixture(scope="module")
def setup_user(test_client):
    """Crea un usuario de prueba si no existe."""
    user = User.query.filter_by(email="test@example.com").first()
    if not user:
        user = User(email="test@example.com", password="test1234")
        db.session.add(user)
        db.session.commit()
    return user


# ----------------------------
# TESTS MODELOS / SERVICIOS
# ----------------------------


def test_create_community_creator_becomes_curator(test_client, setup_user):
    service = CommunityService()
    community, error = service.create_community(
        name="Test Community Curator",
        description="Comunidad de prueba para verificar que el creador es curador",
        creator_id=setup_user.id,
    )
    assert error is None
    assert community is not None
    assert community.creator_id == setup_user.id
    assert service.is_curator(community.id, setup_user.id) is True
    curators = community.get_curators_list()
    assert len(curators) == 1
    assert curators[0].id == setup_user.id

    db.session.delete(community)
    db.session.commit()


def test_update_community_description_and_logo(test_client, setup_user):
    service = CommunityService()

    community, _ = service.create_community("UpdateTestCommunity", "Old description", setup_user.id)
    assert community is not None

    mock_logo_file = MagicMock()
    mock_logo_file.filename = "logo.png"

    with patch.object(service, "_save_logo", return_value="/uploads/communities/logo.png"):
        success, error = service.update_community(community.id, description="New description", logo_file=mock_logo_file)

    assert success is True
    assert error is None

    updated_community = service.get_by_slug(community.slug)
    assert updated_community.description == "New description"
    assert updated_community.logo_path.endswith("logo.png")

    db.session.delete(updated_community)
    db.session.commit()


def test_get_eligible_datasets_excludes_already_added(test_client, setup_user):
    service = CommunityService()

    community, error = service.create_community(
        name="Test Community Datasets",
        description="Comunidad para probar filtrado de datasets",
        creator_id=setup_user.id,
    )
    assert error is None

    metadata1 = DSMetaData(title="Dataset 1", description="Ya en comunidad", publication_type=PublicationType.NONE)
    metadata2 = DSMetaData(
        title="Dataset 2", description="Con solicitud pendiente", publication_type=PublicationType.NONE
    )
    metadata3 = DSMetaData(title="Dataset 3", description="Elegible", publication_type=PublicationType.NONE)
    db.session.add_all([metadata1, metadata2, metadata3])
    db.session.flush()

    dataset1 = GPXDataset(user_id=setup_user.id, ds_meta_data_id=metadata1.id)
    dataset2 = GPXDataset(user_id=setup_user.id, ds_meta_data_id=metadata2.id)
    dataset3 = GPXDataset(user_id=setup_user.id, ds_meta_data_id=metadata3.id)
    db.session.add_all([dataset1, dataset2, dataset3])
    db.session.flush()

    cd1 = CommunityDataset(community_id=community.id, dataset_id=dataset1.id, added_by_id=setup_user.id)
    db.session.add(cd1)

    cr = CommunityRequest(
        community_id=community.id,
        dataset_id=dataset2.id,
        requester_id=setup_user.id,
        status=CommunityRequest.STATUS_PENDING,
        message="Solicitud de prueba",
    )
    db.session.add(cr)
    db.session.commit()

    eligible = service.get_eligible_datasets_for_community(setup_user.id, community.id)
    assert len(eligible) == 1
    assert eligible[0].id == dataset3.id

    db.session.delete(cr)
    db.session.delete(cd1)
    db.session.delete(community)
    db.session.delete(dataset1)
    db.session.delete(dataset2)
    db.session.delete(dataset3)
    db.session.delete(metadata1)
    db.session.delete(metadata2)
    db.session.delete(metadata3)
    db.session.commit()


def test_approve_request_adds_dataset_to_community(test_client, setup_user):
    service = CommunityService()

    community, _ = service.create_community(
        name="Test Community Approval", description="Comunidad para aprobar solicitudes", creator_id=setup_user.id
    )

    metadata = DSMetaData(title="Dataset para aprobar", description="", publication_type=PublicationType.NONE)
    db.session.add(metadata)
    db.session.flush()
    dataset = GPXDataset(user_id=setup_user.id, ds_meta_data_id=metadata.id)
    db.session.add(dataset)
    db.session.flush()

    success, error = service.propose_dataset(community.id, dataset.id, setup_user.id, "Por favor aprobar")
    assert success and error is None

    pending = service.get_pending_requests(community.id)[0]
    success, error = service.approve_request(pending.id, setup_user.id, "Aprobado")
    assert success and error is None

    db.session.refresh(pending)
    assert pending.status == CommunityRequest.STATUS_APPROVED

    community_datasets = service.get_community_datasets(community.id)
    assert any(d.id == dataset.id for d in community_datasets)

    db.session.delete(community)
    db.session.delete(dataset)
    db.session.delete(metadata)
    db.session.commit()


def test_reject_request_does_not_add_dataset(test_client, setup_user):
    service = CommunityService()

    community, _ = service.create_community(
        name="Test Community Rejection", description="Comunidad para probar rechazo", creator_id=setup_user.id
    )

    metadata = DSMetaData(title="Dataset para rechazar", description="", publication_type=PublicationType.NONE)
    db.session.add(metadata)
    db.session.flush()
    dataset = GPXDataset(user_id=setup_user.id, ds_meta_data_id=metadata.id)
    db.session.add(dataset)
    db.session.flush()

    success, error = service.propose_dataset(community.id, dataset.id, setup_user.id, "Por favor considerar")
    assert success and error is None

    pending = service.get_pending_requests(community.id)[0]
    success, error = service.reject_request(pending.id, setup_user.id, "Rechazado")
    assert success and error is None

    db.session.refresh(pending)
    assert pending.status == CommunityRequest.STATUS_REJECTED

    community_datasets = service.get_community_datasets(community.id)
    assert all(d.id != dataset.id for d in community_datasets)

    db.session.delete(community)
    db.session.delete(dataset)
    db.session.delete(metadata)
    db.session.commit()


# ----------------------------
# TEST FOLLOW / UNFOLLOW
# ----------------------------


def test_follow_and_unfollow_community(test_client, setup_user):
    service = CommunityService()

    community, _ = service.create_community(
        name="Test Community Follow", description="Comunidad para probar follow", creator_id=setup_user.id
    )

    follower = User(email="follower@example.com", password="test1234")
    db.session.add(follower)
    db.session.commit()

    success, error = service.follow_community(follower.id, community.id)
    assert success is True
    assert error is None

    success, error = service.follow_community(follower.id, community.id)
    assert success is False
    assert error == "User is already following this community"

    success, error = service.unfollow_community(follower.id, community.id)
    assert success is True
    assert error is None

    success, error = service.unfollow_community(follower.id, community.id)
    assert success is False
    assert error == "User is not currently following this community"

    db.session.delete(follower)
    db.session.delete(community)
    db.session.commit()


# ----------------------------
# TEST MODELOS (repr y helpers)
# ----------------------------


def test_community_repr_contains_name():
    c = Community(name="Test", slug="test-slug", description="desc", creator_id=1)
    r = repr(c)
    assert "Community<" in r
    assert "Test" in r


def test_follower_model_repr():
    f = CommunityFollower(user_id=1, community_id=2)
    assert repr(f) == "CommunityFollower<user_id=1, community_id=2>"


def test_community_request_status_helpers():
    r = CommunityRequest(community_id=1, dataset_id=2, requester_id=3, status=CommunityRequest.STATUS_PENDING)
    assert r.is_pending() is True
    assert r.status == CommunityRequest.STATUS_PENDING


# ----------------------------
# TEST GET CURATOR INFO / USER IDS
# ----------------------------


def test_get_curator_info_returns_dict(test_client, setup_user):
    db.session.rollback()
    service = CommunityService()

    info = service.get_curator_info(setup_user.id)

    assert isinstance(info, dict)
    assert info["id"] == setup_user.id
    assert info["email"] == setup_user.email
    assert isinstance(info["name"], str)
    assert isinstance(info["surname"], str)


def test_get_curator_user_ids_returns_list(test_client, setup_user):
    db.session.rollback()
    service = CommunityService()

    community, _ = service.create_community(
        "CuratorListCommunity",
        "Desc",
        setup_user.id,
    )
    ids = service.get_curator_user_ids(community.id)
    assert setup_user.id in ids

    db.session.delete(community)
    db.session.commit()
