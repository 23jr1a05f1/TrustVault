"""Authorization and listing tests for document permission management."""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.routes import security as security_routes
from conftest import SecurityTestEnvironment


def test_owner_can_list_document_permissions(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("perm-owner", email="owner@example.com")
    viewer_id = test_env.add_user("perm-viewer", email="viewer@example.com")
    editor_id = test_env.add_user("perm-editor", email="editor@example.com")
    document_id = test_env.add_document(owner_id)
    test_env.add_permission(document_id, viewer_id, owner_id, access_level="read")
    test_env.add_permission(document_id, editor_id, owner_id, access_level="edit")

    test_env.sign_in_as("perm-owner")
    response = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/permissions",
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload) == 2

    by_user = {entry["user_id"]: entry for entry in payload}
    assert by_user[str(viewer_id)]["email"] == "viewer@example.com"
    assert by_user[str(viewer_id)]["access_level"] == "read"
    assert by_user[str(editor_id)]["email"] == "editor@example.com"
    assert by_user[str(editor_id)]["access_level"] == "edit"

    for entry in payload:
        assert "clerk_id" not in entry
        assert set(entry.keys()) == {"user_id", "email", "access_level"}

    assert any(
        event.event_type == "permission.list" and event.outcome == "success"
        for event in test_env.audit_events()
    )


def test_admin_can_list_document_permissions(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("doc-owner")
    test_env.add_user("doc-admin", role="admin")
    viewer_id = test_env.add_user("doc-viewer", email="viewer@example.com")
    document_id = test_env.add_document(owner_id)
    test_env.add_permission(document_id, viewer_id, owner_id, access_level="read")

    test_env.sign_in_as("doc-admin")
    response = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/permissions",
    )

    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert response.json()[0]["user_id"] == str(viewer_id)


def test_viewer_cannot_list_document_permissions(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("list-owner")
    viewer_id = test_env.add_user("list-viewer")
    document_id = test_env.add_document(owner_id)
    test_env.add_permission(document_id, viewer_id, owner_id, access_level="read")

    test_env.sign_in_as("list-viewer")
    response = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/permissions",
    )

    assert response.status_code == 404
    assert any(
        event.event_type == "document.manage_permissions.denied"
        and event.outcome == "denied"
        for event in test_env.audit_events()
    )


def test_outsider_cannot_list_or_guess_permissions(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("secret-owner")
    test_env.add_user("secret-outsider")
    document_id = test_env.add_document(owner_id)

    test_env.sign_in_as("secret-outsider")
    unauthorized = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/permissions",
    )
    guessed = test_env.client.request(
        "GET",
        f"/api/documents/{uuid4()}/permissions",
    )

    assert unauthorized.status_code == 404
    assert guessed.status_code == 404


def test_grant_by_email_then_list_and_revoke(
    test_env: SecurityTestEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_id = test_env.add_user("share-owner")
    viewer_id = test_env.add_user("share-viewer")
    document_id = test_env.add_document(owner_id)

    monkeypatch.setattr(
        security_routes,
        "_find_verified_clerk_user",
        lambda _settings, _email: SimpleNamespace(id="share-viewer"),
    )

    test_env.sign_in_as("share-owner")
    grant = test_env.client.request(
        "POST",
        f"/api/documents/{document_id}/permissions",
        {"email": "viewer@example.com", "access_level": "edit"},
    )
    assert grant.status_code == 201, grant.text
    assert grant.json()["user_id"] == str(viewer_id)
    assert grant.json()["email"] == "viewer@example.com"
    assert grant.json()["access_level"] == "edit"

    listed = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/permissions",
    )
    assert listed.status_code == 200, listed.text
    assert listed.json() == [
        {
            "user_id": str(viewer_id),
            "email": "viewer@example.com",
            "access_level": "edit",
        }
    ]

    revoked = test_env.client.request(
        "DELETE",
        f"/api/documents/{document_id}/permissions/{viewer_id}",
    )
    assert revoked.status_code == 204

    after_revoke = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/permissions",
    )
    assert after_revoke.status_code == 200
    assert after_revoke.json() == []


def test_viewer_cannot_revoke_permissions(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("rev-owner")
    viewer_id = test_env.add_user("rev-viewer")
    target_id = test_env.add_user("rev-target")
    document_id = test_env.add_document(owner_id)
    test_env.add_permission(document_id, viewer_id, owner_id, access_level="read")
    test_env.add_permission(document_id, target_id, owner_id, access_level="read")

    test_env.sign_in_as("rev-viewer")
    response = test_env.client.request(
        "DELETE",
        f"/api/documents/{document_id}/permissions/{target_id}",
    )

    assert response.status_code == 404
    assert any(
        event.event_type == "document.manage_permissions.denied"
        and event.outcome == "denied"
        for event in test_env.audit_events()
    )


def test_owner_lists_empty_permissions(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("empty-owner")
    document_id = test_env.add_document(owner_id)
    test_env.sign_in_as("empty-owner")

    response = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}/permissions",
    )

    assert response.status_code == 200
    assert response.json() == []
