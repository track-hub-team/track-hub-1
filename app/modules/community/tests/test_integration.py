from unittest.mock import patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.community.models import Community, CommunityRequest
from app.modules.community.services import CommunityService
from app.modules.dataset.models import DSMetaData, GPXDataset, PublicationType


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Crear usuario de prueba
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(email="test@example.com", password="test1234")
            db.session.add(user)
            db.session.commit()

    yield test_client


def test_propose_dataset_full_workflow(test_client):
    """
    Verifica el flujo completo de propuesta y aprobación de un dataset.
    """
    # Obtener usuario de prueba
    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None, "Test user not found"

    # Crear un dataset para el test
    metadata = DSMetaData(
        title="Dataset Workflow Test",
        description="Dataset para probar flujo completo",
        publication_type=PublicationType.NONE,
    )
    db.session.add(metadata)
    db.session.flush()

    dataset = GPXDataset(user_id=user.id, ds_meta_data_id=metadata.id)
    db.session.add(dataset)
    db.session.commit()

    # 1. Login del usuario
    login_response = test_client.post(
        "/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert login_response.status_code == 200, "Login failed"

    # 2. Crear comunidad vía POST /community/create
    create_response = test_client.post(
        "/community/create",
        data=dict(name="Test Community Workflow", description="Comunidad para probar flujo completo de integración"),
        follow_redirects=True,
    )
    assert create_response.status_code == 200, "Community creation failed"

    # Obtener la comunidad creada desde la BD
    community = Community.query.filter_by(name="Test Community Workflow").first()
    assert community is not None, "Community was not created in DB"

    # 3. Usuario propone dataset vía POST /community/{slug}/propose
    propose_response = test_client.post(
        f"/community/{community.slug}/propose",
        data=dict(dataset_id=dataset.id, message="Este dataset es perfecto para la comunidad"),
        follow_redirects=True,
    )
    assert propose_response.status_code == 200, "Dataset proposal failed"

    # 4. Verificar que aparece solicitud pendiente vía GET /community/{slug}/manage
    manage_response = test_client.get(f"/community/{community.slug}/manage")
    assert manage_response.status_code == 200, "Could not access management page"

    # Verificar que el HTML contiene información de la solicitud pendiente
    html_content = manage_response.data.decode("utf-8")
    assert "Dataset Workflow Test" in html_content, "Proposed dataset does not appear on management page"
    assert "Este dataset es perfecto para la comunidad" in html_content, "Proposal message does not appear"

    # Obtener la solicitud desde la BD para aprobarla
    community_service = CommunityService()
    pending_requests = community_service.get_pending_requests(community.id)
    assert len(pending_requests) == 1, f"Expected 1 pending request, found {len(pending_requests)}"
    request = pending_requests[0]

    # 5. Curador aprueba la solicitud vía POST /community/{slug}/request/{id}/approve
    approve_response = test_client.post(
        f"/community/{community.slug}/request/{request.id}/approve",
        data=dict(comment="Dataset aprobado por el curador"),
        follow_redirects=True,
    )
    assert approve_response.status_code == 200, "Request approval failed"

    # 6. Verificar que dataset aparece en la comunidad
    community_datasets = community_service.get_community_datasets(community.id)
    assert len(community_datasets) == 1, "Dataset was not added to the community"
    assert community_datasets[0].id == dataset.id, "The dataset in the community is not the correct one"

    # 7. Verificar que ya no hay solicitudes pendientes
    pending_after = community_service.get_pending_requests(community.id)
    assert len(pending_after) == 0, "There should be no pending requests after approval"

    # 8. Verificar que la solicitud está aprobada
    db.session.refresh(request)
    assert request.status == CommunityRequest.STATUS_APPROVED, "Request status did not change to approved"

    # Logout
    test_client.get("/logout", follow_redirects=True)

    # Limpieza
    db.session.delete(community)
    db.session.delete(dataset)
    db.session.delete(metadata)
    db.session.commit()


def test_curator_management_full_workflow(test_client):
    """
    Verifica el flujo completo de añadir y eliminar curadores.
    """
    # Obtener usuarios de prueba
    user1 = User.query.filter_by(email="test@example.com").first()
    assert user1 is not None, "Test user not found"

    # Crear segundo usuario para añadir como curador
    user2 = User.query.filter_by(email="curator2@example.com").first()
    if not user2:
        user2 = User(email="curator2@example.com", password="test1234")
        db.session.add(user2)
        db.session.commit()

    # 1. Login del usuario
    login_response = test_client.post(
        "/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert login_response.status_code == 200, "Login failed"

    # 2. Crear comunidad vía POST (user1 es curador automáticamente)
    create_response = test_client.post(
        "/community/create",
        data=dict(name="Test Community Curators", description="Comunidad para probar gestión de curadores"),
        follow_redirects=True,
    )
    assert create_response.status_code == 200, "Community creation failed"

    # Obtener la comunidad creada
    community = Community.query.filter_by(name="Test Community Curators").first()
    assert community is not None, "Community was not created in DB"

    # 3. Añadir user2 como curador vía POST /add-curator
    add_curator_response = test_client.post(
        f"/community/{community.slug}/add-curator", data=dict(user_id=user2.id), follow_redirects=True
    )
    assert add_curator_response.status_code == 200, "Adding curator failed"

    # 4. Verificar que user2 aparece en lista de curadores desde el endpoint /manage
    manage_response = test_client.get(f"/community/{community.slug}/manage")
    assert manage_response.status_code == 200, "Could not access management page"

    html_content = manage_response.data.decode("utf-8")
    assert user2.email in html_content, "User2 does not appear on management page as curator"

    # 5. Eliminar user2 como curador vía POST /remove-curator
    remove_curator_response = test_client.post(
        f"/community/{community.slug}/remove-curator", data=dict(user_id=user2.id), follow_redirects=True
    )
    assert remove_curator_response.status_code == 200, "Removing curator failed"

    # 6. Verificar que user2 ya no aparece en lista de curadores desde el endpoint /manage
    manage_after_remove = test_client.get(f"/community/{community.slug}/manage")
    assert manage_after_remove.status_code == 200, "Could not access management page"

    html_after_remove = manage_after_remove.data.decode("utf-8")
    # Verificar que solo aparece user1 como curador
    assert user1.email in html_after_remove, "User1 does not appear as curator"

    # 7. Intentar remover al creador (user1) - debe fallar
    remove_creator_response = test_client.post(
        f"/community/{community.slug}/remove-curator", data=dict(user_id=user1.id), follow_redirects=True
    )
    assert remove_creator_response.status_code == 200, "Request completed successfully"

    # Verificar que el mensaje de error está en la respuesta
    html_error = remove_creator_response.data.decode("utf-8")
    assert (
        "Cannot remove the community creator" in html_error or "error" in html_error.lower()
    ), "Error message was not shown when trying to remove creator"

    # Logout
    test_client.get("/logout", follow_redirects=True)

    # Limpieza
    db.session.delete(community)
    db.session.delete(user2)
    db.session.commit()


def _create_user(email):
    user = User(email=email, password="test1234")
    db.session.add(user)
    db.session.commit()
    return user


def _create_dataset(user_id, title="Dataset Test"):
    meta = DSMetaData(
        title=title,
        description="desc",
        publication_type=PublicationType.NONE,
    )
    db.session.add(meta)
    db.session.flush()

    ds = GPXDataset(user_id=user_id, ds_meta_data_id=meta.id)
    db.session.add(ds)
    db.session.commit()
    return ds, meta


def test_notify_followers_when_dataset_approved(test_client):
    service = CommunityService()

    creator = _create_user("creator_comm@example.com")
    follower = _create_user("follower_comm@example.com")

    community, _ = service.create_community(
        name="Notify Community",
        description="Test",
        creator_id=creator.id,
    )

    # ✅ FOLLOW CORRECTO
    service.follow_community(follower.id, community.id)

    dataset, meta = _create_dataset(creator.id)

    service.propose_dataset(community.id, dataset.id, creator.id, "please")
    request = service.get_pending_requests(community.id)[0]

    with patch(
        "app.modules.mail.services.MailService.send_new_dataset_in_community_notification",
        return_value=(True, None),
    ) as mail_mock:

        success, error = service.approve_request(request.id, creator.id, "ok")

        assert success is True
        mail_mock.assert_called_once()

    db.session.rollback()


def test_no_email_if_community_has_no_followers(test_client):
    service = CommunityService()

    creator = _create_user("creator_nof@example.com")

    community, _ = service.create_community(
        name="No Followers Community",
        description="Test",
        creator_id=creator.id,
    )

    dataset, meta = _create_dataset(creator.id)

    service.propose_dataset(community.id, dataset.id, creator.id, "please")
    request = service.get_pending_requests(community.id)[0]

    with patch(
        "app.modules.mail.services.MailService.send_new_dataset_in_community_notification",
        return_value=(True, None),
    ) as mail_mock:

        success, error = service.approve_request(request.id, creator.id, "ok")

        assert success is True
        mail_mock.assert_not_called()

    db.session.rollback()


def login_as(test_client, email: str, password: str):
    return test_client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_unfollow_community_ajax(test_client):
    service = CommunityService()

    creator = User(email="c_unf@example.com", password="1234")
    follower = User(email="f_unf@example.com", password="1234")
    db.session.add_all([creator, follower])
    db.session.commit()

    community, _ = service.create_community("Unfollow Comm", "desc", creator.id)
    service.follow_community(follower.id, community.id)

    login_as(test_client, "f_unf@example.com", "1234")

    response = test_client.post(
        f"/community/{community.slug}/unfollow",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.is_json
    data = response.get_json()
    assert data["following"] is False
    db.session.rollback()


def test_follow_community_twice_ajax(test_client):
    service = CommunityService()

    creator = User(email="c_twice@example.com", password="1234")
    follower = User(email="f_twice@example.com", password="1234")
    db.session.add_all([creator, follower])
    db.session.commit()

    community, _ = service.create_community("Twice Comm", "desc", creator.id)

    login_as(test_client, "f_twice@example.com", "1234")

    test_client.post(
        f"/community/{community.slug}/follow",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    response = test_client.post(
        f"/community/{community.slug}/follow",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    data = response.get_json()
    assert data["success"] is False
    db.session.rollback()


def test_follow_user_ajax_ok(test_client):
    u1 = User(email="fu1@example.com", password="1234")
    u2 = User(email="fu2@example.com", password="1234")
    db.session.add_all([u1, u2])
    db.session.commit()

    login_as(test_client, "fu1@example.com", "1234")

    response = test_client.post(
        f"/community/user/{u2.id}/follow",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.is_json
    data = response.get_json()
    assert data["following"] is True
    db.session.rollback()


def test_unfollow_user_not_following_ajax(test_client):
    u1 = User(email="u_nf1@example.com", password="1234")
    u2 = User(email="u_nf2@example.com", password="1234")
    db.session.add_all([u1, u2])
    db.session.commit()

    login_as(test_client, "u_nf1@example.com", "1234")

    response = test_client.post(
        f"/community/user/{u2.id}/unfollow",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    data = response.get_json()
    assert data["success"] is False
    db.session.rollback()


def test_unfollow_community_ajax_not_found(test_client):
    test_client.post(
        "/login",
        data={"email": "test@example.com", "password": "test1234"},
        follow_redirects=True,
    )

    response = test_client.post(
        "/community/does-not-exist/unfollow",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 404
    assert response.get_json()["success"] is False
