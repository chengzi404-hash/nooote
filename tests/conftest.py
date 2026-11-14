import pytest

from nooote import create_app
from nooote.extensions import db

TEST_PASSWORD = "password123"


@pytest.fixture()
def app(tmp_path):
    database = (tmp_path / "test.db").as_posix()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database}",
            "UPLOAD_FOLDER": (tmp_path / "uploads").as_posix(),
        }
    )
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def register_client(app):
    def make(username="tester", password=TEST_PASSWORD):
        client = app.test_client()
        response = client.post(
            "/register",
            data={
                "username": username,
                "password": password,
                "confirm": password,
            },
        )
        assert response.status_code == 302
        return client

    return make


@pytest.fixture()
def auth_client(register_client):
    return register_client()
