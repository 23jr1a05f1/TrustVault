from types import SimpleNamespace
from unittest.mock import MagicMock

from pydantic import SecretStr

from app.routes import security as security_routes


def make_settings():
    return SimpleNamespace(
        clerk_secret_key=SecretStr("sk_test_not_used")
    )


def make_clerk_user(
    email="viewer@example.com",
    status="verified",
    primary=True,
):
    address = SimpleNamespace(
        id="email-1",
        email_address=email,
        verification=SimpleNamespace(status=status),
    )
    return SimpleNamespace(
        id="clerk-viewer",
        primary_email_address_id=(
            "email-1" if primary else "another-email-id"
        ),
        email_addresses=[address],
    )


def mock_clerk(monkeypatch, users):
    client = MagicMock()
    client.__enter__.return_value = client
    client.users.list.return_value = users

    monkeypatch.setattr(
        security_routes,
        "Clerk",
        lambda **kwargs: client,
    )
    return client


def test_verified_primary_email_is_found(monkeypatch):
    clerk_user = make_clerk_user()
    mock_clerk(monkeypatch, [clerk_user])

    result = security_routes._find_verified_clerk_user(
        make_settings(),
        "viewer@example.com",
    )

    assert result is clerk_user


def test_unverified_email_is_rejected(monkeypatch):
    mock_clerk(
        monkeypatch,
        [make_clerk_user(status="unverified")],
    )

    result = security_routes._find_verified_clerk_user(
        make_settings(),
        "viewer@example.com",
    )

    assert result is None


def test_non_primary_email_is_rejected(monkeypatch):
    mock_clerk(
        monkeypatch,
        [make_clerk_user(primary=False)],
    )

    result = security_routes._find_verified_clerk_user(
        make_settings(),
        "viewer@example.com",
    )

    assert result is None


def test_different_email_is_rejected(monkeypatch):
    mock_clerk(
        monkeypatch,
        [make_clerk_user(email="other@example.com")],
    )

    result = security_routes._find_verified_clerk_user(
        make_settings(),
        "viewer@example.com",
    )

    assert result is None
