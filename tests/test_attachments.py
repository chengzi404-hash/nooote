import io
import os

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32


def upload(client, data=PNG_BYTES, filename="pic.png", content_type="image/png"):
    return client.post(
        "/api/console/attachments",
        data={"file": (io.BytesIO(data), filename, content_type)},
        content_type="multipart/form-data",
    )


def test_upload_image_returns_markdown(auth_client):
    response = upload(auth_client)
    assert response.status_code == 201

    payload = response.get_json()
    assert payload["filename"] == "pic.png"
    assert payload["content_type"] == "image/png"
    assert payload["size"] == len(PNG_BYTES)
    assert payload["url"].startswith("/files/")
    assert payload["markdown"] == f"![pic.png]({payload['url']})"


def test_uploaded_image_is_served_inline(auth_client):
    payload = upload(auth_client).get_json()

    response = auth_client.get(payload["url"])
    assert response.status_code == 200
    assert response.data == PNG_BYTES
    assert response.mimetype == "image/png"
    assert "attachment" not in response.headers.get("Content-Disposition", "")


def test_non_image_attachment_is_downloaded(auth_client):
    response = upload(auth_client, b"hello", "notes.txt", "text/plain")
    payload = response.get_json()

    assert payload["content_type"] == "text/plain"
    assert payload["markdown"] == f"[notes.txt]({payload['url']})"

    served = auth_client.get(payload["url"])
    assert served.data == b"hello"
    assert served.mimetype == "application/octet-stream"
    assert "attachment" in served.headers["Content-Disposition"]


def test_svg_is_served_as_download(auth_client):
    payload = upload(auth_client, b"<svg/>", "diagram.svg", "image/svg+xml").get_json()

    assert payload["content_type"] == "image/svg+xml"
    assert payload["markdown"].startswith("[diagram.svg](")

    served = auth_client.get(payload["url"])
    assert served.mimetype == "application/octet-stream"
    assert "attachment" in served.headers["Content-Disposition"]


def test_upload_api_requires_login(client):
    response = upload(client)
    assert response.status_code == 401


def test_upload_requires_a_file(auth_client):
    response = auth_client.post(
        "/api/console/attachments", data={}, content_type="multipart/form-data"
    )
    assert response.status_code == 400


def test_empty_upload_is_rejected(auth_client):
    response = upload(auth_client, b"", "empty.png", "image/png")
    assert response.status_code == 400


def test_oversized_upload_is_rejected(auth_client):
    original = auth_client.application.config["MAX_UPLOAD_BYTES"]
    auth_client.application.config["MAX_UPLOAD_BYTES"] = 8
    try:
        response = upload(auth_client, b"123456789", "big.bin", "application/octet-stream")
        assert response.status_code == 413
    finally:
        auth_client.application.config["MAX_UPLOAD_BYTES"] = original


def test_filename_is_sanitized_and_escaped(auth_client):
    payload = upload(auth_client, PNG_BYTES, "../../a]b.png", "image/png").get_json()

    assert payload["filename"] == "a]b.png"
    assert payload["markdown"].startswith("![a\\]b.png](")


def test_attachments_page_form_upload(auth_client):
    response = auth_client.post(
        "/console/attachments",
        data={"file": (io.BytesIO(PNG_BYTES), "form.png", "image/png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200

    page = response.get_data(as_text=True)
    assert "form.png" in page
    assert "已上传 form.png" in page
    assert "/files/" in page


def test_attachments_page_lists_only_own_files(register_client):
    owner = register_client("owner")
    upload(owner, PNG_BYTES, "mine.png", "image/png")

    page = owner.get("/console/attachments").get_data(as_text=True)
    assert "mine.png" in page

    other = register_client("other")
    other_page = other.get("/console/attachments").get_data(as_text=True)
    assert "mine.png" not in other_page


def test_delete_attachment_removes_file(auth_client):
    payload = upload(auth_client).get_json()
    path = os.path.join(auth_client.application.config["UPLOAD_FOLDER"], payload["id"])
    assert os.path.exists(path)

    response = auth_client.delete(f"/api/console/attachments/{payload['id']}")
    assert response.status_code == 204

    assert auth_client.get(payload["url"]).status_code == 404
    assert not os.path.exists(path)


def test_delete_attachment_from_page(auth_client):
    payload = upload(auth_client).get_json()

    response = auth_client.post(
        f"/console/attachments/{payload['id']}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert "附件已删除" in response.get_data(as_text=True)
    assert auth_client.get(payload["url"]).status_code == 404


def test_cannot_delete_another_users_attachment(register_client):
    owner = register_client("owner")
    payload = upload(owner).get_json()

    other = register_client("other")
    assert other.delete(f"/api/console/attachments/{payload['id']}").status_code == 404
    assert owner.get(payload["url"]).status_code == 200


def test_attachments_are_public_by_link(auth_client, client):
    payload = upload(auth_client).get_json()

    assert client.get(payload["url"]).status_code == 200


def test_invalid_attachment_ids_are_rejected(auth_client, client):
    assert client.get("/files/short").status_code == 404
    assert client.get("/files/" + "a" * 17).status_code == 404
    assert client.delete("/api/console/attachments/short").status_code == 401
    assert auth_client.delete("/api/console/attachments/short").status_code == 404


def test_upload_without_extension_uses_provided_type(auth_client):
    payload = upload(auth_client, b"data", "blob", "application/x-thing").get_json()

    assert payload["content_type"] == "application/x-thing"
    assert payload["markdown"].startswith("[blob](")


def test_attachments_page_form_error_is_reported(auth_client):
    response = auth_client.post(
        "/console/attachments",
        data={},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "请选择要上传的文件" in response.get_data(as_text=True)


def test_missing_file_on_disk_returns_404(auth_client):
    payload = upload(auth_client).get_json()
    path = os.path.join(auth_client.application.config["UPLOAD_FOLDER"], payload["id"])
    os.remove(path)

    assert auth_client.get(payload["url"]).status_code == 404
