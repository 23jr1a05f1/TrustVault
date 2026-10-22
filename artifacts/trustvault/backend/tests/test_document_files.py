
from types import SimpleNamespace

from app.routes import documents as document_routes
from app.routes import security as security_routes


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


def test_user_cannot_download_after_permission_is_revoked(
    test_env, tmp_path, monkeypatch
):
    monkeypatch.setattr(document_routes, "STORAGE_DIR", tmp_path)

    test_env.add_user("revocation-owner")
    viewer_id = test_env.add_user("revocation-viewer")

    # Simulate Clerk finding the viewer's verified email.
    monkeypatch.setattr(
        security_routes,
        "_find_verified_clerk_user",
        lambda _settings, _email: SimpleNamespace(
            id="revocation-viewer"
        ),
    )

    # Owner uploads a document.
    test_env.sign_in_as("revocation-owner")

    upload_response = test_env.client.upload(
        "/api/documents",
        filename="shared-note.txt",
        content=b"Confidential test document",
        content_type="text/plain",
    )

    assert upload_response.status_code == 201, upload_response.text
    document_id = upload_response.json()["id"]

    # Owner grants the viewer read permission using their email.
    grant_response = test_env.client.request(
        "POST",
        f"/api/documents/{document_id}/permissions",
        body={
            "email": "viewer@example.com",
            "access_level": "read",
        },
    )

    assert grant_response.status_code in (200, 201), grant_response.text

    # Viewer should be able to download the document.
    test_env.sign_in_as("revocation-viewer")

    allowed_response = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/download",
    )

    assert allowed_response.status_code == 200, allowed_response.text

    # Owner revokes the viewer's permission.
    test_env.sign_in_as("revocation-owner")

    revoke_response = test_env.client.request(
        "DELETE",
        f"/api/documents/{document_id}/permissions/{viewer_id}",
    )

    assert revoke_response.status_code == 204, revoke_response.text

    # Viewer must no longer be able to download the document.
    test_env.sign_in_as("revocation-viewer")

    denied_response = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/download",
    )

    assert denied_response.status_code == 404
