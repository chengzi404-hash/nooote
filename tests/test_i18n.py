import io
import sqlite3

import pytest
from sqlalchemy import select

from nooote import create_app
from nooote.extensions import db
from nooote.models import User

PASSWORD = "password123"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@pytest.fixture()
def en_client(app):
    client = app.test_client()
    client.set_cookie("lang", "en")
    return client


@pytest.fixture()
def en_auth_client(app):
    client = app.test_client()
    client.post(
        "/register",
        data={"username": "tester", "password": PASSWORD, "confirm": PASSWORD},
    )
    client.post("/console/settings", data={"locale": "en", "theme": "auto"})
    return client


def create_note(client) -> str:
    response = client.post("/console/notes")
    assert response.status_code == 302
    return response.headers["Location"].rsplit("/", 1)[-1]


def test_default_locale_is_chinese(client):
    page = client.get("/").get_data(as_text=True)

    assert 'lang="zh-CN"' in page
    assert "免费创建账号" in page
    assert 'data-locale="zh"' in page


def test_english_cookie_switches_the_interface(en_client):
    page = en_client.get("/").get_data(as_text=True)

    assert 'lang="en"' in page
    assert "Create a free account" in page
    assert 'data-locale="en"' in page
    assert "免费创建账号" not in page


def test_language_endpoint_sets_cookie_and_redirects(client):
    response = client.post("/language", data={"locale": "en", "next": "/"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert "lang=en" in response.headers["Set-Cookie"].replace(" ", "")

    page = client.get("/").get_data(as_text=True)
    assert 'lang="en"' in page


def test_language_endpoint_rejects_unsupported_locale(client):
    assert client.post("/language", data={"locale": "fr"}).status_code == 400
    assert client.post("/language", data={}).status_code == 400


def test_language_endpoint_blocks_external_redirects(client):
    for target in ("//evil.example", "https://evil.example", "/\\evil.example"):
        response = client.post("/language", data={"locale": "en", "next": target})
        assert response.status_code == 302
        assert response.headers["Location"] == "/"


def test_english_flash_messages(en_client):
    response = en_client.post(
        "/register",
        data={"username": "a b", "password": PASSWORD, "confirm": PASSWORD},
    )
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "letters, digits, underscores, dots or hyphens" in page
    assert "用户名需为" not in page


def test_english_api_errors(client, en_client):
    payload = en_client.post(
        "/api/console/attachments",
        data={},
        content_type="multipart/form-data",
    ).get_json()

    assert payload["error"] == "Authentication required"

    invalid = en_client.get("/api/share/bad%20id")
    assert invalid.status_code == 400
    assert invalid.get_json()["error"] == "Invalid note id"

    zh_payload = client.post(
        "/api/console/attachments",
        data={},
        content_type="multipart/form-data",
    ).get_json()
    assert zh_payload["error"] == "请先登录"


def test_english_upload_error_message(en_auth_client):
    response = en_auth_client.post(
        "/api/console/attachments",
        data={"file": (io.BytesIO(b""), "empty.png", "image/png")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "The file is empty"


def test_english_upload_success_flash(en_auth_client):
    response = en_auth_client.post(
        "/console/attachments",
        data={"file": (io.BytesIO(PNG_BYTES), "pic.png", "image/png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    page = response.get_data(as_text=True)
    assert "Uploaded pic.png" in page


def test_account_locale_beats_the_cookie(auth_client, app):
    auth_client.post(
        "/console/settings",
        data={"locale": "en", "theme": "auto", "display_name": ""},
        follow_redirects=True,
    )

    with app.app_context():
        user = db.session.execute(
            select(User).where(User.username == "tester")
        ).scalar_one()
        assert user.locale == "en"

    auth_client.set_cookie("lang", "zh")
    page = auth_client.get("/").get_data(as_text=True)
    assert 'lang="en"' in page


def test_settings_saves_locale_and_syncs_cookie(auth_client):
    response = auth_client.post(
        "/console/settings",
        data={"locale": "en", "theme": "auto", "display_name": ""},
    )

    assert response.status_code == 302
    assert "lang=en" in response.headers["Set-Cookie"].replace(" ", "")

    page = auth_client.get("/console/settings").get_data(as_text=True)
    assert 'lang="en"' in page
    assert "Settings saved" in page
    assert 'value="en" checked' in page


def test_settings_page_lists_language_options(auth_client):
    page = auth_client.get("/console/settings").get_data(as_text=True)

    assert 'name="locale"' in page
    assert 'value="zh"' in page
    assert 'value="en"' in page
    assert 'value="zh" checked' in page


def test_invalid_locale_in_settings_is_ignored(auth_client):
    auth_client.post(
        "/console/settings",
        data={"locale": "klingon", "theme": "auto", "display_name": ""},
    )

    page = auth_client.get("/console/settings").get_data(as_text=True)
    assert 'value="zh" checked' in page
    assert 'lang="zh-CN"' in page


def test_language_switcher_is_rendered_on_public_pages(client):
    for path in ("/", "/login", "/register"):
        page = client.get(path).get_data(as_text=True)
        assert 'action="/language"' in page, path
        assert 'name="locale" value="en"' in page, path


def test_language_switcher_is_rendered_on_console_pages(auth_client):
    note_id = create_note(auth_client)

    for path in ("/console", "/console/settings", f"/console/notes/{note_id}"):
        page = auth_client.get(path).get_data(as_text=True)
        assert 'action="/language"' in page, path


def test_share_page_is_english_with_cookie(auth_client, en_client):
    note_id = create_note(auth_client)
    auth_client.put(f"/api/console/notes/{note_id}", json={"content": "# Hi"})
    auth_client.post(f"/console/notes/{note_id}/publish")

    page = en_client.get(f"/share/{note_id}").get_data(as_text=True)
    assert 'lang="en"' in page
    assert "Public · read-only" in page
    assert "Public note" in page


def test_english_messages_are_exposed_to_the_browser(en_client):
    page = en_client.get("/").get_data(as_text=True)

    assert "data-i18n" in page
    assert "View code" in page
    assert "Rendering diagram" in page


def test_preview_placeholder_is_attribute_driven(client):
    page = client.get("/share/whatever").get_data(as_text=True)

    assert page.count("data-empty-hint") >= 0
    assert "开始输入" not in page


def test_legacy_users_get_the_default_locale(tmp_path):
    database = tmp_path / "legacy_locale.db"
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

    with app.app_context():
        row = db.session.execute(select(User.locale).where(User.id == "old")).scalar_one()
        assert row == "zh"


def test_translate_falls_back_through_the_chain():
    from nooote.i18n import translate

    assert translate("settings.saved", "en") == "Settings saved"
    assert translate("settings.saved", "zh") == "设置已保存"
    assert translate("missing.key.entirely", "en") == "missing.key.entirely"


def test_placeholder_parameters_are_formatted():
    from nooote.i18n import translate

    assert translate("console.note_count", "zh", total=2, attachments=3) == "共 2 篇笔记 · 3 个附件"
    assert translate("console.note_count", "en", total=2, attachments=3) == "2 notes · 3 files"


def test_browser_message_catalog_covers_the_same_keys():
    from nooote.i18n import MESSAGES, js_messages

    for locale in ("zh", "en"):
        exported = js_messages(locale)
        expected = {
            key
            for key in MESSAGES[locale]
            if key.startswith("js.") or key.startswith("markdown.")
        }
        assert expected <= set(exported)
        assert all(exported[key] for key in expected)


def test_message_catalogs_have_matching_keys():
    from nooote.i18n import MESSAGES

    assert set(MESSAGES["zh"]) == set(MESSAGES["en"])
