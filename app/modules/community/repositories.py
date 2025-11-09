from typing import List, Optional

from app.modules.community.models import Community, CommunityCurator, CommunityDataset, CommunityRequest
from core.repositories.BaseRepository import BaseRepository


# --------------------------------------------------------
# Repository: Community
# --------------------------------------------------------
class CommunityRepository(BaseRepository):
    """Repositorio para operaciones CRUD y consultas básicas sobre comunidades."""

    def __init__(self):
        super().__init__(Community)

    def get_by_slug(self, slug: str) -> Optional[Community]:
        """Obtener una comunidad por su slug."""
        return self.model.query.filter_by(slug=slug).first()

    def get_all(self) -> List[Community]:
        """Obtener todas las comunidades ordenadas por fecha de creación."""
        return self.model.query.order_by(self.model.created_at.desc()).all()

    def search_by_name_or_description(self, query: str) -> List[Community]:
        """Buscar comunidades por nombre o descripción."""
        search_pattern = f"%{query}%"
        return (
            self.model.query.filter(
                (self.model.name.ilike(search_pattern)) | (self.model.description.ilike(search_pattern))
            )
            .order_by(self.model.created_at.desc())
            .all()
        )


# --------------------------------------------------------
# Repository: Community Curator
# --------------------------------------------------------
class CommunityCuratorRepository(BaseRepository):
    """Repositorio para gestionar los curadores de comunidades."""

    def __init__(self):
        super().__init__(CommunityCurator)

    def get_by_community_and_user(self, community_id: int, user_id: int) -> Optional[CommunityCurator]:
        """Obtener la relación curador-comunidad si existe."""
        return self.model.query.filter_by(community_id=community_id, user_id=user_id).first()

    def is_curator(self, community_id: int, user_id: int) -> bool:
        """Verificar si un usuario es curador de una comunidad."""
        return self.get_by_community_and_user(community_id, user_id) is not None


# --------------------------------------------------------
# Repository: Community Dataset
# --------------------------------------------------------
class CommunityDatasetRepository(BaseRepository):
    """Repositorio para gestionar datasets asociados a comunidades."""

    def __init__(self):
        super().__init__(CommunityDataset)

    def get_community_datasets(self, community_id: int) -> List[CommunityDataset]:
        """Obtener todos los datasets pertenecientes a una comunidad."""
        return self.model.query.filter_by(community_id=community_id).order_by(self.model.added_at.desc()).all()

    def get_by_community_and_dataset(self, community_id: int, dataset_id: int) -> Optional[CommunityDataset]:
        """Obtener un dataset específico dentro de una comunidad."""
        return self.model.query.filter_by(community_id=community_id, dataset_id=dataset_id).first()

    def dataset_in_community(self, community_id: int, dataset_id: int) -> bool:
        """Comprobar si un dataset ya pertenece a una comunidad."""
        return self.get_by_community_and_dataset(community_id, dataset_id) is not None


# --------------------------------------------------------
# Repository: Community Request
# --------------------------------------------------------
class CommunityRequestRepository(BaseRepository):
    """Repositorio para manejar solicitudes de datasets en comunidades."""

    def __init__(self):
        super().__init__(CommunityRequest)

    def get_pending_requests(self, community_id: int) -> List[CommunityRequest]:
        """Obtener las solicitudes pendientes de una comunidad."""
        return (
            self.model.query.filter_by(community_id=community_id, status=CommunityRequest.STATUS_PENDING)
            .order_by(self.model.requested_at.desc())
            .all()
        )

    def get_by_community_and_dataset(self, community_id: int, dataset_id: int) -> Optional[CommunityRequest]:
        """Obtener una solicitud específica por comunidad y dataset."""
        return self.model.query.filter_by(community_id=community_id, dataset_id=dataset_id).first()

    def has_pending_request(self, community_id: int, dataset_id: int) -> bool:
        """Comprobar si existe una solicitud pendiente para un dataset en una comunidad."""
        return (
            self.model.query.filter_by(
                community_id=community_id,
                dataset_id=dataset_id,
                status=CommunityRequest.STATUS_PENDING,
            ).first()
            is not None
        )
