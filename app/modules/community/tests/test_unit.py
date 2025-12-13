from unittest.mock import MagicMock, patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.community.models import (
    Community,
    CommunityDataset,
    CommunityFollower,
    CommunityRequest,
)
from app.modules.community.repositories import CommunityCuratorRepository, CommunityRepository, FollowerRepository
from app.modules.community.seeders import CommunitySeeder
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


def test_create_community_prevents_duplicate_name(test_client):
    service = CommunityService()
    c, _ = service.create_community("UniqueName", "d", 1)
    assert c is not None

    c2, error = service.create_community("UniqueName", "d2", 1)
    assert c2 is None
    assert isinstance(error, str) and "already exists" in error

    db.session.delete(c)
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


# ----------------------------
# TEST REPOSITORY
# ----------------------------


def test_repository_get_by_slug(test_client):
    repo = CommunityRepository()
    c = Community(name="Repo Test", slug="repo-test", description="", creator_id=1)
    db.session.add(c)
    db.session.commit()

    found = repo.get_by_slug("repo-test")
    assert found is not None
    assert found.slug == "repo-test"

    db.session.delete(c)
    db.session.commit()


def test_repository_search_by_name_or_description(test_client):
    repo = CommunityRepository()
    c = Community(name="SearchableName", slug="search-test", description="desc", creator_id=1)
    db.session.add(c)
    db.session.commit()

    results = repo.search_by_name_or_description("Searchable")
    assert any(x.id == c.id for x in results)

    db.session.delete(c)
    db.session.commit()


def test_repository_get_community_curators(test_client):
    curator_repo = CommunityCuratorRepository()
    c = Community(name="Curator Repo Test", slug="curator-repo-test", description="", creator_id=1)
    db.session.add(c)
    db.session.commit()

    curators = curator_repo.get_community_curators(c.id)
    assert isinstance(curators, list)

    db.session.delete(c)
    db.session.commit()


# ----------------------------
# TEST RUTAS SIMPLES
# ----------------------------


def test_route_follow_redirects(test_client):
    user = User(email="routeuser@example.com", password="test1234")
    db.session.add(user)
    db.session.commit()

    with test_client.session_transaction() as sess:
        sess["user_id"] = user.id

    response = test_client.post("/community/1/follow", follow_redirects=False)
    assert response.status_code in (302, 303)

    db.session.delete(user)
    db.session.commit()


def test_route_unfollow_redirects(test_client):
    user = User(email="routeuser2@example.com", password="test1234")
    db.session.add(user)
    db.session.commit()

    with test_client.session_transaction() as sess:
        sess["user_id"] = user.id

    response = test_client.post("/community/1/unfollow", follow_redirects=False)
    assert response.status_code in (302, 303)

    db.session.delete(user)
    db.session.commit()


# ----------------------------
# TEST SEEDER
# ----------------------------


def test_seeder_runs_minimal(test_client, setup_user):

    users = User.query.limit(2).all()
    while len(users) < 2:
        u = User(email=f"seeduser{len(users)}@example.com", password="test1234")
        db.session.add(u)
        db.session.commit()
        users.append(u)

    datasets = GPXDataset.query.limit(2).all()
    while len(datasets) < 2:
        meta = DSMetaData(
            title=f"Seed Dataset {len(datasets)}",
            description="Auto-generated",
            publication_type=PublicationType.NONE,
        )
        db.session.add(meta)
        db.session.commit()
        ds = GPXDataset(user_id=users[0].id, ds_meta_data_id=meta.id)
        db.session.add(ds)
        db.session.commit()
        datasets.append(ds)

    seeder = CommunitySeeder()
    seeder.run()

    seeded = Community.query.filter(
        Community.name.in_(["Software Engineering Research", "Machine Learning Models"])
    ).all()
    assert len(seeded) == 2

    db.session.rollback()


# ----------------------------
# TEST FREPOSITORY FOLLOW EMAIL
# ----------------------------


def test_get_followers_users_returns_followers(test_client):
    repo = FollowerRepository()

    user = User(email="author@example.com", password="test1234")
    follower1 = User(email="f1@example.com", password="test1234")
    follower2 = User(email="f2@example.com", password="test1234")

    db.session.add_all([user, follower1, follower2])
    db.session.commit()

    repo.follow(follower1.id, user.id)
    repo.follow(follower2.id, user.id)

    followers = repo.get_followers_users(user.id)
    follower_ids = {u.id for u in followers}

    assert follower1.id in follower_ids
    assert follower2.id in follower_ids
    assert user.id not in follower_ids

    repo.unfollow(follower1.id, user.id)
    repo.unfollow(follower2.id, user.id)

    db.session.delete(follower1)
    db.session.delete(follower2)
    db.session.delete(user)
    db.session.commit()


def test_get_followers_users_empty(test_client):
    repo = FollowerRepository()

    user = User(email="lonely@example.com", password="test1234")
    db.session.add(user)
    db.session.commit()

    followers = repo.get_followers_users(user.id)

    assert followers == []

    db.session.delete(user)
    db.session.commit()


def test_follow_user_success(test_client):
    service = CommunityService()

    user1 = User(email="u1@example.com", password="1234")
    user2 = User(email="u2@example.com", password="1234")
    db.session.add_all([user1, user2])
    db.session.commit()

    record, error = service.follow_user(user1.id, user2.id)

    assert error is None
    assert record is not None
    assert record.follower_id == user1.id
    assert record.followed_id == user2.id

    db.session.delete(record)
    db.session.delete(user1)
    db.session.delete(user2)
    db.session.commit()


def test_follow_user_self_not_allowed(test_client):
    service = CommunityService()

    user = User(email="self@example.com", password="1234")
    db.session.add(user)
    db.session.commit()

    record, error = service.follow_user(user.id, user.id)

    assert record is None
    assert error == "You cannot follow yourself"

    db.session.delete(user)
    db.session.commit()


def test_unfollow_user_success(test_client):
    service = CommunityService()

    follower = User(email="follower_u@example.com", password="1234")
    followed = User(email="followed_u@example.com", password="1234")
    db.session.add_all([follower, followed])
    db.session.commit()

    service.follow_user(follower.id, followed.id)

    ok, error = service.unfollow_user(follower.id, followed.id)

    assert ok is True
    assert error is None
    assert service.is_following_user(follower.id, followed.id) is False

    db.session.delete(follower)
    db.session.delete(followed)
    db.session.commit()


def test_unfollow_user_not_following(test_client):
    service = CommunityService()

    follower = User(email="nf1@example.com", password="1234")
    followed = User(email="nf2@example.com", password="1234")
    db.session.add_all([follower, followed])
    db.session.commit()

    ok, error = service.unfollow_user(follower.id, followed.id)

    assert ok is None
    assert error == "You are not following this user"

    db.session.delete(follower)
    db.session.delete(followed)
    db.session.commit()


def test_get_followed_communities_returns_list(test_client):
    service = CommunityService()

    user = User(email="gfc@example.com", password="1234")
    creator = User(email="creator_gfc@example.com", password="1234")
    db.session.add_all([user, creator])
    db.session.commit()

    community, _ = service.create_community("GFC", "desc", creator.id)
    service.follow_community(user.id, community.id)

    communities = service.get_followed_communities(user.id)

    assert len(communities) == 1
    assert communities[0].id == community.id

    db.session.rollback()


def test_is_following_user(test_client):
    service = CommunityService()

    u1 = User(email="ifu1@example.com", password="1234")
    u2 = User(email="ifu2@example.com", password="1234")
    db.session.add_all([u1, u2])
    db.session.commit()

    assert service.is_following_user(u1.id, u2.id) is False

    service.follow_user(u1.id, u2.id)

    assert service.is_following_user(u1.id, u2.id) is True

    db.session.rollback()


def test_add_curator_community_not_found():
    service = CommunityService()

    success, error = service.add_curator(community_id=9999, user_id=1)

    assert success is False
    assert error == "Community not found"


def test_remove_curator_community_not_found():
    service = CommunityService()

    success, error = service.remove_curator(community_id=9999, user_id=1, requester_id=2)

    assert success is False
    assert error == "Community not found"


def test_follow_user_repository_exception(test_client):
    service = CommunityService()

    with patch(
        "app.modules.community.services.FollowerRepository.follow",
        side_effect=Exception("DB error"),
    ):
        record, error = service.follow_user(1, 2)

    assert record is None
    assert "Error following user" in error


def test_unfollow_community_not_following_unit(test_client):
    service = CommunityService()

    user = User(email="unit_unf@example.com", password="1234")
    community = Community(
        name="Unit Unfollow",
        slug="unit-unf",
        description="desc",
        creator_id=1,
    )
    db.session.add_all([user, community])
    db.session.commit()

    success, error = service.unfollow_community(user.id, community.id)

    assert success is False
    assert error == "User is not currently following this community"

    db.session.rollback()


def test_follow_community_not_found_unit():
    service = CommunityService()

    success, error = service.follow_community(user_id=1, community_id=9999)

    assert success is False
    assert error == "Community not found"


def test_follow_user_exception_unit():
    service = CommunityService()

    with patch(
        "app.modules.community.services.FollowerRepository.follow",
        side_effect=Exception("DB fail"),
    ):
        record, error = service.follow_user(1, 2)

    assert record is None
    assert "Error following user" in error


def test_follow_user_self_unit():
    service = CommunityService()

    record, error = service.follow_user(1, 1)

    assert record is None
    assert error == "You cannot follow yourself"


def test_follow_user_followed_not_exists_unit(test_client):
    service = CommunityService()

    follower = User(email="fu_ne1@example.com", password="1234")
    db.session.add(follower)
    db.session.commit()

    record, error = service.follow_user(follower.id, 9999)

    # El repositorio lanza IntegrityError internamente
    assert record is None
    assert error is not None

    db.session.rollback()


def test_unfollow_user_not_following_unit(test_client):
    service = CommunityService()

    u1 = User(email="ufu_nf1@example.com", password="1234")
    u2 = User(email="ufu_nf2@example.com", password="1234")
    db.session.add_all([u1, u2])
    db.session.commit()

    ok, error = service.unfollow_user(u1.id, u2.id)

    assert ok is None
    assert error == "You are not following this user"

    db.session.rollback()


def test_get_followed_users_unit(test_client):
    service = CommunityService()

    u1 = User(email="gfu1@example.com", password="1234")
    u2 = User(email="gfu2@example.com", password="1234")
    u3 = User(email="gfu3@example.com", password="1234")
    db.session.add_all([u1, u2, u3])
    db.session.commit()

    assert service.get_followed_users(u1.id) == []

    service.follow_user(u1.id, u2.id)
    service.follow_user(u1.id, u3.id)

    followed = service.get_followed_users(u1.id)
    followed_ids = {u.id for u in followed}

    assert followed_ids == {u2.id, u3.id}

    db.session.rollback()
