from datetime import datetime

from app import db


class Community(db.Model):
    __tablename__ = "community"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    slug = db.Column(db.String(120), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=False)
    logo_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    creator = db.relationship("User", foreign_keys=[creator_id], backref="created_communities")
    curators = db.relationship("CommunityCurator", back_populates="community", cascade="all, delete-orphan")
    datasets = db.relationship("CommunityDataset", back_populates="community", cascade="all, delete-orphan")

    def get_datasets_count(self):
        return len(self.datasets)

    def is_curator(self, user_id: int) -> bool:
        return any(c.user_id == user_id for c in self.curators)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "logo_path": self.logo_path,
            "created_at": self.created_at.isoformat(),
            "datasets_count": self.get_datasets_count(),
            "curators": [{"id": c.user.id, "email": c.user.email} for c in self.curators],
        }


class CommunityCurator(db.Model):
    __tablename__ = "community_curator"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    community = db.relationship("Community", back_populates="curators")
    user = db.relationship("User", backref="curator_of_communities")

    __table_args__ = (db.UniqueConstraint("community_id", "user_id", name="uq_community_curator"),)


class CommunityDataset(db.Model):
    __tablename__ = "community_dataset"

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("community.id"), nullable=False)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    community = db.relationship("Community", back_populates="datasets")
    dataset = db.relationship("BaseDataset", backref="in_communities")
    added_by = db.relationship("User", foreign_keys=[added_by_id])

    __table_args__ = (db.UniqueConstraint("community_id", "dataset_id", name="uq_community_dataset"),)
