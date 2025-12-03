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
        # Crear usuario de prueba para los tests de integración
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(email="test@example.com", password="test1234")
            db.session.add(user)
            db.session.commit()

    yield test_client


def test_propose_dataset_full_workflow(test_client):
    """
    Prueba de integración que verifica el flujo completo de propuesta y aprobación de un dataset.
    """
    # Obtener usuario de prueba
    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None, "Usuario de prueba no encontrado"

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
    assert login_response.status_code == 200, "Login falló"

    # 2. Crear comunidad vía POST /community/create
    create_response = test_client.post(
        "/community/create",
        data=dict(name="Test Community Workflow", description="Comunidad para probar flujo completo de integración"),
        follow_redirects=True,
    )
    assert create_response.status_code == 200, "Creación de comunidad falló"

    # Obtener la comunidad creada desde la BD
    community = Community.query.filter_by(name="Test Community Workflow").first()
    assert community is not None, "Comunidad no fue creada en la BD"

    # 3. Usuario propone dataset vía POST /community/{slug}/propose
    propose_response = test_client.post(
        f"/community/{community.slug}/propose",
        data=dict(dataset_id=dataset.id, message="Este dataset es perfecto para la comunidad"),
        follow_redirects=True,
    )
    assert propose_response.status_code == 200, "Propuesta de dataset falló"

    # 4. Verificar que aparece solicitud pendiente vía GET /community/{slug}/manage
    manage_response = test_client.get(f"/community/{community.slug}/manage")
    assert manage_response.status_code == 200, "No se pudo acceder a la página de gestión"

    # Verificar que el HTML contiene información de la solicitud pendiente
    html_content = manage_response.data.decode("utf-8")
    assert "Dataset Workflow Test" in html_content, "El dataset propuesto no aparece en la página de gestión"
    assert "Este dataset es perfecto para la comunidad" in html_content, "El mensaje de la propuesta no aparece"

    # Obtener la solicitud desde la BD para aprobarla
    community_service = CommunityService()
    pending_requests = community_service.get_pending_requests(community.id)
    assert len(pending_requests) == 1, f"Se esperaba 1 solicitud pendiente, se encontraron {len(pending_requests)}"
    request = pending_requests[0]

    # 5. Curador aprueba la solicitud vía POST /community/{slug}/request/{id}/approve
    approve_response = test_client.post(
        f"/community/{community.slug}/request/{request.id}/approve",
        data=dict(comment="Dataset aprobado por el curador"),
        follow_redirects=True,
    )
    assert approve_response.status_code == 200, "Aprobación de solicitud falló"

    # 6. Verificar que dataset aparece en la comunidad
    community_datasets = community_service.get_community_datasets(community.id)
    assert len(community_datasets) == 1, "El dataset no fue añadido a la comunidad"
    assert community_datasets[0].id == dataset.id, "El dataset en la comunidad no es el correcto"

    # 7. Verificar que ya no hay solicitudes pendientes
    pending_after = community_service.get_pending_requests(community.id)
    assert len(pending_after) == 0, "No debería haber solicitudes pendientes después de aprobar"

    # 8. Verificar que la solicitud está aprobada
    db.session.refresh(request)
    assert request.status == CommunityRequest.STATUS_APPROVED, "La solicitud no cambió a estado aprobado"

    # Logout
    test_client.get("/logout", follow_redirects=True)

    # Limpieza
    db.session.delete(community)
    db.session.delete(dataset)
    db.session.delete(metadata)
    db.session.commit()


def test_curator_management_full_workflow(test_client):
    """
    Prueba de integración end-to-end para gestión de curadores.
    Verifica el flujo completo de añadir y eliminar curadores desde la interfaz.
    """
    # Obtener usuarios de prueba
    user1 = User.query.filter_by(email="test@example.com").first()
    assert user1 is not None, "Usuario de prueba no encontrado"

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
    assert login_response.status_code == 200, "Login falló"

    # 2. Crear comunidad vía POST (user1 es curador automáticamente)
    create_response = test_client.post(
        "/community/create",
        data=dict(name="Test Community Curators", description="Comunidad para probar gestión de curadores"),
        follow_redirects=True,
    )
    assert create_response.status_code == 200, "Creación de comunidad falló"

    # Obtener la comunidad creada
    community = Community.query.filter_by(name="Test Community Curators").first()
    assert community is not None, "Comunidad no fue creada en la BD"

    # 3. Añadir user2 como curador vía POST /add-curator
    add_curator_response = test_client.post(
        f"/community/{community.slug}/add-curator", data=dict(user_id=user2.id), follow_redirects=True
    )
    assert add_curator_response.status_code == 200, "Añadir curador falló"

    # 4. Verificar que user2 aparece en lista de curadores desde el endpoint /manage
    manage_response = test_client.get(f"/community/{community.slug}/manage")
    assert manage_response.status_code == 200, "No se pudo acceder a la página de gestión"

    html_content = manage_response.data.decode("utf-8")
    assert user2.email in html_content, "User2 no aparece en la página de gestión como curador"

    # 5. Remover user2 como curador vía POST /remove-curator
    remove_curator_response = test_client.post(
        f"/community/{community.slug}/remove-curator", data=dict(user_id=user2.id), follow_redirects=True
    )
    assert remove_curator_response.status_code == 200, "Remover curador falló"

    # 6. Verificar que user2 ya no aparece en lista de curadores desde el endpoint /manage
    manage_after_remove = test_client.get(f"/community/{community.slug}/manage")
    assert manage_after_remove.status_code == 200, "No se pudo acceder a la página de gestión"

    html_after_remove = manage_after_remove.data.decode("utf-8")
    # Verificar que solo aparece user1 como curador
    assert user1.email in html_after_remove, "User1 no aparece como curador"

    # 7. Intentar remover al creador (user1) - debe fallar
    remove_creator_response = test_client.post(
        f"/community/{community.slug}/remove-curator", data=dict(user_id=user1.id), follow_redirects=True
    )
    assert remove_creator_response.status_code == 200, "Request completó correctamente"

    # Verificar que el mensaje de error está en la respuesta
    html_error = remove_creator_response.data.decode("utf-8")
    assert (
        "Cannot remove the community creator" in html_error or "error" in html_error.lower()
    ), "No se mostró mensaje de error al intentar remover creador"

    # Logout
    test_client.get("/logout", follow_redirects=True)

    # Limpieza
    db.session.delete(community)
    db.session.delete(user2)
    db.session.commit()
