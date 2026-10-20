from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app import auth
from app.models import AuditEvent, DocumentPermission, User
from conftest import SecurityTestEnvironment


def test_new_verified_account_defaults_to_member(
    test_env: SecurityTestEnvironment,
) -> None:
    response = test_env.client.request("GET", "/api/me")

    assert response.status_code == 200
    assert response.json()["role"] == "member"
    with test_env.session_factory() as db:
        user = db.scalar(
            select(User).where(User.clerk_id == test_env.auth_context["clerk_id"])
        )
        assert user is not None
        assert user.role == "member"


def test_missing_clerk_session_is_401_and_audited(
    test_env: SecurityTestEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SignedOut:
        is_signed_in = False
        reason = SimpleNamespace(name="SESSION_TOKEN_MISSING")

    monkeypatch.setattr(auth, "authenticate_request", lambda *_args: SignedOut())
    # Remove only the test identity override so this request exercises Clerk's
    # production verification dependency with a missing session token.
    from app.main import app

    app.dependency_overrides.pop(auth.require_clerk_identity, None)
    response = test_env.client.request("GET", "/api/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"] == "SESSION_TOKEN_MISSING"
    assert any(
        event.event_type == "authentication.denied"
        and event.outcome == "denied"
        and event.actor_id is None
        for event in test_env.audit_events()
    )


def test_member_cannot_promote_self_to_admin(
    test_env: SecurityTestEnvironment,
) -> None:
    member_id = test_env.add_user("user-member")
    test_env.sign_in_as("user-member")

    response = test_env.client.request(
        "PATCH",
        f"/api/users/{member_id}/role",
        {"role": "admin"},
    )

    assert response.status_code == 403
    assert test_env.user(member_id).role == "member"  # type: ignore[union-attr]
    assert any(
        event.event_type == "user.role.change.denied"
        and event.outcome == "denied"
        for event in test_env.audit_events()
    )


def test_admin_can_change_server_stored_account_role(
    test_env: SecurityTestEnvironment,
) -> None:
    test_env.add_user("user-admin", role="admin")
    member_id = test_env.add_user("user-member")
    test_env.sign_in_as("user-admin")

    response = test_env.client.request(
        "PATCH",
        f"/api/users/{member_id}/role",
        {"role": "admin"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert test_env.user(member_id).role == "admin"  # type: ignore[union-attr]
    assert any(
        event.event_type == "user.role.changed"
        and event.outcome == "success"
        for event in test_env.audit_events()
    )


def test_non_owner_cannot_read_or_enumerate_documents(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("user-owner")
    test_env.add_user("user-outsider")
    document_id = test_env.add_document(owner_id, "Private plan.pdf")
    test_env.sign_in_as("user-outsider")

    unauthorized = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}",
    )
    guessed = test_env.client.request(
        "GET",
        f"/api/documents/{uuid4()}",
    )

    assert unauthorized.status_code == 404
    assert guessed.status_code == 404
    assert "Private plan.pdf" not in unauthorized.text
    denied_reads = [
        event
        for event in test_env.audit_events()
        if event.event_type == "document.read.denied"
    ]
    assert len(denied_reads) == 2
    assert all(event.outcome == "denied" for event in denied_reads)


def test_owner_grants_then_revokes_viewer_access_immediately(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("user-owner")
    viewer_id = test_env.add_user("user-viewer")
    document_id = test_env.add_document(owner_id)

    test_env.sign_in_as("user-owner")
    grant = test_env.client.request(
        "POST",
        f"/api/documents/{document_id}/permissions",
        {"user_id": str(viewer_id), "access_level": "read"},
    )
    assert grant.status_code == 201

    test_env.sign_in_as("user-viewer")
    allowed = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}",
    )
    assert allowed.status_code == 200
    assert allowed.json()["role"] == "viewer"

    test_env.sign_in_as("user-owner")
    revoked = test_env.client.request(
        "DELETE",
        f"/api/documents/{document_id}/permissions/{viewer_id}",
    )
    assert revoked.status_code == 204

    test_env.sign_in_as("user-viewer")
    denied = test_env.client.request(
        "GET",
        f"/api/documents/{document_id}",
    )
    assert denied.status_code == 404
    with test_env.session_factory() as db:
        grant_row = db.scalar(
            select(DocumentPermission).where(
                DocumentPermission.document_id == document_id,
                DocumentPermission.user_id == viewer_id,
            )
        )
        assert grant_row is None

    event_types = {event.event_type for event in test_env.audit_events()}
    assert "permission.granted" in event_types
    assert "document.read" in event_types
    assert "permission.revoked" in event_types
    assert "document.read.denied" in event_types


def test_viewer_cannot_grant_permissions(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("user-owner")
    viewer_id = test_env.add_user("user-viewer")
    target_id = test_env.add_user("user-target")
    document_id = test_env.add_document(owner_id)
    test_env.add_permission(document_id, viewer_id, owner_id, access_level="read")
    test_env.sign_in_as("user-viewer")

    response = test_env.client.request(
        "POST",
        f"/api/documents/{document_id}/permissions",
        {"user_id": str(target_id), "access_level": "read"},
    )

    assert response.status_code == 404
    assert any(
        event.event_type == "document.manage_permissions.denied"
        and event.outcome == "denied"
        for event in test_env.audit_events()
    )


def test_audit_rows_cannot_be_updated_or_deleted(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("user-owner")
    test_env.add_user("user-outsider")
    document_id = test_env.add_document(owner_id)
    test_env.sign_in_as("user-outsider")
    test_env.client.request("GET", f"/api/documents/{document_id}")

    event_id = test_env.audit_events()[0].id
    with test_env.session_factory() as db:
        audit_event = db.get(AuditEvent, event_id)
        assert audit_event is not None
        audit_event.outcome = "success"
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    with test_env.session_factory() as db:
        audit_event = db.get(AuditEvent, event_id)
        assert audit_event is not None
        db.delete(audit_event)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_invalid_account_role_is_rejected(
    test_env: SecurityTestEnvironment,
) -> None:
    response = test_env.client.request(
        "PATCH",
        f"/api/users/{uuid4()}/role",
        {"role": "superadmin"},
    )

    assert response.status_code == 422


def test_authenticated_user_can_read_own_profile(
    test_env: SecurityTestEnvironment,
) -> None:
    test_env.sign_in_as("user-1")

    response = test_env.client.request("GET", "/api/me")

    assert response.status_code == 200
    assert "role" in response.json()


def test_document_list_shows_only_authorized_documents(
    test_env: SecurityTestEnvironment,
) -> None:
    owner_id = test_env.add_user("list-owner")
    outsider_id = test_env.add_user("list-outsider")

    test_env.add_document(owner_id, "My document.pdf")
    test_env.add_document(outsider_id, "Private document.pdf")

    test_env.sign_in_as("list-owner")
    response = test_env.client.request("GET", "/api/documents")

    assert response.status_code == 200

    documents = response.json()
    names = [document["name"] for document in documents]

    assert "My document.pdf" in names
    assert "Private document.pdf" not in names
    assert all(
        "storage_key" not in document for document in documents
    )

    assert any(
        event.event_type == "document.list"
        and event.outcome == "success"
        for event in test_env.audit_events()
    )
