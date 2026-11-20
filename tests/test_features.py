import json

from sqlalchemy import select

from nooote import create_app
from nooote.config import ROLE_ADMIN
from nooote.extensions import db
from nooote.features import FEATURE_REGISTRY, plugin_feature_key
from nooote.models import User

PASSWORD = "password123"
FEATURE_COLUMNS = ("notes", "attachments", "public_shares", "registration")

PLUGIN_SOURCE = '''
from flask import Blueprint
from nooote.features import Feature, feature_require, plugin_feature_key
from nooote.permissions import permission_require
from nooote.plugins import Plugin


def create_plugin():
    bp = Blueprint("demo", __name__)
    widgets = plugin_feature_key("demo", "widgets")

    @bp.route("")
    @permission_require(["plugin.access"])
    def index():
        return "plugin index"

    @bp.route("/widget")
    @permission_require(["plugin.access"])
    @feature_require(widgets)
    def widget():
        return "plugin widget"

    return Plugin(
        name="demo",
        label="Demo",
        blueprint=bp,
        features=(Feature("widgets", "Widgets"),),
    )
'''


def register(app, username="tester"):
    client = app.test_client()
    client.post(
        "/register",
        data={"username": username, "password": PASSWORD, "confirm": PASSWORD},
    )
    return client


def admin_client(app, username="boss"):
    client = register(app, username)
    with app.app_context():
        user = db.session.execute(
            select(User).where(User.username == username)
        ).scalar_one()
        user.role = ROLE_ADMIN
        db.session.commit()
    return client


def toggle(client, key, enabled):
    return client.post(
        f"/manage/features/{key}",
        data={"enabled": "1" if enabled else "0"},
    )


def test_manage_lists_core_feature_flags(app):
    client = admin_client(app)

    page = client.get("/manage").get_data(as_text=True)

    assert "功能开关" in page
    for key in FEATURE_COLUMNS:
        assert f"<code>{key}</code>" in page
    assert "已关闭" not in page
    assert 'action="/manage/features/notes"' in page


def test_disabled_notes_hide_nav_and_block_routes(app):
    client = admin_client(app)
    note_id = client.post("/console/notes").headers["Location"].rsplit("/", 1)[-1]

    assert toggle(client, "notes", False).status_code == 302

    page = client.get("/console/settings").get_data(as_text=True)
    assert 'data-nav="notes"' not in page
    assert "新建私有笔记" not in page

    response = client.get("/console")
    assert response.status_code == 403
    assert "功能已关闭" in response.get_data(as_text=True)

    api = client.get(f"/api/console/notes/{note_id}")
    assert api.status_code == 403
    assert api.get_json()["error"] == "该功能已被关闭"

    assert toggle(client, "notes", True).status_code == 302
    assert client.get("/console").status_code == 200


def test_disabled_attachments_hide_nav_and_block_routes(app):
    client = admin_client(app)

    toggle(client, "attachments", False)

    page = client.get("/console").get_data(as_text=True)
    assert 'data-nav="attachments"' not in page
    assert client.get("/console/attachments").status_code == 403
    assert client.post("/api/console/attachments").status_code == 403


def test_disabled_registration_keeps_login(app):
    client = admin_client(app)
    guest = app.test_client()

    toggle(client, "registration", False)

    assert guest.get("/register").status_code == 403
    assert guest.get("/login").status_code == 200
    home = guest.get("/").get_data(as_text=True)
    assert 'href="/register"' not in home
    assert 'href="/login"' in home


def test_disabled_public_shares_block_sharing_and_home_list(app):
    client = admin_client(app)
    note_id = client.post("/console/notes").headers["Location"].rsplit("/", 1)[-1]
    client.post(f"/console/notes/{note_id}/publish")

    toggle(client, "public_shares", False)

    assert client.get(f"/share/{note_id}").status_code == 403
    assert client.post(f"/console/notes/{note_id}/publish").status_code == 403
    home = client.get("/").get_data(as_text=True)
    assert 'id="recent"' not in home


def test_only_admins_toggle_features(app):
    member = register(app)
    assert toggle(member, "notes", False).status_code == 403

    guest = app.test_client()
    response = toggle(guest, "notes", False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    assert app.test_client().get("/").status_code == 200


def test_unknown_feature_toggle_is_404(app):
    client = admin_client(app)

    assert toggle(client, "does.not.exist", False).status_code == 404


def test_every_view_requires_registered_features(app):
    known = set(app.extensions[FEATURE_REGISTRY])
    for rule in app.url_map.iter_rules():
        view = app.view_functions[rule.endpoint]
        declared = getattr(view, "required_features", frozenset())
        assert set(declared) <= known, f"{rule.rule} declares an unknown feature"


def build_plugin_app(tmp_path):
    plugin = tmp_path / "plugins" / "demo"
    plugin.mkdir(parents=True)
    (plugin / "__init__.py").write_text(PLUGIN_SOURCE, encoding="utf-8")

    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": (
                f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
            ),
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "PLUGINS_FOLDER": str(tmp_path / "plugins"),
            "PLUGIN_REGISTRY_PATH": str(tmp_path / "plugins.json"),
        }
    )


def test_plugin_features_are_listed_and_split(tmp_path):
    app = build_plugin_app(tmp_path)
    client = admin_client(app)
    plugin_id = app.extensions["plugins"][0].id

    page = client.get("/manage").get_data(as_text=True)
    master = plugin_feature_key("demo")
    widgets = plugin_feature_key("demo", "widgets")
    assert "<code>plugin.demo</code>" in page
    assert f"<code>{widgets}</code>" in page
    assert 'action="/manage/features/plugin.demo.widgets"' in page

    assert client.get(f"/plug/{plugin_id}").status_code == 200
    assert client.get(f"/plug/{plugin_id}/widget").status_code == 200

    toggle(client, widgets, False)
    assert client.get(f"/plug/{plugin_id}").status_code == 200
    assert client.get(f"/plug/{plugin_id}/widget").status_code == 403

    toggle(client, master, False)
    assert client.get(f"/plug/{plugin_id}").status_code == 403
    nav = client.get("/console").get_data(as_text=True)
    assert f'href="/plug/{plugin_id}"' not in nav

    registry = json.loads((tmp_path / "plugins.json").read_text(encoding="utf-8"))
    assert registry["demo"]["id"] == plugin_id
