from datetime import datetime

from app import db


class Community(db.Model):
    """Representa una comunidad que agrupa datasets relacionados por temática."""

    __tablename__ = "community"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    slug = db.Column(db.String(120), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=False)
    logo_path = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Relaciones
    creator = db.relationship("User", foreign_keys=[creator_id], backref="created_communities")
    curators = db.relationship("CommunityCurator", back_populates="community", cascade="all, delete-orphan")
    datasets = db.relationship("CommunityDataset", back_populates="community", cascade="all, delete-orphan")
    requests = db.relationship("CommunityRequest", back_populates="community", cascade="all, delete-orphan")

    # -----------------------------
    # Métodos utilitarios
    # -----------------------------
    @staticmethod
    def _serialize_user(user):
        """Serializa un usuario incluyendo su perfil si existe."""
        if not user:
            return None
        profile = getattr(user, "profile", None)
        return {
            "id": user.id,
            "email": user.email,
            "name": getattr(profile, "name", None),
            "surname": getattr(profile, "surname", None),
        }

    def get_datasets_count(self):
        """Devuelve el número de datasets asociados a la comunidad."""
        return len(self.datasets)

    def get_curators_list(self):
        """Devuelve una lista de usuarios curadores."""
        return [curator.user for curator in self.curators]

    def is_curator(self, user_id: int) -> bool:
        """Verifica si un usuario es curador de la comunidad."""
        return any(curator.user_id == user_id for curator in self.curators)

    def to_dict(self):
        """Serializa la comunidad a un diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "logo_path": self.logo_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "creator_id": self.creator_id,
            "creator": self._serialize_user(self.creator),
            "curators": [self._serialize_user(c.user) for c in self.curators],
            "datasets_count": self.get_datasets_count(),
        }

    def __repr__(self):
        return f"<Community id={self.id} name='{self.name}'>"


class CommunityCurator(db.Model):
    """Asociación entre comunidades y usuarios curadores."""

    __tablename__ = "community_curator"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    assigned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    community = db.relationship("Community", back_populates="curators")
    user = db.relationship("User", backref="curator_of_communities")

    __table_args__ = (db.UniqueConstraint("community_id", "user_id", name="uq_community_curator"),)

    def __repr__(self):
        return f"<CommunityCurator community_id={self.community_id} user_id={self.user_id}>"


class CommunityDataset(db.Model):
    """Asociación entre comunidades y datasets aceptados."""

    __tablename__ = "community_dataset"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=False)
    added_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    added_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    community = db.relationship("Community", back_populates="datasets")
    dataset = db.relationship("BaseDataset", backref="in_communities")
    added_by = db.relationship("User", foreign_keys=[added_by_id])

    __table_args__ = (db.UniqueConstraint("community_id", "dataset_id", name="uq_community_dataset"),)

    def to_dict(self):
        """Serializa la relación comunidad-dataset."""
        return {
            "id": self.id,
            "community_id": self.community_id,
            "dataset_id": self.dataset_id,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "dataset": self.dataset.to_dict() if self.dataset else None,
        }

    def __repr__(self):
        return f"<CommunityDataset community_id={self.community_id} dataset_id={self.dataset_id}>"


class CommunityRequest(db.Model):
    """Representa una solicitud para añadir un dataset a una comunidad."""

    __tablename__ = "community_request"

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)

    requested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    review_comment = db.Column(db.Text, nullable=True)

    # Relaciones
    community = db.relationship("Community", back_populates="requests")
    dataset = db.relationship("BaseDataset", backref="community_requests")
    requester = db.relationship("User", foreign_keys=[requester_id], backref="dataset_requests")
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    # -----------------------------
    # Lógica de negocio
    # -----------------------------
    def approve(self, curator_id: int, comment: str | None = None):
        """Aprueba la solicitud y registra la revisión."""
        self.status = self.STATUS_APPROVED
        self.reviewed_at = datetime.utcnow()
        self.reviewed_by_id = curator_id
        self.review_comment = comment

    def reject(self, curator_id: int, comment: str | None = None):
        """Rechaza la solicitud y registra la revisión."""
        self.status = self.STATUS_REJECTED
        self.reviewed_at = datetime.utcnow()
        self.reviewed_by_id = curator_id
        self.review_comment = comment

    def is_pending(self) -> bool:
        """Devuelve True si la solicitud aún no fue revisada."""
        return self.status == self.STATUS_PENDING

    def to_dict(self):
        """Serializa la solicitud a un diccionario."""
        return {
            "id": self.id,
            "community_id": self.community_id,
            "dataset_id": self.dataset_id,
            "dataset": self.dataset.to_dict() if self.dataset else None,
            "requester": Community._serialize_user(self.requester),
            "message": self.message,
            "status": self.status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": Community._serialize_user(self.reviewed_by),
            "review_comment": self.review_comment,
        }

    def __repr__(self):
        return (
            f"<CommunityRequest id={self.id} community={self.community_id} "
            f"dataset={self.dataset_id} status='{self.status}'>"
        )
