import json

from nooote import create_app
from nooote.config import PLUGIN_ID_BYTES

PASSWORD = "password123"

PLUGIN_SOURCE = '''
from flask import Blueprint, render_template
from nooote.permissions import permission_require
from nooote.plugins import Plugin


def create_plugin():
    bp = Blueprint(
        "demo", __name__, template_folder="templates", static_folder="static"
    )

    @bp.route("")
    @permission_require(["plugin.access"])
    def index():
        return render_template("demo/index.html")

    @bp.route("/widget")
    @permission_require(["plugin.access"])
    def widget():
        return {"widget": True, "plugin": "demo"}

    return Plugin(name="demo", label="Demo", blueprint=bp)
'''


def write_plugin(tmp_path, source: str = PLUGIN_SOURCE, name: str = "demo"):
    folder = tmp_path / "plugins" / name
    (folder / "templates" / name).mkdir(parents=True)
    (folder / "static").mkdir()
    (folder / "__init__.py").write_text(source, encoding="utf-8")
    (folder / "templates" / name / "index.html").write_text(
        '<p id="demo">Hello from demo</p>', encoding="utf-8"
    )
    (folder / "static" / "demo.css").write_text(
        "#demo { color: red; }", encoding="utf-8"
    )
    return folder


def build_app(tmp_path, **config):
    options = {
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "SQLALCHEMY_DATABASE_URI": (
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        ),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
        "PLUGINS_FOLDER": str(tmp_path / "plugins"),
        "PLUGIN_REGISTRY_PATH": str(tmp_path / "plugins.json"),
    }
    options.update(config)
    return create_app(options)


def login(app):
    client = app.test_client()
    client.post(
        "/register",
        data={"username": "tester", "password": PASSWORD, "confirm": PASSWORD},
    )
    return client


def test_plugin_gets_a_generated_id_and_routes(tmp_path):
    write_plugin(tmp_path)
    app = build_app(tmp_path)

    installed = app.extensions["plugins"]
    assert len(installed) == 1
    plugin_id = installed[0].id
    assert len(plugin_id) == PLUGIN_ID_BYTES * 2
    assert int(plugin_id, 16) >= 0

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert f"/plug/{plugin_id}" in rules
    assert f"/plug/{plugin_id}/widget" in rules

    registry = json.loads((tmp_path / "plugins.json").read_text(encoding="utf-8"))
    assert registry["demo"]["id"] == plugin_id
    assert registry["demo"]["installed_at"]


def test_plugin_page_and_sidebar_entry(tmp_path):
    write_plugin(tmp_path)
    app = build_app(tmp_path)
    plugin_id = app.extensions["plugins"][0].id
    client = login(app)

    page = client.get(f"/plug/{plugin_id}")
    assert page.status_code == 200
    assert "Hello from demo" in page.get_data(as_text=True)

    widget = client.get(f"/plug/{plugin_id}/widget")
    assert widget.status_code == 200
    assert widget.get_json() == {"widget": True, "plugin": "demo"}

    sidebar = client.get("/console").get_data(as_text=True)
    assert f'href="/plug/{plugin_id}"' in sidebar
    assert "Demo" in sidebar


def test_plugin_requires_its_declared_permission(tmp_path):
    write_plugin(tmp_path)
    app = build_app(tmp_path)
    plugin_id = app.extensions["plugins"][0].id

    response = app.test_client().get(f"/plug/{plugin_id}")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_plugin_static_assets_are_public(tmp_path):
    write_plugin(tmp_path)
    app = build_app(tmp_path)
    plugin_id = app.extensions["plugins"][0].id

    response = app.test_client().get(f"/plug/{plugin_id}/static/demo.css")
    assert response.status_code == 200
    assert "#demo" in response.get_data(as_text=True)


def test_plugin_id_survives_restarts(tmp_path):
    write_plugin(tmp_path)
    first = build_app(tmp_path)
    first_id = first.extensions["plugins"][0].id

    second = build_app(tmp_path)
    assert second.extensions["plugins"][0].id == first_id
    registry = json.loads((tmp_path / "plugins.json").read_text(encoding="utf-8"))
    assert registry["demo"]["id"] == first_id


def test_broken_plugin_is_skipped(tmp_path):
    write_plugin(tmp_path, source="def create_plugin():\n    raise RuntimeError('boom')\n")

    app = build_app(tmp_path)

    assert app.extensions["plugins"] == []
    assert not any("demo" in rule.endpoint for rule in app.url_map.iter_rules())
