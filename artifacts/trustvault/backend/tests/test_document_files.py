
from app.routes import documents as document_routes


def test_owner_can_upload_and_download_document(
    test_env, tmp_path, monkeypatch
):
    monkeypatch.setattr(document_routes, "STORAGE_DIR", tmp_path)

    test_env.add_user("document-owner")
    test_env.sign_in_as("document-owner")

    content = b"TrustVault private test document"

    upload_response = test_env.client.upload(
        "/api/documents",
        filename="private-note.txt",
        content=content,
        content_type="text/plain",
    )

    assert upload_response.status_code == 201, upload_response.text

    uploaded = upload_response.json()
    document_id = uploaded["id"]

    assert uploaded["name"] == "private-note.txt"
    assert uploaded["size_bytes"] == len(content)

    download_response = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/download",
    )

    assert download_response.status_code == 200, download_response.text
    assert download_response.content == content

    events = test_env.audit_events()

    assert any(
        event.event_type == "document.uploaded"
        and event.outcome == "success"
        for event in events
    )

    assert any(
        event.event_type == "document.downloaded"
        and event.outcome == "success"
        for event in events
    )


def test_other_user_cannot_download_private_document(
    test_env, tmp_path, monkeypatch
):
    monkeypatch.setattr(document_routes, "STORAGE_DIR", tmp_path)

    test_env.add_user("private-document-owner")
    test_env.sign_in_as("private-document-owner")

    upload_response = test_env.client.upload(
        "/api/documents",
        filename="secret.txt",
        content=b"Private information",
        content_type="text/plain",
    )

    assert upload_response.status_code == 201, upload_response.text
    document_id = upload_response.json()["id"]

    test_env.add_user("unauthorized-user")
    test_env.sign_in_as("unauthorized-user")

    response = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/download",
    )

    assert response.status_code == 404

    events = test_env.audit_events()

    assert any(
        event.event_type == "document.download.denied"
        and event.outcome == "denied"
        for event in events
    )


def test_oversized_upload_is_rejected(
    test_env, tmp_path, monkeypatch
):
    monkeypatch.setattr(document_routes, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(document_routes, "MAX_FILE_SIZE", 4)

    test_env.add_user("size-limit-owner")
    test_env.sign_in_as("size-limit-owner")

    response = test_env.client.upload(
        "/api/documents",
        filename="too-large.txt",
        content=b"12345",
        content_type="text/plain",
    )

    assert response.status_code == 413
    assert not list(tmp_path.iterdir())
