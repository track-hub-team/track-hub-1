from typing import List, Optional

from app.modules.community.models import Community, CommunityCurator, CommunityDataset, CommunityRequest
from core.repositories.BaseRepository import BaseRepository


class CommunityRepository(BaseRepository):
    def __init__(self):
        super().__init__(Community)

    def get_by_slug(self, slug: str) -> Optional[Community]:
        """Obtener comunidad por slug"""
        return self.model.query.filter_by(slug=slug).first()

    def get_all_with_datasets_count(self) -> List[Community]:
        """Obtener todas las comunidades ordenadas por fecha de creación"""
        return self.model.query.order_by(self.model.created_at.desc()).all()

    def search_by_name_or_description(self, query: str) -> List[Community]:
        """Buscar comunidades por nombre o descripción"""
        search_pattern = f"%{query}%"
        return (
            self.model.query.filter(
                (self.model.name.ilike(search_pattern)) | (self.model.description.ilike(search_pattern))
            )
            .order_by(self.model.created_at.desc())
            .all()
        )

    def get_user_communities(self, user_id: int) -> List[Community]:
        """Obtener comunidades creadas por un usuario"""
        return self.model.query.filter_by(creator_id=user_id).order_by(self.model.created_at.desc()).all()

    def get_curated_communities(self, user_id: int) -> List[Community]:
        """Obtener comunidades donde el usuario es curador"""
        return (
            self.model.query.join(CommunityCurator)
            .filter(CommunityCurator.user_id == user_id)
            .order_by(self.model.created_at.desc())
            .all()
        )


class CommunityCuratorRepository(BaseRepository):
    def __init__(self):
        super().__init__(CommunityCurator)

    def get_by_community_and_user(self, community_id: int, user_id: int) -> Optional[CommunityCurator]:
        """Verificar si un usuario es curador de una comunidad"""
        return self.model.query.filter_by(community_id=community_id, user_id=user_id).first()

    def is_curator(self, community_id: int, user_id: int) -> bool:
        """Verificar si un usuario es curador de una comunidad"""
        return self.get_by_community_and_user(community_id, user_id) is not None

    def get_community_curators(self, community_id: int) -> List[CommunityCurator]:
        """Obtener todos los curadores de una comunidad"""
        return self.model.query.filter_by(community_id=community_id).all()


class CommunityDatasetRepository(BaseRepository):
    def __init__(self):
        super().__init__(CommunityDataset)

    def get_by_community_and_dataset(self, community_id: int, dataset_id: int) -> Optional[CommunityDataset]:
        """Verificar si un dataset está en una comunidad"""
        return self.model.query.filter_by(community_id=community_id, dataset_id=dataset_id).first()

    def dataset_in_community(self, community_id: int, dataset_id: int) -> bool:
        """Verificar si un dataset está en una comunidad"""
        return self.get_by_community_and_dataset(community_id, dataset_id) is not None

    def get_community_datasets(self, community_id: int) -> List[CommunityDataset]:
        """Obtener todos los datasets de una comunidad"""
        return self.model.query.filter_by(community_id=community_id).order_by(self.model.added_at.desc()).all()

    def get_dataset_communities(self, dataset_id: int) -> List[CommunityDataset]:
        """Obtener todas las comunidades donde está un dataset"""
        return self.model.query.filter_by(dataset_id=dataset_id).all()


class CommunityRequestRepository(BaseRepository):
    def __init__(self):
        super().__init__(CommunityRequest)

    def get_pending_requests(self, community_id: int) -> List[CommunityRequest]:
        """Obtener solicitudes pendientes de una comunidad"""
        return (
            self.model.query.filter_by(community_id=community_id, status=CommunityRequest.STATUS_PENDING)
            .order_by(self.model.requested_at.desc())
            .all()
        )

    def get_by_community_and_dataset(self, community_id: int, dataset_id: int) -> Optional[CommunityRequest]:
        """Obtener solicitud específica por comunidad y dataset"""
        return self.model.query.filter_by(community_id=community_id, dataset_id=dataset_id).first()

    def has_pending_request(self, community_id: int, dataset_id: int) -> bool:
        """Verificar si existe una solicitud pendiente para un dataset en una comunidad"""
        return (
            self.model.query.filter_by(
                community_id=community_id, dataset_id=dataset_id, status=CommunityRequest.STATUS_PENDING
            ).first()
            is not None
        )

    def get_user_requests(self, user_id: int) -> List[CommunityRequest]:
        """Obtener todas las solicitudes de un usuario"""
        return self.model.query.filter_by(requester_id=user_id).order_by(self.model.requested_at.desc()).all()
