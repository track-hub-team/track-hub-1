import pytest

from app import create_app, db
from app.modules.auth.models import User
from app.modules.community.models import Community

# ------------------------------
# FIXTURES
# ------------------------------


@pytest.fixture(scope="module")
def test_app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


# ------------------------------
# FUNCIONES AUXILIARES
# ------------------------------


def create_user(email="suser@test.com", password="password"):
    from flask import current_app

    with current_app.app_context():
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


def create_community(user, name="Selenium Community", description="Community for Selenium testing"):
    from flask import current_app

    with current_app.app_context():
        community = Community(
            name=name,
            slug=name.lower().replace(" ", "-"),
            description=description,
            creator_id=user.id,
        )
        db.session.add(community)
        db.session.commit()
        db.session.refresh(community)
        return community


# ------------------------------
# TESTS FUNCIONALES
# ------------------------------


def test_create_community_db(test_app):
    """Crea una comunidad directamente en la DB (sin Selenium)."""
    user = create_user()
    community = create_community(user)
    assert community.id is not None
    assert community.name == "Selenium Community"
