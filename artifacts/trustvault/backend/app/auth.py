"""Clerk session verification for FastAPI requests."""

from dataclasses import dataclass
from typing import Annotated

from clerk_backend_api import AuthenticateRequestOptions, authenticate_request
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.authorization import record_audit
from app.database import get_db
from app.models import AuditEvent
from sqlalchemy.orm import Session

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """Identity taken from a verified Clerk session, never from request JSON."""

    clerk_id: str


def require_clerk_identity(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
    _credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ] = None,
) -> AuthenticatedIdentity:
    parties = settings.authorized_parties
    if not parties:
        record_audit(
            db,
            actor=None,
            event_type="authentication.denied",
            outcome="denied",
            resource_type="api",
            resource_id=request.url.path,
            details={"method": request.method, "reason": "origin_allowlist_missing"},
        )
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Authentication origin allowlist is not configured",
        )

    options = AuthenticateRequestOptions(
        secret_key=settings.clerk_secret_key.get_secret_value(),
        jwt_key=(
            settings.clerk_jwt_key.get_secret_value()
            if settings.clerk_jwt_key
            else None
        ),
        authorized_parties=parties,
        accepts_token=["session_token"],
    )
    state = authenticate_request(request, options)
    if not state.is_signed_in:
        reason = getattr(state.reason, "name", None) or "unauthorized"
        record_audit(
            db,
            actor=None,
            event_type="authentication.denied",
            outcome="denied",
            resource_type="api",
            resource_id=request.url.path,
            details={"method": request.method, "reason": reason},
        )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=reason,
            headers={"WWW-Authenticate": "Bearer"},
        )

    clerk_id = state.payload.get("sub")
    if not isinstance(clerk_id, str) or not clerk_id:
        record_audit(
            db,
            actor=None,
            event_type="authentication.denied",
            outcome="denied",
            resource_type="api",
            resource_id=request.url.path,
            details={"method": request.method, "reason": "invalid_session_subject"},
        )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail="invalid_session_subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthenticatedIdentity(clerk_id=clerk_id)
