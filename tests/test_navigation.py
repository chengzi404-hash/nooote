import pytest

from nooote.navigation import NavItem, console_nav, register_nav_item

PASSWORD = "password123"


def sidebar(page: str) -> str:
    start = page.index('class="sidebar-nav"')
    return page[start : page.index("</nav>", start)]


def set_role(app, username: str, role: str) -> None:
    from sqlalchemy import select

    from nooote.extensions import db
    from nooote.models import User

    with app.app_context():
        user = db.session.execute(
            select(User).where(User.username == username)
        ).scalar_one()
        user.role = role
        db.session.commit()


def test_member_sees_workspace_and_account_items(auth_client):
    nav = sidebar(auth_client.get("/console").get_data(as_text=True))

    assert "我的笔记" in nav
    assert "图床与附件" in nav
    assert "用户设置" in nav
    assert "返回首页" in nav
    assert "站点管理" not in nav


def test_admin_sees_manage_item(register_client, app):
    admin = register_client("boss")
    set_role(app, "boss", "admin")

    nav = sidebar(admin.get("/console").get_data(as_text=True))
    assert 'href="/manage"' in nav
    assert "站点管理" in nav


def test_active_item_follows_the_current_endpoint(auth_client):
    console = sidebar(auth_client.get("/console").get_data(as_text=True))
    assert 'data-nav="notes"' in console
    assert 'class="nav-link is-active" href="/console" data-nav="notes"' in console

    settings = sidebar(
        auth_client.get("/console/settings").get_data(as_text=True)
    )
    assert 'class="nav-link is-active" href="/console/settings" data-nav="settings"' in settings
    assert 'data-nav="settings"' in settings


def test_nav_counts_come_from_template_stats(auth_client):
    auth_client.post("/console/notes")

    nav = sidebar(auth_client.get("/console").get_data(as_text=True))
    assert '<span class="nav-count">1</span>' in nav


def test_custom_item_is_registered_after_create(app):
    register_nav_item(
        app,
        NavItem(
            key="custom",
            endpoint="console.index",
            label="console.my_notes",
            icon="fa-solid fa-puzzle-piece",
            order=15,
        ),
    )

    client = app.test_client()
    client.post(
        "/register",
        data={"username": "tester", "password": PASSWORD, "confirm": PASSWORD},
    )

    page = client.get("/console").get_data(as_text=True)
    nav = sidebar(page)
    assert 'data-nav="custom"' in nav
    assert '<i class="fa-solid fa-puzzle-piece"' in nav
    # Custom items are active on their endpoint alongside the built-in note link.
    assert 'is-active" href="/console" data-nav="custom"' in nav


def test_custom_item_hidden_without_permission(app):
    register_nav_item(
        app,
        NavItem(
            key="secret",
            endpoint="admin.manage",
            label="console.manage",
            icon="shield",
            permission="manage.view",
        ),
    )

    client = app.test_client()
    client.post(
        "/register",
        data={"username": "tester", "password": PASSWORD, "confirm": PASSWORD},
    )

    nav = sidebar(client.get("/console").get_data(as_text=True))
    assert 'data-nav="secret"' not in nav


def test_console_nav_sections_are_grouped(app):
    with app.test_request_context("/console"):
        sections = console_nav()

    assert [section["key"] for section in sections] == ["workspace", "account"]


def register_extra_items(app, count: int, endpoint: str = "console.settings") -> None:
    for index in range(count):
        register_nav_item(
            app,
            NavItem(
                key=f"extra{index}",
                endpoint=endpoint,
                label="console.settings",
                icon="settings",
            ),
        )


def test_excess_items_collapse_into_more_apps(app, register_client):
    register_extra_items(app, 3)
    client = register_client()

    nav = sidebar(client.get("/console").get_data(as_text=True))

    assert '<details class="nav-more">' in nav
    assert "更多应用" in nav
    assert '<span class="nav-more-count">1</span>' in nav
    assert nav.index('data-nav="extra2"') > nav.index('<details class="nav-more">')


def test_active_item_is_never_collapsed(app, register_client):
    register_extra_items(app, 3)
    client = register_client()

    nav = sidebar(client.get("/console/settings").get_data(as_text=True))

    assert '<details class="nav-more">' not in nav
    for index in range(3):
        assert f'data-nav="extra{index}"' in nav


def test_duplicate_nav_key_is_rejected(app):
    item = NavItem(
        key="notes",
        endpoint="console.index",
        label="console.my_notes",
        icon="notes",
    )
    with pytest.raises(ValueError):
        register_nav_item(app, item)


def test_unknown_permission_is_rejected(app):
    item = NavItem(
        key="bad",
        endpoint="console.index",
        label="console.my_notes",
        icon="notes",
        permission="note.teleport",
    )
    with pytest.raises(ValueError):
        register_nav_item(app, item)


def test_unknown_group_is_rejected(app):
    item = NavItem(
        key="bad",
        endpoint="console.index",
        label="console.my_notes",
        icon="notes",
        group="elsewhere",
    )
    with pytest.raises(ValueError):
        register_nav_item(app, item)


def test_unknown_endpoint_is_rejected(app):
    item = NavItem(
        key="bad",
        endpoint="console.missing",
        label="console.my_notes",
        icon="notes",
    )
    with pytest.raises(ValueError):
        register_nav_item(app, item)
