import logging
import os
from typing import List, Optional, Tuple

from slugify import slugify  # type: ignore
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import db
from app.modules.auth.models import User
from app.modules.community.models import Community, CommunityRequest
from app.modules.community.repositories import (
    CommunityCuratorRepository,
    CommunityDatasetRepository,
    CommunityRepository,
    CommunityRequestRepository,
)
from app.modules.dataset.models import BaseDataset
from app.modules.mail.services import MailService
from app.modules.profile.models import UserProfile
from core.services.BaseService import BaseService

logger = logging.getLogger(__name__)

# Configuración de logos
ALLOWED_LOGO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_LOGO_SIZE_MB = 2
MAX_LOGO_SIZE_BYTES = MAX_LOGO_SIZE_MB * 1024 * 1024


class CommunityService(BaseService):
    def __init__(self):
        super().__init__(CommunityRepository())
        self.curator_repository = CommunityCuratorRepository()
        self.dataset_repository = CommunityDatasetRepository()
        self.request_repository = CommunityRequestRepository()

    def get_all(self, query: Optional[str] = None) -> List[Community]:
        """Obtener todas las comunidades, opcionalmente filtradas por búsqueda"""
        if query:
            return self.repository.search_by_name_or_description(query)
        return self.repository.get_all_ordered()

    def get_by_slug(self, slug: str) -> Optional[Community]:
        """Obtener comunidad por slug"""
        return self.repository.get_by_slug(slug)

    def create_community(
        self, name: str, description: str, creator_id: int, logo_file: Optional[FileStorage] = None
    ) -> Tuple[Optional[Community], Optional[str]]:
        """
        Crear una nueva comunidad.
        """
        # Generar slug (único)
        base_slug = slugify(name)
        slug = base_slug
        counter = 1

        while self.repository.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Procesar logo si existe
        logo_path = None
        if logo_file and logo_file.filename:
            try:
                logo_path = self._save_logo(logo_file, slug)
            except Exception as e:
                return None, f"Error saving logo: {str(e)}"

        # Crear comunidad
        try:
            community = self.repository.create(
                name=name, slug=slug, description=description, logo_path=logo_path, creator_id=creator_id
            )

            # El creador es automáticamente curador
            self.curator_repository.create(community_id=community.id, user_id=creator_id)

            db.session.commit()
            return community, None

        except Exception as e:
            db.session.rollback()
            return None, f"Error creating community: {str(e)}"

    def update_community(
        self,
        community_id: int,
        description: Optional[str] = None,
        logo_file: Optional[FileStorage] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Actualizar información de una comunidad existente.
        El nombre no se puede cambiar para mantener la integridad del slug
        """
        community = self.repository.get_by_id(community_id)
        if not community:
            return False, "Community not found"

        try:
            # Actualizar descripción si se proporciona
            if description is not None:
                community.description = description

            # Actualizar logo si se proporciona
            if logo_file and logo_file.filename:
                # Eliminar logo anterior si existe
                if community.logo_path:
                    try:
                        working_dir = os.getenv("WORKING_DIR", "")
                        if not working_dir:
                            working_dir = os.path.dirname(
                                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            )
                        old_logo_path = os.path.join(working_dir, community.logo_path)
                        if os.path.exists(old_logo_path):
                            os.remove(old_logo_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete old logo: {e}")

                # Guardar nuevo logo
                logo_path = self._save_logo(logo_file, community.slug)
                community.logo_path = logo_path

            db.session.commit()
            return True, None

        except Exception as e:
            db.session.rollback()
            return False, f"Error updating community: {str(e)}"

    def add_curator(self, community_id: int, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Añadir un curador a una comunidad.
        """
        # Verificar que la comunidad existe
        community = self.repository.get_by_id(community_id)
        if not community:
            return False, "Community not found"

        # Verificar que no es ya curador
        if self.curator_repository.is_curator(community_id, user_id):
            return False, "User is already a curator of this community"

        try:
            self.curator_repository.create(community_id=community_id, user_id=user_id)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, f"Error adding curator: {str(e)}"

    def remove_curator(self, community_id: int, user_id: int, requester_id: int) -> Tuple[bool, Optional[str]]:
        """
        Remover un curador de una comunidad.
        No se puede eliminar al creador de la comunidad.
        """
        community = self.repository.get_by_id(community_id)
        if not community:
            return False, "Community not found"

        # No se puede eliminar al creador
        if community.creator_id == user_id:
            return False, "Cannot remove the community creator as curator"

        # Solo curadores pueden eliminar otros curadores
        if not self.curator_repository.is_curator(community_id, requester_id):
            return False, "Only curators can remove other curators"

        curator = self.curator_repository.get_by_community_and_user(community_id, user_id)
        if not curator:
            return False, "User is not a curator of this community"

        try:
            db.session.delete(curator)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, f"Error removing curator: {str(e)}"

    def get_community_datasets(self, community_id: int) -> List[BaseDataset]:
        """Obtener todos los datasets de una comunidad"""
        community_datasets = self.dataset_repository.get_community_datasets(community_id)
        return [cd.dataset for cd in community_datasets if cd.dataset]

    def propose_dataset(
        self, community_id: int, dataset_id: int, requester_id: int, message: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Proponer un dataset para ser añadido a una comunidad.
        """
        # Verificar que la comunidad existe
        community = self.repository.get_by_id(community_id)
        if not community:
            return False, "Community not found"

        # Verificar que el dataset no está ya en la comunidad
        if self.dataset_repository.dataset_in_community(community_id, dataset_id):
            return False, "Dataset is already in this community"

        # Verificar que no existe una solicitud pendiente
        if self.request_repository.has_pending_request(community_id, dataset_id):
            return False, "There is already a pending request for this dataset"

        try:
            self.request_repository.create(
                community_id=community_id,
                dataset_id=dataset_id,
                requester_id=requester_id,
                message=message,
                status=CommunityRequest.STATUS_PENDING,
            )
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, f"Error creating request: {str(e)}"

    def get_pending_requests(self, community_id: int) -> List[CommunityRequest]:
        """Obtener solicitudes pendientes de una comunidad"""
        return self.request_repository.get_pending_requests(community_id)

    def get_request_by_id(self, request_id: int) -> Optional[CommunityRequest]:
        """Obtener una solicitud por su ID"""
        return self.request_repository.get_by_id(request_id)

    def approve_request(
        self, request_id: int, curator_id: int, comment: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Aprobar una solicitud y añadir el dataset a la comunidad.
        """
        request = self.request_repository.get_by_id(request_id)
        if not request:
            return False, "Request not found"

        if not request.is_pending():
            return False, "Request is not pending"

        # Verificar que el usuario es curador
        if not self.curator_repository.is_curator(request.community_id, curator_id):
            return False, "Only curators can approve requests"

        # Verificar que el dataset no está ya en la comunidad
        if self.dataset_repository.dataset_in_community(request.community_id, request.dataset_id):
            return False, "Dataset is already in the community"

        try:
            # Aprobar la solicitud
            request.approve(curator_id, comment)

            # Añadir el dataset a la comunidad
            self.dataset_repository.create(
                community_id=request.community_id, dataset_id=request.dataset_id, added_by_id=curator_id
            )

            db.session.commit()

            # Enviar notificación por correo
            try:
                requester = request.requester
                dataset = request.dataset
                community = request.community

                requester_name = requester.profile.name if requester.profile and requester.profile.name else "User"

                # Determinar el nombre del dataset
                dataset_name = f"Dataset #{dataset.id}"
                if hasattr(dataset, "ds_meta_data") and dataset.ds_meta_data:
                    if hasattr(dataset.ds_meta_data, "title") and dataset.ds_meta_data.title:
                        dataset_name = dataset.ds_meta_data.title

                # Enviar correo
                success, error = MailService.send_dataset_approved_notification(
                    requester_email=requester.email,
                    requester_name=requester_name,
                    dataset_name=dataset_name,
                    community_name=community.name,
                )

                if not success:
                    # Log del error pero no falla la aprobación
                    logger.warning(f"Failed to send approval email to {requester.email}: {error}")

            except Exception as e:
                # Si falla el envío de correo, solo loguear pero no revertir la aprobación
                logger.error(f"Exception sending approval email: {str(e)}")

            return True, None
        except Exception as e:
            db.session.rollback()
            return False, f"Error approving request: {str(e)}"

    def reject_request(
        self, request_id: int, curator_id: int, comment: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Rechazar una solicitud.
        """
        request = self.request_repository.get_by_id(request_id)
        if not request:
            return False, "Request not found"

        if not request.is_pending():
            return False, "Request is not pending"

        # Verificar que el usuario es curador
        if not self.curator_repository.is_curator(request.community_id, curator_id):
            return False, "Only curators can reject requests"

        try:
            request.reject(curator_id, comment)
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, f"Error rejecting request: {str(e)}"

    def is_curator(self, community_id: int, user_id: int) -> bool:
        """Verificar si un usuario es curador de una comunidad"""
        return self.curator_repository.is_curator(community_id, user_id)

    def get_user_communities(self, user_id: int) -> List[Community]:
        """Obtener comunidades creadas por un usuario"""
        return self.repository.get_user_communities(user_id)

    def get_curated_communities(self, user_id: int) -> List[Community]:
        """Obtener comunidades donde el usuario es curador"""
        return self.repository.get_curated_communities(user_id)

    def get_user_datasets(self, user_id: int) -> List[BaseDataset]:
        """Obtener todos los datasets de un usuario"""
        return BaseDataset.query.filter_by(user_id=user_id).all()

    def get_eligible_datasets_for_community(self, user_id: int, community_id: int) -> List[BaseDataset]:
        """
        Obtener datasets del usuario que pueden ser propuestos a una comunidad.
        Excluye datasets que ya están en la comunidad o tienen solicitud pendiente.
        """
        # Obtener todos los datasets del usuario
        user_datasets = self.get_user_datasets(user_id)

        # Obtener IDs de datasets ya en la comunidad
        datasets_in_community = self.dataset_repository.get_community_datasets(community_id)
        dataset_ids_in_community = {cd.dataset_id for cd in datasets_in_community}

        # Obtener IDs de datasets con solicitud pendiente
        pending_requests = self.request_repository.get_pending_requests(community_id)
        dataset_ids_with_pending_request = {req.dataset_id for req in pending_requests}

        # Filtrar datasets elegibles
        eligible_datasets = [
            dataset
            for dataset in user_datasets
            if dataset.id not in dataset_ids_in_community and dataset.id not in dataset_ids_with_pending_request
        ]

        return eligible_datasets

    def search_users(self, query: str, limit: int = 10, exclude_user_ids: Optional[List[int]] = None) -> List[dict]:
        """
        Buscar usuarios por email, nombre o apellido.
        """
        if not query or len(query) < 2:
            return []

        # Construir query
        query_builder = (
            db.session.query(User)
            .join(UserProfile, User.id == UserProfile.user_id, isouter=True)
            .filter(
                db.or_(
                    User.email.ilike(f"%{query}%"),
                    UserProfile.name.ilike(f"%{query}%"),
                    UserProfile.surname.ilike(f"%{query}%"),
                )
            )
        )

        # Excluir usuarios específicos si se proporciona la lista
        if exclude_user_ids:
            query_builder = query_builder.filter(User.id.notin_(exclude_user_ids))

        users = query_builder.limit(limit).all()

        # Formatear resultados
        results = []
        for user in users:
            results.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "name": user.profile.name if user.profile and user.profile.name else "",
                    "surname": user.profile.surname if user.profile and user.profile.surname else "",
                }
            )

        return results

    def get_curator_info(self, user_id: int) -> Optional[dict]:
        """
        Obtener información de un usuario para mostrar como curador.
        """
        user = User.query.get(user_id)
        if not user:
            return None

        return {
            "id": user.id,
            "email": user.email,
            "name": user.profile.name if user.profile and user.profile.name else "",
            "surname": user.profile.surname if user.profile and user.profile.surname else "",
        }

    def get_curator_user_ids(self, community_id: int) -> List[int]:
        """
        Obtener lista de IDs de usuarios que son curadores de una comunidad.
        """
        curators = self.curator_repository.get_community_curators(community_id)
        return [curator.user_id for curator in curators]

    def _validate_logo(self, logo_file: FileStorage) -> Optional[str]:
        """
        Validar el archivo de logo.
        """
        if not logo_file or not logo_file.filename:
            return None

        # Validar extensión
        filename = secure_filename(logo_file.filename)
        _, ext = os.path.splitext(filename)
        if ext.lower() not in ALLOWED_LOGO_EXTENSIONS:
            allowed = ", ".join(ALLOWED_LOGO_EXTENSIONS)
            return f"Invalid file type. Allowed: {allowed}"

        # Validar tamaño
        logo_file.seek(0, os.SEEK_END)
        size = logo_file.tell()
        logo_file.seek(0)

        if size > MAX_LOGO_SIZE_BYTES:
            return f"File too large. Maximum size: {MAX_LOGO_SIZE_MB}MB"

        return None

    def _save_logo(self, logo_file: FileStorage, slug: str) -> str:
        """
        Guardar el logo de la comunidad.
        """
        # Validar archivo
        validation_error = self._validate_logo(logo_file)
        if validation_error:
            raise ValueError(validation_error)

        # Crear directorio si no existe
        working_dir = os.getenv("WORKING_DIR", "")
        if not working_dir:
            working_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        upload_dir = os.path.join(working_dir, "uploads", "communities")
        os.makedirs(upload_dir, exist_ok=True)

        # Generar nombre de archivo único
        filename = secure_filename(logo_file.filename)
        _, ext = os.path.splitext(filename)
        unique_filename = f"{slug}{ext.lower()}"

        # Guardar archivo
        file_path = os.path.join(upload_dir, unique_filename)
        logo_file.save(file_path)

        # Retornar ruta relativa
        return f"/uploads/communities/{unique_filename}"
