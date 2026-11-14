from sqlalchemy import select
from werkzeug.security import check_password_hash

from nooote.extensions import db
from nooote.models import User

PASSWORD = "password123"
REGISTER_DATA = {
    "username": "alice",
    "password": PASSWORD,
    "confirm": PASSWORD,
}


def test_register_page_renders(client):
    page = client.get("/register").get_data(as_text=True)
    assert "注册" in page
    assert 'name="username"' in page
    assert 'name="password"' in page
    assert 'name="confirm"' in page


def test_registration_logs_in_and_hashes_password(app, client):
    response = client.post("/register", data=REGISTER_DATA)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/console")

    with app.app_context():
        user = db.session.execute(
            select(User).where(User.username == "alice")
        ).scalar_one()
        assert user.password_hash != PASSWORD
        assert check_password_hash(user.password_hash, PASSWORD)

    assert client.get("/console").status_code == 200


def test_duplicate_username_is_rejected(client):
    client.post("/register", data=REGISTER_DATA)
    client.post("/logout")

    response = client.post("/register", data=REGISTER_DATA, follow_redirects=True)
    assert response.status_code == 200
    assert "用户名已被使用" in response.get_data(as_text=True)


def test_password_mismatch_is_rejected(client):
    response = client.post(
        "/register",
        data={"username": "alice", "password": PASSWORD, "confirm": "different123"},
        follow_redirects=True,
    )
    assert "两次输入的密码不一致" in response.get_data(as_text=True)


def test_short_password_is_rejected(client):
    response = client.post(
        "/register",
        data={"username": "alice", "password": "short", "confirm": "short"},
        follow_redirects=True,
    )
    assert "密码至少需要 8 位" in response.get_data(as_text=True)


def test_invalid_username_is_rejected(client):
    response = client.post(
        "/register",
        data={"username": "a b", "password": PASSWORD, "confirm": PASSWORD},
        follow_redirects=True,
    )
    assert "用户名需为" in response.get_data(as_text=True)


def test_login_with_correct_credentials(client):
    client.post("/register", data=REGISTER_DATA)
    client.post("/logout")

    response = client.post(
        "/login", data={"username": "alice", "password": PASSWORD}
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/console")
    assert client.get("/console").status_code == 200


def test_login_with_wrong_password_fails(client):
    client.post("/register", data=REGISTER_DATA)
    client.post("/logout")

    response = client.post(
        "/login", data={"username": "alice", "password": "wrong-password"}
    )
    assert response.status_code == 200
    assert "用户名或密码错误" in response.get_data(as_text=True)
    assert client.get("/console").status_code == 302


def test_login_with_unknown_user_fails(client):
    response = client.post(
        "/login", data={"username": "nobody", "password": PASSWORD}
    )
    assert response.status_code == 200
    assert "用户名或密码错误" in response.get_data(as_text=True)


def test_logout_clears_session(auth_client):
    response = auth_client.post("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")

    assert auth_client.get("/console").status_code == 302


def test_protected_api_requires_login(client):
    assert client.get("/api/console/notes/abc").status_code == 401
    assert client.put(
        "/api/console/notes/abc", json={"content": "x"}
    ).status_code == 401
    assert client.post(
        "/api/console/attachments", data={}, content_type="multipart/form-data"
    ).status_code == 401
    assert client.delete(
        "/api/console/attachments/" + "a" * 20
    ).status_code == 401


def test_console_redirect_includes_next(client):
    response = client.get("/console/settings")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert "next=" in response.headers["Location"]


def test_login_honors_safe_next(client):
    client.post("/register", data=REGISTER_DATA)
    client.post("/logout")

    response = client.post(
        "/login?next=%2Fconsole%2Fsettings",
        data={"username": "alice", "password": PASSWORD},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/console/settings")


def test_login_ignores_external_next(client):
    client.post("/register", data=REGISTER_DATA)
    client.post("/logout")

    response = client.post(
        "/login?next=//evil.example",
        data={"username": "alice", "password": PASSWORD},
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/console"


def test_logged_in_user_is_redirected_away_from_auth_pages(auth_client):
    assert auth_client.get("/login").status_code == 302
    assert auth_client.get("/register").status_code == 302
