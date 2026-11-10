def test_index_page_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Nooote" in response.get_data(as_text=True)


def test_visiting_note_creates_it(client):
    response = client.get("/world/hello")
    assert response.status_code == 200

    data = client.get("/api/world/hello").get_json()
    assert data["id"] == "hello"
    assert data["content"] == ""


def test_save_note_and_reload(client):
    content = "# 标题\n\n- 一\n- 二\n\n`code`"
    response = client.put("/api/world/hello", json={"content": content})
    assert response.status_code == 200
    assert response.get_json()["length"] == len(content)

    data = client.get("/api/world/hello").get_json()
    assert data["content"] == content

    page = client.get("/world/hello").get_data(as_text=True)
    assert content in page
    assert 'data-preview aria-label="Markdown 预览"></article>' in page
    assert "<h1>标题</h1>" not in page


def test_note_page_loads_client_renderers(client):
    page = client.get("/world/client").get_data(as_text=True)

    assert "vendor/marked.min.js" in page
    assert "vendor/purify.min.js" in page
    assert "vendor/highlight.min.js" in page
    assert "vendor/katex/katex.min.js" in page
    assert "vendor/katex/katex.min.css" in page
    assert "vendor/mermaid/mermaid.min.js" in page
    assert "vendor/lezer-checks.js" in page
    assert "vendor/ruby-checks.js" in page
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


def test_server_preview_endpoint_removed(client):
    response = client.post("/api/preview", json={"markdown": "# hi"})
    assert response.status_code == 404


def test_invalid_note_ids_are_rejected(client):
    assert client.get("/world/bad%20id").status_code == 404
    assert client.get("/api/world/bad%20id").status_code == 400
    assert client.put("/api/world/bad%20id", json={"content": "x"}).status_code == 400


def test_save_requires_json_content(client):
    response = client.put("/api/world/hello", data="x", content_type="text/plain")
    assert response.status_code == 400

    response = client.put("/api/world/hello", json={})
    assert response.status_code == 400


def test_world_lookup_redirects(client):
    response = client.get("/world?id=my-note")
    assert response.status_code == 302
    assert "/world/my-note" in response.headers["Location"]

    response = client.get("/world?id=bad%20id")
    assert response.headers["Location"] == "/"


def test_unicode_note_id(client):
    response = client.put("/api/world/中文笔记", json={"content": "你好"})
    assert response.status_code == 200
    assert client.get("/api/world/中文笔记").get_json()["content"] == "你好"


def test_security_headers(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers
    assert "wasm-unsafe-eval" in response.headers["Content-Security-Policy"]
    assert "style-src 'self' 'unsafe-inline'" in response.headers["Content-Security-Policy"]
    assert "font-src 'self'" in response.headers["Content-Security-Policy"]
