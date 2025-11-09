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
    """Service layer for managing community-related operations."""

    def __init__(self):
        self.repository = CommunityRepository()
        self.curator_repository = CommunityCuratorRepository()
        self.dataset_repository = CommunityDatasetRepository()

    # --------------------------------------------------------
    # Core retrieval methods
    # --------------------------------------------------------
    def get_all(self, query: Optional[str] = None) -> List[Community]:
        """Return all communities, optionally filtered by a search query."""
        if query:
            return self.repository.search_by_name_or_description(query)
        return self.repository.get_all_with_datasets_count()

    def get_community_datasets(self, community_id: int):
        """Retrieve all datasets associated with a specific community."""
        return [cd.dataset for cd in self.dataset_repository.get_community_datasets(community_id)]

    def is_curator(self, community_id: int, user_id: int) -> bool:
        """Check whether a user is a curator of a given community."""
        return self.curator_repository.is_curator(community_id, user_id)

    # --------------------------------------------------------
    # Community creation
    # --------------------------------------------------------
    def create_community(
        self,
        name: str,
        description: str,
        creator_id: int,
        logo_file: Optional[FileStorage] = None,
    ) -> Tuple[Optional[Community], Optional[str]]:
        """
        Create a new community with a unique slug and optional logo upload.
        Returns a tuple (community, error_message).
        """
        base_slug = slugify(name)
        slug = base_slug
        counter = 1

        # Ensure slug uniqueness
        while self.repository.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Save logo if provided
        logo_path = self._save_logo(logo_file, slug) if logo_file else None

        try:
            community = self.repository.create(
                name=name,
                slug=slug,
                description=description,
                logo_path=logo_path,
                creator_id=creator_id,
            )
            # Automatically assign the creator as curator
            self.curator_repository.create(community_id=community.id, user_id=creator_id)
            db.session.commit()
            return community, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    # --------------------------------------------------------
    # File handling
    # --------------------------------------------------------
    def _save_logo(self, logo_file: FileStorage, slug: str) -> str:
        """
        Save a community logo file and return its relative path.
        """
        base_dir = os.getenv("WORKING_DIR", "")
        upload_dir = os.path.join(base_dir, "uploads", "communities")
        os.makedirs(upload_dir, exist_ok=True)

        filename = secure_filename(logo_file.filename)
        _, ext = os.path.splitext(filename)
        unique_filename = f"{slug}{ext}"

        file_path = os.path.join(upload_dir, unique_filename)
        logo_file.save(file_path)

        # Return relative path for database storage
        return os.path.join("uploads", "communities", unique_filename)
