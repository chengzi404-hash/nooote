import pytest

from nooote import create_app
from nooote.extensions import db


@pytest.fixture()
def app(tmp_path):
    database = (tmp_path / "test.db").as_posix()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
        }
    )
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
