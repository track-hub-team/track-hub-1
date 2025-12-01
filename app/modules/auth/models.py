from datetime import datetime, timezone
from typing import TYPE_CHECKING

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db

if TYPE_CHECKING:
    from sqlalchemy.orm import DeclarativeBase

    class Model(DeclarativeBase):
        pass  # <-- CORRECCIÓN: 'pass' en su propia línea


class User(Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    data_sets = db.relationship(
        "BaseDataset", foreign_keys="BaseDataset.user_id", lazy=True, cascade="all, delete-orphan"
    )
    profile = db.relationship("UserProfile", backref="user", uselist=False)

    # ----------------------------------------------------------------------
    # Relaciones de SEGUIMIENTO
    # ----------------------------------------------------------------------

    following = db.relationship(
        "Follower",
        foreign_keys="Follower.follower_id",
        backref=db.backref("follower_user", lazy="joined"),
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    followers = db.relationship(
        "Follower",
        foreign_keys="Follower.followed_id",
        backref=db.backref("followed_user", lazy="joined"),
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    followed_communities = db.relationship(
        "CommunityFollower",
        foreign_keys="CommunityFollower.user_id",
        backref=db.backref("follower_user", lazy="joined"),
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ----------------------------------------------------------------------
    # Métodos de la Clase
    # ----------------------------------------------------------------------

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if "password" in kwargs:
            self.set_password(kwargs["password"])

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, password: str) -> None:
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    def temp_folder(self) -> str:
        from app.modules.auth.services import AuthenticationService

        return AuthenticationService().temp_folder_by_user(self)

    # ----------------------------------------------------------------------
    # Métodos de SEGUIMIENTO (User-to-User)
    # ----------------------------------------------------------------------

    def is_following(self, user) -> bool:
        if user.id is None:
            return False
        return self.following.filter_by(followed_id=user.id).first() is not None

    def follow(self, user) -> None:
        if not self.is_following(user):
            from app.modules.community.models import Follower

            f = Follower(follower_id=self.id, followed_id=user.id)
            db.session.add(f)

    def unfollow(self, user) -> None:
        if self.is_following(user):
            f = self.following.filter_by(followed_id=user.id).first()
            if f:
                db.session.delete(f)

    # ----------------------------------------------------------------------
    # Métodos de SEGUIMIENTO (User-to-Community)
    # ----------------------------------------------------------------------

    def is_following_community(self, community) -> bool:
        if community.id is None:
            return False
        return self.followed_communities.filter_by(community_id=community.id).first() is not None
