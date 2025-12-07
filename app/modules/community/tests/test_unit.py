import pytest

from app import db
from app.modules.auth.models import User
from app.modules.community.models import CommunityDataset, CommunityRequest
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


def test_sample_assertion(test_client):
    """
    Sample test to verify that the test framework and environment are working correctly.
    It does not communicate with the Flask application; it only performs a simple assertion to
    confirm that the tests in this module can be executed.
    """
    greeting = "Hello, World!"
    assert greeting == "Hello, World!", "The greeting does not coincide with 'Hello, World!'"


def test_create_community_creator_becomes_curator(test_client):
    """
    Prueba que verifica que al crear una comunidad, el creador es automáticamente
    añadido como curador de la misma.
    """

    # Obtener usuario de prueba
    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None, "Test user not found"

    community_service = CommunityService()

    # Crear comunidad
    community, error = community_service.create_community(
        name="Test Community Curator",
        description="Comunidad de prueba para verificar que el creador es curador",
        creator_id=user.id,
    )

    # Verificar que la comunidad se creó correctamente
    assert error is None, f"Error creating community: {error}"
    assert community is not None, "Community was not created"
    assert community.creator_id == user.id, "Creator does not match the user"

    # Verificar que el creador es curador
    is_curator = community_service.is_curator(community.id, user.id)
    assert is_curator is True, "Creator was not automatically added as curator"

    # Verificar que existe exactamente 1 curador (el creador)
    curators = community.get_curators_list()
    assert len(curators) == 1, f"Expected 1 curator, found {len(curators)}"
    assert curators[0].id == user.id, "The only curator is not the creator"

    # Limpieza
    db.session.delete(community)
    db.session.commit()


def test_get_eligible_datasets_excludes_already_added(test_client):
    """
    Prueba que verifica que se excluyen
    correctamente los datasets que ya están en la comunidad o tienen una solicitud pendiente.
    Solo deben aparecer como elegibles los datasets que el usuario posee y que no están
    en ninguna de esas dos situaciones.
    """

    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None, "Test user not found"

    community_service = CommunityService()

    # Crear una comunidad
    community, error = community_service.create_community(
        name="Test Community Datasets", description="Comunidad para probar filtrado de datasets", creator_id=user.id
    )
    assert error is None and community is not None, "Error creating test community"

    # Crear 3 datasets del usuario
    metadata1 = DSMetaData(
        title="Dataset 1 - Ya en comunidad",
        description="Dataset que ya está añadido",
        publication_type=PublicationType.NONE,
    )
    db.session.add(metadata1)
    db.session.flush()

    dataset1 = GPXDataset(user_id=user.id, ds_meta_data_id=metadata1.id)
    db.session.add(dataset1)

    metadata2 = DSMetaData(
        title="Dataset 2 - Con solicitud pendiente",
        description="Dataset con solicitud pendiente",
        publication_type=PublicationType.NONE,
    )
    db.session.add(metadata2)
    db.session.flush()

    dataset2 = GPXDataset(user_id=user.id, ds_meta_data_id=metadata2.id)
    db.session.add(dataset2)

    metadata3 = DSMetaData(
        title="Dataset 3 - Elegible",
        description="Dataset disponible para proponer",
        publication_type=PublicationType.NONE,
    )
    db.session.add(metadata3)
    db.session.flush()

    dataset3 = GPXDataset(user_id=user.id, ds_meta_data_id=metadata3.id)
    db.session.add(dataset3)
    db.session.flush()

    # Añadir dataset1 directamente a la comunidad (ya está en la comunidad)
    community_dataset = CommunityDataset(community_id=community.id, dataset_id=dataset1.id, added_by_id=user.id)
    db.session.add(community_dataset)

    # Crear solicitud pendiente para dataset2
    pending_request = CommunityRequest(
        community_id=community.id,
        dataset_id=dataset2.id,
        requester_id=user.id,
        status=CommunityRequest.STATUS_PENDING,
        message="Solicitud de prueba",
    )
    db.session.add(pending_request)
    db.session.commit()

    # Obtener datasets elegibles
    eligible_datasets = community_service.get_eligible_datasets_for_community(user.id, community.id)

    # Verificaciones
    assert len(eligible_datasets) == 1, f"Expected 1 eligible dataset, found {len(eligible_datasets)}"
    assert eligible_datasets[0].id == dataset3.id, "The eligible dataset is not the correct one"

    # Verificar que los otros dos no están en la lista
    eligible_ids = [d.id for d in eligible_datasets]
    assert dataset1.id not in eligible_ids, "Dataset1 (already in community) should not be eligible"
    assert dataset2.id not in eligible_ids, "Dataset2 (with pending request) should not be eligible"

    # Limpieza
    db.session.delete(pending_request)
    db.session.delete(community_dataset)
    db.session.delete(community)
    db.session.delete(dataset1)
    db.session.delete(dataset2)
    db.session.delete(dataset3)
    db.session.delete(metadata1)
    db.session.delete(metadata2)
    db.session.delete(metadata3)
    db.session.commit()


def test_approve_request_adds_dataset_to_community(test_client):
    """
    Prueba que verifica que al aprobar una solicitud pendiente, el dataset se añade
    correctamente a la comunidad y la solicitud cambia su estado a 'approved'.
    """

    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None, "Test user not found"

    community_service = CommunityService()

    # Crear una comunidad (el usuario será curador automáticamente)
    community, error = community_service.create_community(
        name="Test Community Approval",
        description="Comunidad para probar aprobación de solicitudes",
        creator_id=user.id,
    )
    assert error is None and community is not None, "Error creating community"

    # Crear un dataset
    metadata = DSMetaData(
        title="Dataset para aprobar", description="Dataset que será aprobado", publication_type=PublicationType.NONE
    )
    db.session.add(metadata)
    db.session.flush()

    dataset = GPXDataset(user_id=user.id, ds_meta_data_id=metadata.id)
    db.session.add(dataset)
    db.session.flush()

    # Crear solicitud pendiente
    success, error = community_service.propose_dataset(
        community_id=community.id, dataset_id=dataset.id, requester_id=user.id, message="Por favor, aprueben mi dataset"
    )
    assert success is True and error is None, "Error creating request"

    # Obtener la solicitud creada
    pending_requests = community_service.get_pending_requests(community.id)
    assert len(pending_requests) == 1, "There should be exactly 1 pending request"
    request = pending_requests[0]

    # Aprobar la solicitud (el usuario es curador)
    success, error = community_service.approve_request(
        request_id=request.id, curator_id=user.id, comment="Dataset aprobado para la comunidad"
    )

    # Verificaciones
    assert success is True, f"Error approving request: {error}"
    assert error is None, f"Expected None, got error: {error}"

    # Verificar que la solicitud cambió de estado
    db.session.refresh(request)
    assert request.status == CommunityRequest.STATUS_APPROVED, "Request status did not change to 'approved'"
    assert request.reviewed_by_id == user.id, "Reviewer is not the correct curator"
    assert request.review_comment == "Dataset aprobado para la comunidad", "Comment does not match"

    # Verificar que el dataset está ahora en la comunidad
    community_datasets = community_service.get_community_datasets(community.id)
    assert len(community_datasets) == 1, "Dataset was not added to the community"
    assert community_datasets[0].id == dataset.id, "The added dataset is not the correct one"

    # Verificar que ya no hay solicitudes pendientes
    pending_after = community_service.get_pending_requests(community.id)
    assert len(pending_after) == 0, "There should be no pending requests after approval"

    # Limpieza
    db.session.delete(community)
    db.session.delete(dataset)
    db.session.delete(metadata)
    db.session.commit()


def test_reject_request_does_not_add_dataset(test_client):
    """
    Prueba que verifica que al rechazar una solicitud pendiente, el dataset NO se añade
    a la comunidad y la solicitud cambia su estado a 'rejected'.
    """

    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None, "Test user not found"

    community_service = CommunityService()

    # Crear una comunidad (el usuario será curador automáticamente)
    community, error = community_service.create_community(
        name="Test Community Rejection", description="Comunidad para probar rechazo de solicitudes", creator_id=user.id
    )
    assert error is None and community is not None, "Error creating community"

    # Crear un dataset
    metadata = DSMetaData(
        title="Dataset para rechazar", description="Dataset que será rechazado", publication_type=PublicationType.NONE
    )
    db.session.add(metadata)
    db.session.flush()

    dataset = GPXDataset(user_id=user.id, ds_meta_data_id=metadata.id)
    db.session.add(dataset)
    db.session.flush()

    # Crear solicitud pendiente
    success, error = community_service.propose_dataset(
        community_id=community.id,
        dataset_id=dataset.id,
        requester_id=user.id,
        message="Por favor, consideren mi dataset",
    )
    assert success is True and error is None, "Error creating request"

    # Obtener la solicitud creada
    pending_requests = community_service.get_pending_requests(community.id)
    assert len(pending_requests) == 1, "There should be exactly 1 pending request"
    request = pending_requests[0]

    # Rechazar la solicitud (el usuario es curador)
    success, error = community_service.reject_request(
        request_id=request.id, curator_id=user.id, comment="Dataset no cumple con los requisitos de la comunidad"
    )

    # Verificaciones
    assert success is True, f"Error rejecting request: {error}"
    assert error is None, f"Expected None, got error: {error}"

    # Verificar que la solicitud cambió de estado
    db.session.refresh(request)
    assert request.status == CommunityRequest.STATUS_REJECTED, "Request status did not change to 'rejected'"
    assert request.reviewed_by_id == user.id, "Reviewer is not the correct curator"
    assert request.review_comment == "Dataset no cumple con los requisitos de la comunidad", "Comment does not match"

    # Verificar que el dataset NO está en la comunidad
    community_datasets = community_service.get_community_datasets(community.id)
    assert len(community_datasets) == 0, "Dataset should not be in the community after rejection"

    # Verificar que ya no hay solicitudes pendientes
    pending_after = community_service.get_pending_requests(community.id)
    assert len(pending_after) == 0, "There should be no pending requests after rejection"

    # Limpieza
    db.session.delete(community)
    db.session.delete(dataset)
    db.session.delete(metadata)
    db.session.commit()


def test_cannot_remove_community_creator_as_curator(test_client):
    """
    Prueba que verifica que el creador de una comunidad no puede ser eliminado como curador.
    """

    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None, "Test user not found"

    community_service = CommunityService()

    # Crear una comunidad
    community, error = community_service.create_community(
        name="Test Community Creator Protection",
        description="Comunidad para probar que el creador no puede ser removido",
        creator_id=user.id,
    )
    assert error is None and community is not None, "Error creating community"

    # Verificar que el usuario es curador
    is_curator = community_service.is_curator(community.id, user.id)
    assert is_curator is True, "Creator should be a curator"

    # Intentar eliminar al creador como curador
    success, error = community_service.remove_curator(
        community_id=community.id, user_id=user.id, requester_id=user.id  # El mismo usuario intenta eliminarse
    )

    # Verificaciones
    assert success is False, "Should not be possible to remove creator as curator"
    assert error is not None, "Should return an error message"
    assert "Cannot remove the community creator as curator" in error, f"Unexpected error, got: {error}"

    # Verificar que el usuario sigue siendo curador
    is_still_curator = community_service.is_curator(community.id, user.id)
    assert is_still_curator is True, "Creator should still be a curator after the attempt"

    # Verificar que sigue habiendo exactamente 1 curador
    curators = community.get_curators_list()
    assert len(curators) == 1, f"There should be exactly 1 curator, found {len(curators)}"

    # Limpieza
    db.session.delete(community)
    db.session.commit()


def test_cannot_create_community_with_duplicate_name(test_client):
    """
    Prueba que verifica que no se puede crear una comunidad con un nombre que ya existe.
    """

    user = User.query.filter_by(email="test@example.com").first()
    assert user is not None, "Test user not found"

    community_service = CommunityService()

    # Crear la primera comunidad
    community1, error1 = community_service.create_community(
        name="Unique Community Name",
        description="Primera comunidad con este nombre",
        creator_id=user.id,
    )
    assert error1 is None, f"Error creating first community: {error1}"
    assert community1 is not None, "First community was not created"

    # Intentar crear una segunda comunidad con el mismo nombre
    community2, error2 = community_service.create_community(
        name="Unique Community Name",
        description="Intento de crear una comunidad con nombre duplicado",
        creator_id=user.id,
    )

    # Verificaciones
    assert community2 is None, "Should not have created a second community with the same name"
    assert error2 is not None, "Should return an error message"
    assert "already exists" in error2, f"Unexpected error message, got: {error2}"
    assert "Unique Community Name" in error2, "Error message should include the community name"

    # Limpieza
    db.session.delete(community1)
    db.session.commit()
