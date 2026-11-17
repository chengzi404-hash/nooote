import pytest
from sqlalchemy import select

from nooote.config import (
    PERMISSIONS,
    ROLE_ADMIN,
    ROLE_GUEST,
    ROLE_MEMBER,
    ROLE_PERMISSIONS,
)
from nooote.extensions import db
from nooote.models import Note, User
from nooote.permissions import granted_permissions, initial_role, permission_require

PASSWORD = "password123"


def create_note(client) -> str:
    response = client.post("/console/notes")
    assert response.status_code == 302
    return response.headers["Location"].rsplit("/", 1)[-1]


def set_role(app, username: str, role: str) -> None:
    with app.app_context():
        user = db.session.execute(
            select(User).where(User.username == username)
        ).scalar_one()
        user.role = role
        db.session.commit()


def user_id(app, username: str) -> str:
    with app.app_context():
        return db.session.execute(
            select(User.id).where(User.username == username)
        ).scalar_one()


# ---------------------------------------------------------------- route wiring


def test_every_route_declares_permissions(app):
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        view = app.view_functions[rule.endpoint]
        assert hasattr(view, "required_permissions"), f"{rule.rule} is unprotected"


def test_declared_permissions_exist(app):
    known = set(PERMISSIONS)
    for rule in app.url_map.iter_rules():
        view = app.view_functions[rule.endpoint]
        declared = getattr(view, "required_permissions", frozenset())
        assert set(declared) <= known, f"{rule.rule} declares unknown permissions"


def test_permission_require_rejects_unknown_permission():
    with pytest.raises(ValueError):
        permission_require(["note.teleport"])


# ---------------------------------------------------------------- role groups


def test_role_permission_groups():
    assert ROLE_PERMISSIONS[ROLE_GUEST] < ROLE_PERMISSIONS[ROLE_MEMBER]
    assert ROLE_PERMISSIONS[ROLE_ADMIN] == frozenset(PERMISSIONS)
    assert ROLE_PERMISSIONS[ROLE_MEMBER] <= ROLE_PERMISSIONS[ROLE_ADMIN]
    assert "note.write" in ROLE_PERMISSIONS[ROLE_MEMBER]
    assert "note.write" not in ROLE_PERMISSIONS[ROLE_GUEST]
    assert "manage.view" in ROLE_PERMISSIONS[ROLE_ADMIN]
    assert "manage.view" not in ROLE_PERMISSIONS[ROLE_MEMBER]


def test_managers_are_a_superset_of_members():
    assert "manage.users.write" in ROLE_PERMISSIONS[ROLE_ADMIN]
    assert "manage.users.write" not in ROLE_PERMISSIONS[ROLE_MEMBER]


def test_guests_get_the_guest_group():
    assert granted_permissions(None) == ROLE_PERMISSIONS[ROLE_GUEST]


def test_unknown_role_falls_back_to_member():
    class FakeUser:
        role = "courier"

    user = FakeUser()
    assert granted_permissions(user) == ROLE_PERMISSIONS[ROLE_MEMBER]


def test_registration_assigns_member_role(auth_client, app):
    with app.app_context():
        user = db.session.execute(
            select(User).where(User.username == "tester")
        ).scalar_one()
        assert user.role == ROLE_MEMBER


def test_admin_usernames_get_the_admin_role(app):
    app.config["ADMIN_USERNAMES"] = frozenset({"boss"})
    client = app.test_client()
    client.post(
        "/register",
        data={"username": "boss", "password": PASSWORD, "confirm": PASSWORD},
    )

    with app.app_context():
        assert initial_role("boss") == ROLE_ADMIN
        user = db.session.execute(
            select(User).where(User.username == "boss")
        ).scalar_one()
        assert user.role == ROLE_ADMIN


# ---------------------------------------------------------------- guest access


def test_guest_can_read_public_pages(client):
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200


def test_guest_is_redirected_from_console(client):
    for path in ("/console", "/console/settings", "/console/attachments", "/manage"):
        response = client.get(path)
        assert response.status_code == 302, path
        assert "/login" in response.headers["Location"], path


def test_guest_gets_json_401_for_private_api(client):
    response = client.get("/api/console/notes/abc")
    assert response.status_code == 401
    assert response.get_json()["error"] == "请先登录"


# ---------------------------------------------------------------- manage page


def test_member_cannot_reach_manage(auth_client):
    response = auth_client.get("/manage")
    assert response.status_code == 403
    assert "没有访问权限" in response.get_data(as_text=True)


def test_member_cannot_change_roles(register_client, app):
    member = register_client("member")
    register_client("other")
    other_id = user_id(app, "other")

    response = member.post(f"/manage/users/{other_id}/role", data={"role": ROLE_ADMIN})
    assert response.status_code == 403


def test_admin_sidebar_link_is_hidden_from_members(auth_client):
    page = auth_client.get("/console").get_data(as_text=True)
    assert "/manage" not in page


def test_admin_sidebar_links_to_manage(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)

    page = admin.get("/console").get_data(as_text=True)
    assert 'href="/manage"' in page
    assert "站点管理" in page


def test_manage_lists_users_and_groups(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)
    register_client("someone")

    response = admin.get("/manage")
    assert response.status_code == 200
    page = response.get_data(as_text=True)

    assert "站点管理" in page
    assert "站点数据" in page
    assert "权限组" in page
    assert "boss" in page
    assert "someone" in page
    assert 'name="role"' in page


def test_admin_can_change_another_users_role(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)
    register_client("member")
    member_id = user_id(app, "member")

    response = admin.post(f"/manage/users/{member_id}/role", data={"role": ROLE_ADMIN})
    assert response.status_code == 302

    with app.app_context():
        role = db.session.execute(
            select(User.role).where(User.id == member_id)
        ).scalar_one()
        assert role == ROLE_ADMIN


def test_admin_cannot_change_own_role(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)
    admin_id = user_id(app, "boss")

    response = admin.post(f"/manage/users/{admin_id}/role", data={"role": ROLE_MEMBER})
    assert response.status_code == 302

    with app.app_context():
        role = db.session.execute(
            select(User.role).where(User.id == admin_id)
        ).scalar_one()
        assert role == ROLE_ADMIN


def test_invalid_role_is_rejected(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)
    register_client("member")
    member_id = user_id(app, "member")

    assert admin.post(
        f"/manage/users/{member_id}/role", data={"role": "superuser"}
    ).status_code == 400


def test_unknown_user_role_update_is_404(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)

    assert admin.post(
        "/manage/users/missing/role", data={"role": ROLE_MEMBER}
    ).status_code == 404


def test_old_console_users_route_is_gone(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)

    assert admin.get("/console/users").status_code == 404


# ---------------------------------------------------------------- manage stats


def test_manage_reports_site_wide_stats(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)
    set_role(app, "boss", ROLE_ADMIN)

    register_client("member")
    note_id = create_note(admin)
    admin.put(f"/api/console/notes/{note_id}", json={"content": "abc"})

    page = admin.get("/manage").get_data(as_text=True)
    assert "账号" in page
    assert "笔记" in page
    assert "附件" in page


def test_site_stats_counts_every_account_and_note(register_client, app):
    from nooote.services import site_stats

    owner = register_client("owner")
    register_client("other")

    private_id = create_note(owner)
    public_id = create_note(owner)
    owner.put(f"/api/console/notes/{private_id}", json={"content": "secret"})
    owner.put(f"/api/console/notes/{public_id}", json={"content": "hello"})
    owner.post(f"/console/notes/{public_id}/publish")

    with app.app_context():
        stats = site_stats()

    assert stats["users"] == 2
    assert stats["role_counts"][ROLE_MEMBER] == 2
    assert stats["notes"] == 2
    assert stats["public_notes"] == 1
    assert stats["private_notes"] == 1
    assert stats["note_bytes"] == len("secret") + len("hello")
    assert stats["attachments"] == 0
    assert stats["attachment_bytes"] == 0


def test_site_stats_groups_unknown_roles_as_members(register_client, app):
    from nooote.services import site_stats

    register_client("odd")
    with app.app_context():
        user = db.session.execute(
            select(User).where(User.username == "odd")
        ).scalar_one()
        user.role = "courier"
        db.session.commit()

        stats = site_stats()

    assert stats["role_counts"][ROLE_MEMBER] == 1
    assert sum(stats["role_counts"].values()) == 1


def test_site_stats_counts_attachments_on_disk(register_client, app):
    import io

    from nooote.services import site_stats

    owner = register_client("owner")
    payload = b"\x89PNG\r\n\x1a\n" + b"0" * 16
    owner.post(
        "/api/console/attachments",
        data={"file": (io.BytesIO(payload), "pic.png", "image/png")},
        content_type="multipart/form-data",
    )

    with app.app_context():
        stats = site_stats()

    assert stats["attachments"] == 1
    assert stats["attachment_bytes"] == len(payload)


def test_manage_shows_role_group_counts(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)
    register_client("member")

    page = admin.get("/manage").get_data(as_text=True)
    assert "个账号" in page


# ---------------------------------------------------------------- member scope


def test_member_permissions_cover_notes_and_attachments(auth_client):
    note_id = create_note(auth_client)
    assert auth_client.put(
        f"/api/console/notes/{note_id}", json={"content": "hi"}
    ).status_code == 200
    assert auth_client.post(f"/console/notes/{note_id}/publish").status_code == 302
    assert auth_client.post(f"/console/notes/{note_id}/unpublish").status_code == 302
    assert auth_client.post(f"/console/notes/{note_id}/delete").status_code == 302


def test_settings_page_shows_the_role_and_granted_permissions(auth_client):
    page = auth_client.get("/console/settings").get_data(as_text=True)

    assert "权限组" in page
    assert "成员" in page
    assert "note.write" in page
    assert "manage.view" not in page


def test_admin_settings_page_lists_manage_permissions(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", ROLE_ADMIN)

    page = admin.get("/console/settings").get_data(as_text=True)
    assert "管理员" in page
    assert "manage.view" in page


# ---------------------------------------------------------------- error surfaces


def test_forbidden_page_is_english_with_account_locale(register_client):
    member = register_client("member")
    member.post("/console/settings", data={"locale": "en", "theme": "auto"})

    response = member.get("/manage")
    assert response.status_code == 403
    page = response.get_data(as_text=True)
    assert "Access denied" in page
    assert "没有访问权限" not in page


def test_forbidden_api_endpoint_returns_json(auth_client, monkeypatch):
    from nooote import permissions

    restricted = dict(ROLE_PERMISSIONS)
    restricted[ROLE_MEMBER] = restricted[ROLE_MEMBER] - {"note.read"}
    monkeypatch.setattr(permissions, "ROLE_PERMISSIONS", restricted)

    response = auth_client.get("/api/console/notes/abc")
    assert response.status_code == 403
    assert response.get_json()["error"] == "没有权限执行该操作"
