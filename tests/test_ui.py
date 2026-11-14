def test_home_page_banner_and_intro(client):
    page = client.get("/").get_data(as_text=True)

    assert "banner.svg" in page
    assert 'class="hero"' in page
    assert "为长期写作准备的编辑器" in page
    assert "免费创建账号" in page


def test_banner_asset_is_served(client):
    response = client.get("/static/banner.svg")

    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert b"<svg" in response.data


def test_console_shell_has_sidebar(auth_client):
    page = auth_client.get("/console").get_data(as_text=True)

    assert 'class="app-shell"' in page
    assert 'class="sidebar"' in page
    assert "图床与附件" in page
    assert "用户设置" in page
    assert "笔记概览" in page


def test_sidebar_stats_track_owned_notes(auth_client):
    auth_client.post("/console/notes")

    page = auth_client.get("/console").get_data(as_text=True)
    assert "共 1 篇笔记" in page


def test_styles_define_focus_and_page_motion(client):
    css = client.get("/static/style.css").get_data(as_text=True)

    assert "border-radius: 0" in css
    assert ":focus-visible" in css
    assert "@keyframes focus-ring" in css
    assert "@view-transition" in css
    assert "@keyframes page-in" in css


def test_code_copy_button_replaces_static_checks(client):
    script = client.get("/static/app.js").get_data(as_text=True)
    css = client.get("/static/style.css").get_data(as_text=True)

    assert "code-copy" in script
    assert "addCopyButtons" in script
    assert ".code-copy" in css
    assert "lint-check" not in script
    assert ".lint-check" not in css


def test_mermaid_blocks_toggle_between_diagram_and_code(client):
    script = client.get("/static/app.js").get_data(as_text=True)
    css = client.get("/static/style.css").get_data(as_text=True)

    assert "mermaid-block" in script
    assert "mermaid-toggle" in script
    assert "toggleMermaidView" in script
    assert "查看代码" in script
    assert "查看图表" in script
    assert ".mermaid-block" in css
    assert ".mermaid-toggle" in css
    assert '.mermaid-block[data-view="code"] .mermaid-source' in css


def test_editor_and_preview_scroll_in_sync(client):
    script = client.get("/static/app.js").get_data(as_text=True)

    assert "syncScroll" in script
    assert "scrollRatio" in script
    assert 'textarea.addEventListener("scroll"' in script
    assert 'preview.addEventListener("scroll"' in script
