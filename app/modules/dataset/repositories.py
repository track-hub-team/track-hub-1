import logging
from datetime import datetime, timezone
from typing import List, Optional

from flask_login import current_user
from sqlalchemy import desc, func

from app.modules.dataset.models import BaseDataset  # 👈 usar el mapper base para consultas polimórficas
from app.modules.dataset.models import Author, Comment, DOIMapping, DSDownloadRecord, DSMetaData, DSViewRecord
from core.repositories.BaseRepository import BaseRepository

logger = logging.getLogger(__name__)


class AuthorRepository(BaseRepository):
    def __init__(self):
        super().__init__(Author)


class DSDownloadRecordRepository(BaseRepository):
    def __init__(self):
        super().__init__(DSDownloadRecord)

    def total_dataset_downloads(self) -> int:
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0


class DSMetaDataRepository(BaseRepository):
    def __init__(self):
        super().__init__(DSMetaData)

    def filter_by_doi(self, doi: str) -> Optional[DSMetaData]:
        return self.model.query.filter_by(dataset_doi=doi).first()


class DSViewRecordRepository(BaseRepository):
    def __init__(self):
        super().__init__(DSViewRecord)

    def total_dataset_views(self) -> int:
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0

    def the_record_exists(self, dataset: BaseDataset, user_cookie: str):
        return self.model.query.filter_by(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset.id,
            view_cookie=user_cookie,
        ).first()

    def create_new_record(self, dataset: BaseDataset, user_cookie: str) -> DSViewRecord:
        return self.create(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset.id,
            view_date=datetime.now(timezone.utc),
            view_cookie=user_cookie,
        )


class DataSetRepository(BaseRepository):
    def __init__(self):
        # 👇 Usar BaseDataset para que el ORM devuelva la subclase correcta (uvl/gpx/base)
        super().__init__(BaseDataset)

    def get_synchronized(self, current_user_id: int):
        return (
            self.model.query.join(DSMetaData)
            .filter(BaseDataset.user_id == current_user_id, DSMetaData.dataset_doi.isnot(None))
            .order_by(self.model.created_at.desc())
            .all()
        )

    def get_unsynchronized(self, current_user_id: int):
        return (
            self.model.query.join(DSMetaData)
            .filter(BaseDataset.user_id == current_user_id, DSMetaData.dataset_doi.is_(None))
            .order_by(self.model.created_at.desc())
            .all()
        )

    def get_unsynchronized_dataset(self, current_user_id: int, dataset_id: int):
        return (
            self.model.query.join(DSMetaData)
            .filter(
                BaseDataset.user_id == current_user_id,
                BaseDataset.id == dataset_id,
                DSMetaData.dataset_doi.is_(None),
            )
            .first()
        )

    def count_synchronized_datasets(self):
        return self.model.query.join(DSMetaData).filter(DSMetaData.dataset_doi.isnot(None)).count()

    def count_unsynchronized_datasets(self):
        return self.model.query.join(DSMetaData).filter(DSMetaData.dataset_doi.is_(None)).count()

    def latest_synchronized(self):
        return (
            self.model.query.join(DSMetaData)
            .filter(DSMetaData.dataset_doi.isnot(None))
            .order_by(desc(self.model.id))
            .limit(5)
            .all()
        )


class DOIMappingRepository(BaseRepository):
    def __init__(self):
        super().__init__(DOIMapping)

    def get_new_doi(self, old_doi: str) -> str:
        return self.model.query.filter_by(dataset_doi_old=old_doi).first()


class CommentRepository(BaseRepository):
    """
    Repositorio para operaciones CRUD de comentarios.
    Lógica básica sin moderación ni respuestas anidadas.
    """

    def __init__(self):
        super().__init__(Comment)

    def get_by_dataset(self, dataset_id: int, order_by: str = "created_at") -> List[Comment]:
        """
        Obtener todos los comentarios de un dataset.

        Args:
            dataset_id: ID del dataset
            order_by: Campo para ordenar (default: created_at ascendente)

        Returns:
            List[Comment]: Lista de comentarios ordenados
        """
        query = self.model.query.filter_by(dataset_id=dataset_id)

        if order_by == "created_at":
            query = query.order_by(self.model.created_at.asc())
        elif order_by == "created_at_desc":
            query = query.order_by(self.model.created_at.desc())

        return query.all()

    def get_by_user(self, user_id: int) -> List[Comment]:
        """
        Obtener todos los comentarios de un usuario.

        Args:
            user_id: ID del usuario

        Returns:
            List[Comment]: Lista de comentarios del usuario
        """
        return self.model.query.filter_by(user_id=user_id).order_by(self.model.created_at.desc()).all()

    def count_by_dataset(self, dataset_id: int) -> int:
        """
        Contar comentarios de un dataset.

        Args:
            dataset_id: ID del dataset

        Returns:
            int: Número de comentarios
        """
        return self.model.query.filter_by(dataset_id=dataset_id).count()

    def update_content(self, comment_id: int, new_content: str) -> Optional[Comment]:
        """
        Actualizar el contenido de un comentario.

        Args:
            comment_id: ID del comentario
            new_content: Nuevo contenido

        Returns:
            Optional[Comment]: Comentario actualizado o None si no existe
        """
        comment = self.get_by_id(comment_id)
        if comment:
            comment.content = new_content
            self.session.commit()
            return comment
        return None

    def delete_by_dataset(self, dataset_id: int) -> int:
        """
        Eliminar todos los comentarios de un dataset.
        Útil cuando se elimina un dataset.

        Args:
            dataset_id: ID del dataset

        Returns:
            int: Número de comentarios eliminados
        """
        count = self.model.query.filter_by(dataset_id=dataset_id).count()
        self.model.query.filter_by(dataset_id=dataset_id).delete()
        self.session.commit()
        return count

    def get_latest_comments(self, limit: int = 5) -> List[Comment]:
        """
        Obtener los comentarios más recientes globalmente.

        Args:
            limit: Número máximo de comentarios a devolver

        Returns:
            List[Comment]: Lista de comentarios recientes
        """
        return self.model.query.order_by(desc(self.model.created_at)).limit(limit).all()

    def total_comments(self) -> int:
        """
        Contar el total de comentarios en la plataforma.

        Returns:
            int: Número total de comentarios
        """
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0
