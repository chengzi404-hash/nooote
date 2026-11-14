import sqlite3

from nooote import _load_or_create_secret, create_app
from nooote.extensions import db
from nooote.models import Note


def create_note(client) -> str:
    response = client.post("/console/notes")
    assert response.status_code == 302
    return response.headers["Location"].rsplit("/", 1)[-1]


def test_index_page_renders_anonymous(client):
    page = client.get("/").get_data(as_text=True)
    assert "Nooote" in page
    assert "登录" in page
    assert "注册" in page
    assert "进入我的控制台" not in page


def test_index_page_renders_for_logged_in_user(auth_client):
    page = auth_client.get("/").get_data(as_text=True)
    assert "进入我的控制台" in page
    assert "退出登录" in page


def test_console_requires_login(client):
    response = client.get("/console")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_console_page_renders(auth_client):
    response = auth_client.get("/console")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "我的笔记" in page
    assert "新建私有笔记" in page
    assert "还没有笔记" in page
    assert "tester" in page


def test_creating_a_note_redirects_to_private_editor(auth_client):
    note_id = create_note(auth_client)

    response = auth_client.get(f"/console/notes/{note_id}")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert f'data-note-id="{note_id}"' in page
    assert 'id="editor"' in page

    data = auth_client.get(f"/api/console/notes/{note_id}").get_json()
    assert data["id"] == note_id
    assert data["content"] == ""
    assert data["is_public"] is False
    assert data["share_url"] == f"/share/{note_id}"


def test_console_lists_own_notes(auth_client):
    note_id = create_note(auth_client)

    page = auth_client.get("/console").get_data(as_text=True)
    assert note_id in page
    assert "私有" in page


def test_save_private_note_and_reload(auth_client):
    note_id = create_note(auth_client)
    content = "# 标题\n\n- 一\n- 二\n\n`code`"

    response = auth_client.put(
        f"/api/console/notes/{note_id}", json={"content": content}
    )
    assert response.status_code == 200
    assert response.get_json()["length"] == len(content)

    data = auth_client.get(f"/api/console/notes/{note_id}").get_json()
    assert data["content"] == content

    page = auth_client.get(f"/console/notes/{note_id}").get_data(as_text=True)
    assert content in page
    assert 'data-preview aria-label="Markdown 预览"></article>' in page


def test_private_note_is_not_public_by_default(auth_client):
    note_id = create_note(auth_client)
    auth_client.put(f"/api/console/notes/{note_id}", json={"content": "secret"})

    assert auth_client.get(f"/share/{note_id}").status_code == 404
    assert auth_client.get(f"/api/share/{note_id}").status_code == 404


def test_publishing_makes_a_read_only_share_page(auth_client):
    note_id = create_note(auth_client)
    auth_client.put(f"/api/console/notes/{note_id}", json={"content": "# 公开"})

    response = auth_client.post(f"/console/notes/{note_id}/publish")
    assert response.status_code == 302

    page = auth_client.get(f"/share/{note_id}")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert f'data-share-id="{note_id}"' in html
    assert "公开 · 只读" in html
    assert 'id="share-source"' in html
    assert "# 公开" in html
    assert 'id="editor"' not in html

    data = auth_client.get(f"/api/share/{note_id}").get_json()
    assert data["content"] == "# 公开"


def test_share_api_is_read_only(auth_client):
    note_id = create_note(auth_client)
    auth_client.post(f"/console/notes/{note_id}/publish")

    response = auth_client.put(f"/api/share/{note_id}", json={"content": "overwrite"})
    assert response.status_code == 405


def test_editing_private_note_syncs_to_share(auth_client):
    note_id = create_note(auth_client)
    auth_client.post(f"/console/notes/{note_id}/publish")

    auth_client.put(f"/api/console/notes/{note_id}", json={"content": "新内容"})

    data = auth_client.get(f"/api/share/{note_id}").get_json()
    assert data["content"] == "新内容"


def test_unpublishing_hides_share(auth_client):
    note_id = create_note(auth_client)
    auth_client.post(f"/console/notes/{note_id}/publish")
    assert auth_client.get(f"/share/{note_id}").status_code == 200

    response = auth_client.post(f"/console/notes/{note_id}/unpublish")
    assert response.status_code == 302
    assert auth_client.get(f"/share/{note_id}").status_code == 404


def test_publish_and_unpublish_are_idempotent(auth_client):
    note_id = create_note(auth_client)
    auth_client.post(f"/console/notes/{note_id}/publish")
    auth_client.post(f"/console/notes/{note_id}/publish")
    assert auth_client.get(f"/share/{note_id}").status_code == 200

    auth_client.post(f"/console/notes/{note_id}/unpublish")
    auth_client.post(f"/console/notes/{note_id}/unpublish")
    assert auth_client.get(f"/share/{note_id}").status_code == 404


def test_delete_removes_note(auth_client):
    note_id = create_note(auth_client)

    response = auth_client.post(f"/console/notes/{note_id}/delete")
    assert response.status_code == 302

    assert auth_client.get(f"/console/notes/{note_id}").status_code == 404
    page = auth_client.get("/console").get_data(as_text=True)
    assert note_id not in page


def test_notes_are_isolated_between_users(register_client):
    owner = register_client("owner")
    note_id = create_note(owner)
    owner.put(f"/api/console/notes/{note_id}", json={"content": "私密"})
    owner.post(f"/console/notes/{note_id}/publish")

    other = register_client("intruder")
    assert other.get(f"/console/notes/{note_id}").status_code == 404
    assert other.get(f"/api/console/notes/{note_id}").status_code == 404
    assert other.put(f"/api/console/notes/{note_id}", json={"content": "x"}).status_code == 404
    assert other.post(f"/console/notes/{note_id}/publish").status_code == 404
    assert other.post(f"/console/notes/{note_id}/delete").status_code == 404

    console_page = other.get("/console").get_data(as_text=True)
    assert note_id not in console_page

    assert other.get(f"/share/{note_id}").status_code == 200


def test_home_lists_only_public_notes(auth_client):
    private_id = create_note(auth_client)
    public_id = create_note(auth_client)
    auth_client.post(f"/console/notes/{public_id}/publish")

    page = auth_client.get("/").get_data(as_text=True)
    assert public_id in page
    assert private_id not in page
    assert "随机公开笔记" in page


def test_note_page_loads_client_renderers(auth_client):
    note_id = create_note(auth_client)
    page = auth_client.get(f"/console/notes/{note_id}").get_data(as_text=True)

    assert "vendor/marked.min.js" in page
    assert "vendor/purify.min.js" in page
    assert "vendor/highlight.min.js" in page
    assert "vendor/katex/katex.min.js" in page
    assert "vendor/katex/katex.min.css" in page
    assert "vendor/mermaid/mermaid.min.js" in page
    assert "vendor/lezer-checks.js" in page
    assert "vendor/ruby-checks.js" in page
    assert "static/app.js" in page


def test_share_page_loads_client_renderers(auth_client):
    note_id = create_note(auth_client)
    auth_client.post(f"/console/notes/{note_id}/publish")
    page = auth_client.get(f"/share/{note_id}").get_data(as_text=True)

    assert "vendor/marked.min.js" in page
    assert "vendor/purify.min.js" in page
    assert "vendor/highlight.min.js" in page
    assert "vendor/katex/katex.min.js" in page
    assert "vendor/mermaid/mermaid.min.js" in page
    assert "static/app.js" in page


def test_vendor_assets_are_served(client):
    for name in (
        "marked.min.js",
        "purify.min.js",
        "highlight.min.js",
        "lezer-checks.js",
        "ruby-checks.js",
        "prism.wasm",
        "katex/katex.min.js",
        "katex/katex.min.css",
        "katex/fonts/KaTeX_Main-Regular.woff2",
        "mermaid/mermaid.min.js",
        "github.min.css",
        "github-dark.min.css",
    ):
        response = client.get(f"/static/vendor/{name}")
        assert response.status_code == 200
        assert response.data


def test_markdown_extra_styles_are_present(client):
    css = client.get("/static/style.css").get_data(as_text=True)

    assert ".markdown-alert-warning" in css
    assert ".markdown-alert-important" in css
    assert ".markdown-alert-tip" in css
    assert ".task-list-item-completed" in css
    assert ".mermaid-diagram" in css
    assert ".console" in css
    assert ".share-workspace" in css
    assert ".badge.public" in css
    assert ".auth-card" in css


def test_server_preview_endpoint_removed(client):
    response = client.post("/api/preview", json={"markdown": "# hi"})
    assert response.status_code == 404


def test_invalid_note_ids_are_rejected(auth_client, client):
    assert auth_client.get("/console/notes/bad%20id").status_code == 404
    assert auth_client.get("/api/console/notes/bad%20id").status_code == 400
    assert auth_client.put(
        "/api/console/notes/bad%20id", json={"content": "x"}
    ).status_code == 400
    assert client.get("/share/bad%20id").status_code == 404
    assert client.get("/api/share/bad%20id").status_code == 400
    assert client.get("/world/bad%20id").status_code == 404


def test_save_requires_json_content(auth_client):
    note_id = create_note(auth_client)

    response = auth_client.put(
        f"/api/console/notes/{note_id}", data="x", content_type="text/plain"
    )
    assert response.status_code == 400

    response = auth_client.put(f"/api/console/notes/{note_id}", json={})
    assert response.status_code == 400


def test_oversized_content_is_rejected(auth_client):
    note_id = create_note(auth_client)
    content = "x" * (256 * 1024 + 1)

    response = auth_client.put(
        f"/api/console/notes/{note_id}", json={"content": content}
    )
    assert response.status_code == 413


def test_world_redirects_to_share(client):
    response = client.get("/world/my-note")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/share/my-note")

    response = client.get("/world?id=my-note")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/share/my-note")

    response = client.get("/world?id=bad%20id")
    assert response.headers["Location"] == "/"


def test_unicode_note_id(app, client):
    with app.app_context():
        db.session.add(
            Note(id="中文笔记", owner_id="someone", content="你好", is_public=True)
        )
        db.session.commit()

    assert client.get("/api/share/中文笔记").get_json()["content"] == "你好"


def test_security_headers(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers
    assert "wasm-unsafe-eval" in response.headers["Content-Security-Policy"]
    assert "style-src 'self' 'unsafe-inline'" in response.headers["Content-Security-Policy"]
    assert "font-src 'self'" in response.headers["Content-Security-Policy"]


def test_legacy_database_is_migrated(tmp_path):
    database = tmp_path / "legacy.db"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE notes ("
        "id VARCHAR(128) NOT NULL, "
        "content TEXT NOT NULL, "
        "created_at DATETIME NOT NULL, "
        "updated_at DATETIME NOT NULL, "
        "PRIMARY KEY (id))"
    )
    connection.execute(
        "INSERT INTO notes VALUES ('old', 'legacy content', "
        "'2024-01-01 00:00:00', '2024-01-01 00:00:00')"
    )
    connection.commit()
    connection.close()

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}",
            "UPLOAD_FOLDER": (tmp_path / "uploads").as_posix(),
        }
    )
    client = app.test_client()

    assert client.get("/api/share/old").get_json()["content"] == "legacy content"
    assert client.get("/share/old").status_code == 200


def test_legacy_user_columns_are_migrated(tmp_path):
    database = tmp_path / "legacy_users.db"
    connection = sqlite3.connect(database)
    connection.execute(
        "CREATE TABLE users ("
        "id VARCHAR(64) NOT NULL, "
        "display_name VARCHAR(64) NOT NULL, "
        "default_public BOOLEAN NOT NULL, "
        "theme VARCHAR(16) NOT NULL, "
        "created_at DATETIME NOT NULL, "
        "PRIMARY KEY (id))"
    )
    connection.execute(
        "INSERT INTO users VALUES ('old', '', 0, 'auto', '2024-01-01 00:00:00')"
    )
    connection.commit()
    connection.close()

    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}",
            "UPLOAD_FOLDER": (tmp_path / "uploads").as_posix(),
        }
    )
    client = app.test_client()

    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "password": "password123",
            "confirm": "password123",
        },
    )
    assert response.status_code == 302
    assert client.get("/console").status_code == 200


def test_secret_key_is_persisted(tmp_path):
    first = _load_or_create_secret(str(tmp_path))
    second = _load_or_create_secret(str(tmp_path))

    assert first == second
    assert len(first) == 64


def test_settings_page_renders(auth_client):
    response = auth_client.get("/console/settings")
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "用户设置" in page
    assert "tester" in page
    assert 'name="display_name"' in page
    assert 'name="theme" value="auto"' in page
    assert 'name="default_public"' in page


def test_settings_are_saved_and_applied(auth_client):
    response = auth_client.post(
        "/console/settings",
        data={"display_name": "小明", "theme": "dark", "default_public": "on"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "设置已保存" in page
    assert 'data-theme="dark"' in page
    assert 'value="小明"' in page

    console = auth_client.get("/console").get_data(as_text=True)
    assert "小明 的笔记" in console


def test_default_public_applies_to_new_notes(auth_client):
    auth_client.post(
        "/console/settings",
        data={"display_name": "", "theme": "auto", "default_public": "on"},
    )

    note_id = create_note(auth_client)
    data = auth_client.get(f"/api/console/notes/{note_id}").get_json()
    assert data["is_public"] is True
    assert auth_client.get(f"/share/{note_id}").status_code == 200


def test_theme_setting_applies_to_pages(auth_client):
    auth_client.post("/console/settings", data={"theme": "dark", "display_name": ""})

    assert 'data-theme="dark"' in auth_client.get("/").get_data(as_text=True)
    assert 'data-theme="dark"' in auth_client.get("/console").get_data(as_text=True)

    note_id = create_note(auth_client)
    assert 'data-theme="dark"' in auth_client.get(
        f"/console/notes/{note_id}"
    ).get_data(as_text=True)


def test_light_theme_uses_light_highlighting(auth_client):
    auth_client.post("/console/settings", data={"theme": "light", "display_name": ""})

    page = auth_client.get("/").get_data(as_text=True)
    assert 'data-theme="light"' in page
    assert "github.min.css" in page
    assert 'media="(prefers-color-scheme: light)"' not in page


def test_invalid_theme_falls_back_to_auto(auth_client):
    auth_client.post("/console/settings", data={"theme": "neon", "display_name": ""})

    page = auth_client.get("/console/settings").get_data(as_text=True)
    assert 'data-theme="' not in page
    assert 'name="theme" value="auto" checked' in page


def test_settings_are_isolated_between_users(register_client):
    first = register_client("first")
    first.post("/console/settings", data={"display_name": "甲", "theme": "dark"})

    second = register_client("second")
    page = second.get("/console/settings").get_data(as_text=True)
    assert 'data-theme="' not in page
    assert 'value="甲"' not in page
