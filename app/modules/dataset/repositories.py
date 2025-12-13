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

    def filter_by_conceptrecid(self, conceptrecid: str) -> Optional[DSMetaData]:
        return self.model.query.filter_by(conceptrecid=conceptrecid).first()


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
    """

    def __init__(self):
        super().__init__(Comment)

    def get_by_dataset(self, dataset_id: int, order_by: str = "created_at") -> List[Comment]:
        """
        Obtener todos los comentarios de un dataset.
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
        """
        return self.model.query.filter_by(user_id=user_id).order_by(self.model.created_at.desc()).all()

    def count_by_dataset(self, dataset_id: int) -> int:
        """
        Contar comentarios de un dataset.
        """
        return self.model.query.filter_by(dataset_id=dataset_id).count()

    def update_content(self, comment_id: int, new_content: str) -> Optional[Comment]:
        """
        Actualizar el contenido de un comentario.
        """
        comment = self.get_by_id(comment_id)
        if comment:
            comment.content = new_content
            self.session.commit()
            return comment
        return None

    # 🔧 NUEVO MÉTODO: Eliminar comentario con todas sus respuestas
    def delete_with_replies(self, comment_id: int) -> int:
        """
        Eliminar un comentario y todas sus respuestas recursivamente.

        Args:
            comment_id: ID del comentario a eliminar

        Returns:
            int: Número total de comentarios eliminados (padre + hijos)
        """
        comment = self.get_by_id(comment_id)
        if not comment:
            return 0

        # Contar respuestas antes de eliminar
        replies_count = self._count_all_replies(comment)

        # SQLAlchemy manejará la cascada automáticamente gracias a cascade="all, delete-orphan"
        self.session.delete(comment)
        self.session.commit()

        # Retornar total eliminado (1 padre + N respuestas)
        return 1 + replies_count

    def _count_all_replies(self, comment: Comment) -> int:
        """
        Contar recursivamente todas las respuestas de un comentario.
        """
        count = 0
        for reply in comment.replies:
            count += 1
            count += self._count_all_replies(reply)
        return count

    def delete_by_dataset(self, dataset_id: int) -> int:
        """
        Eliminar todos los comentarios de un dataset.
        """
        count = self.model.query.filter_by(dataset_id=dataset_id).count()
        self.model.query.filter_by(dataset_id=dataset_id).delete()
        self.session.commit()
        return count

    def get_latest_comments(self, limit: int = 5) -> List[Comment]:
        """
        Obtener los comentarios más recientes globalmente.
        """
        return self.model.query.order_by(desc(self.model.created_at)).limit(limit).all()

    def total_comments(self) -> int:
        """
        Contar el total de comentarios en la plataforma.
        """
        max_id = self.model.query.with_entities(func.max(self.model.id)).scalar()
        return max_id if max_id is not None else 0
