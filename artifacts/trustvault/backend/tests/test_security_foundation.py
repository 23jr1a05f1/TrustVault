
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app import auth
from app.main import app
from app.models import Document, DocumentPermission, User
from tests.conftest import SecurityTestEnvironment


def test_missing_clerk_session_is_401_and_audited(
    test_env: SecurityTestEnvironment,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SignedOut:
        is_signed_in = False
        reason = SimpleNamespace(name="SESSION_TOKEN_MISSING")

    monkeypatch.setattr(
        auth,
        "authenticate_request",
        lambda *_args, **_kwargs: SignedOut(),
    )

    # Save the existing override before removing it.
    original_override = app.dependency_overrides.pop(
        auth.require_clerk_identity, None
    )

    try:
        response = test_env.client.request("GET", "/api/me")

        assert response.status_code == 401
        assert any(
            event.event_type == "authentication.denied"
            and event.outcome == "denied"
            for event in test_env.audit_events()
        )
    finally:
        # Restore the override only if one existed.
        if original_override is not None:
            app.dependency_overrides[
                auth.require_clerk_identity
            ] = original_override


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
