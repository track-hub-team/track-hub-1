from datetime import datetime, timezone

from app import db


def utc_now():
    """Devuelve la fecha/hora actual en UTC con información de timezone."""
    return datetime.now(timezone.utc)


class Community(db.Model):

    __tablename__ = "community"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    slug = db.Column(db.String(120), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=False)
    logo_path = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    # Creador de la comunidad
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Relaciones
    # Usamos la cadena "User" en el relationship para evitar dependencias circulares
    # y confiamos en que Mypy use la importación condicional.
    creator = db.relationship("User", foreign_keys=[creator_id], backref="created_communities")
    curators = db.relationship("CommunityCurator", back_populates="community", cascade="all, delete-orphan")
    datasets = db.relationship("CommunityDataset", back_populates="community", cascade="all, delete-orphan")
    requests = db.relationship("CommunityRequest", back_populates="community", cascade="all, delete-orphan")

    # RELACIÓN DE SEGUIMIENTO A COMUNIDADES
    followers = db.relationship("CommunityFollower", backref="community", cascade="all, delete-orphan", lazy="dynamic")

    def get_datasets_count(self):
        """Obtener el número de datasets en la comunidad"""
        return len(self.datasets)

    def get_curators_list(self):
        """Obtener lista de usuarios curadores"""
        return [cast("User", curator.user) for curator in self.curators]

    def is_curator(self, user_id):
        """Verificar si un usuario es curador de esta comunidad"""
        return any(curator.user_id == user_id for curator in self.curators)

    def get_logo_url(self):
        """Obtener URL del logo o imagen por defecto"""
        if self.logo_path:
            if self.logo_path.startswith("/") or self.logo_path.startswith("http"):
                return self.logo_path
            return f"/{self.logo_path}"
        # Usar placeholder con iniciales
        return f"https://ui-avatars.com/api/?name={self.name[:2]}&background=6366f1&color=fff&size=120"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "logo_path": self.logo_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "creator_id": self.creator_id,
            "creator": (
                {
                    "id": self.creator.id,
                    "email": self.creator.email,
                    "name": (
                        self.creator.profile.name if hasattr(self.creator, "profile") and self.creator.profile else None
                    ),
                    "surname": (
                        self.creator.profile.surname
                        if hasattr(self.creator, "profile") and self.creator.profile
                        else None
                    ),
                }
                if self.creator
                else None
            ),
            "curators": [
                {
                    "id": curator.user.id,
                    "email": curator.user.email,
                    "name": (
                        curator.user.profile.name if hasattr(curator.user, "profile") and curator.user.profile else None
                    ),
                    "surname": (
                        curator.user.profile.surname
                        if hasattr(curator.user, "profile") and curator.user.profile
                        else None
                    ),
                }
                for curator in self.curators
            ],
            "datasets_count": self.get_datasets_count(),
        }

    def __repr__(self):
        return f"Community<{self.id}:{self.name}>"


class CommunityCurator(Model): 
    """
    Tabla de asociación entre comunidades y usuarios curadores.
    ...
    """

    __tablename__ = "community_curator"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    assigned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    # Relaciones
    community = db.relationship("Community", back_populates="curators")
    user = db.relationship("User", backref="curator_of_communities")

    # Constraint: Un usuario no puede ser curador dos veces de la misma comunidad
    __table_args__ = (db.UniqueConstraint("community_id", "user_id", name="uq_community_curator"),)

    def __repr__(self):
        return f"CommunityCurator<community_id={self.community_id}, user_id={self.user_id}>"


class CommunityDataset(Model): 
    """
    Tabla de asociación entre comunidades y datasets.
    ...
    """

    __tablename__ = "community_dataset"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    # Curador que aprobó la solicitud (para auditoría, el autor real está en dataset.user_id)
    added_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    # Relaciones
    community = db.relationship("Community", back_populates="datasets")
    dataset = db.relationship("BaseDataset", backref="in_communities")
    added_by = db.relationship("User", foreign_keys=[added_by_id])

    # Constraint: Un dataset no puede estar dos veces en la misma comunidad
    __table_args__ = (db.UniqueConstraint("community_id", "dataset_id", name="uq_community_dataset"),)

    def to_dict(self):
        """Serializar a diccionario"""
        return {
            "id": self.id,
            "community_id": self.community_id,
            "dataset_id": self.dataset_id,
            "added_at": self.added_at.isoformat() if self.added_at else None,
            "dataset": self.dataset.to_dict() if self.dataset else None,
        }

    def __repr__(self):
        return f"CommunityDataset<community_id={self.community_id}, dataset_id={self.dataset_id}>"


class CommunityRequest(Model):
    """
    Solicitud para añadir un dataset a una comunidad.
    ...
    """

    __tablename__ = "community_request"

    # Estados posibles
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=False)

    # Usuario que hizo la solicitud
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Mensaje de la solicitud
    message = db.Column(db.Text, nullable=True)

    # Estado de la solicitud
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)

    # Fechas
    requested_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    # Revisión (si fue aprobada o rechazada)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    review_comment = db.Column(db.Text, nullable=True)

    # Relaciones
    community = db.relationship("Community", back_populates="requests")
    dataset = db.relationship("BaseDataset", backref="community_requests")
    requester = db.relationship("User", foreign_keys=[requester_id], backref="dataset_requests")
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    def approve(self, curator_id, comment=None):
        """Aprobar la solicitud y añadir el dataset a la comunidad"""
        self.status = self.STATUS_APPROVED
        self.reviewed_at = utc_now()
        self.reviewed_by_id = curator_id
        self.review_comment = comment

    def reject(self, curator_id, comment=None):
        """Rechazar la solicitud"""
        self.status = self.STATUS_REJECTED
        self.reviewed_at = utc_now()
        self.reviewed_by_id = curator_id
        self.review_comment = comment

    def is_pending(self):
        """Verificar si la solicitud está pendiente"""
        return self.status == self.STATUS_PENDING

    def to_dict(self):
        """Serializar a diccionario"""
        return {
            "id": self.id,
            "community_id": self.community_id,
            "dataset_id": self.dataset_id,
            "dataset": self.dataset.to_dict() if self.dataset else None,
            "requester": (
                {
                    "id": self.requester.id,
                    "email": self.requester.email,
                    "name": (
                        self.requester.profile.name
                        if hasattr(self.requester, "profile") and self.requester.profile
                        else None
                    ),
                    "surname": (
                        self.requester.profile.surname
                        if hasattr(self.requester, "profile") and self.requester.profile
                        else None
                    ),
                }
                if self.requester
                else None
            ),
            "message": self.message,
            "status": self.status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": (
                {
                    "id": self.reviewed_by.id,
                    "email": self.reviewed_by.email,
                    "name": (
                        self.reviewed_by.profile.name
                        if hasattr(self.reviewed_by, "profile") and self.reviewed_by.profile
                        else None
                    ),
                    "surname": (
                        self.reviewed_by.profile.surname
                        if hasattr(self.reviewed_by, "profile") and self.reviewed_by.profile
                        else None
                    ),
                }
                if self.reviewed_by
                else None
            ),
            "review_comment": self.review_comment,
        }

    def __repr__(self):
        return (
            f"CommunityRequest<{self.id}:community={self.community_id},dataset={self.dataset_id},status={self.status}>"
        )


# ----------------------------------------------------------------------
# MODELOS DE ASOCIACIÓN PARA EL SEGUIMIENTO
# ----------------------------------------------------------------------


class Follower(Model):  
    """
    Tabla de asociación para el seguimiento de usuarios (User sigue a otro User).
    """

    __tablename__ = "follower"

    id = db.Column(db.Integer, primary_key=True)
    # Usuario que sigue (el seguidor)
    follower_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    # Usuario siendo seguido (el seguido)
    followed_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    followed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Constraint: Un usuario solo puede seguir a otro una vez
    __table_args__ = (db.UniqueConstraint("follower_id", "followed_id", name="uq_follower_followed"),)

    def __repr__(self):
        return f"Follower<follower_id={self.follower_id}, followed_id={self.followed_id}>"


class CommunityFollower(Model):
    """
    Tabla de asociación para el seguimiento de Comunidades por parte de Usuarios.
    """

    __tablename__ = "community_follower"

    id = db.Column(db.Integer, primary_key=True)
    # Usuario que sigue
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    # Comunidad seguida
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False, index=True)
    followed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Constraint: Un usuario solo puede seguir a una comunidad una vez
    __table_args__ = (db.UniqueConstraint("user_id", "community_id", name="uq_user_community_follow"),)

    def __repr__(self):
        return f"CommunityFollower<user_id={self.user_id}, community_id={self.community_id}>"
