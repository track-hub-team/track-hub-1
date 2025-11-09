import os
from typing import List, Optional, Tuple

from slugify import slugify  # type: ignore
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import db
from app.modules.community.models import Community
from app.modules.community.repositories import (
    CommunityCuratorRepository,
    CommunityDatasetRepository,
    CommunityRepository,
)


class CommunityService:
    def __init__(self):
        self.repository = CommunityRepository()
        self.curator_repository = CommunityCuratorRepository()
        self.dataset_repository = CommunityDatasetRepository()

    def get_all(self, query: Optional[str] = None) -> List[Community]:
        if query:
            return self.repository.search_by_name_or_description(query)
        return self.repository.get_all_with_datasets_count()

    def create_community(
        self, name: str, description: str, creator_id: int, logo_file: Optional[FileStorage] = None
    ) -> Tuple[Optional[Community], Optional[str]]:
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while self.repository.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        logo_path = self._save_logo(logo_file, slug) if logo_file else None

        try:
            community = self.repository.create(
                name=name, slug=slug, description=description, logo_path=logo_path, creator_id=creator_id
            )
            self.curator_repository.create(community_id=community.id, user_id=creator_id)
            db.session.commit()
            return community, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    def get_community_datasets(self, community_id: int):
        return [cd.dataset for cd in self.dataset_repository.get_community_datasets(community_id)]

    def is_curator(self, community_id: int, user_id: int) -> bool:
        return self.curator_repository.is_curator(community_id, user_id)

    def _save_logo(self, logo_file: FileStorage, slug: str) -> str:
        upload_dir = os.path.join(os.getenv("WORKING_DIR", ""), "uploads", "communities")
        os.makedirs(upload_dir, exist_ok=True)
        filename = secure_filename(logo_file.filename)
        _, ext = os.path.splitext(filename)
        unique_filename = f"{slug}{ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        logo_file.save(file_path)
        # Retornamos la ruta relativa correcta
        return os.path.join("uploads", "communities", unique_filename)
