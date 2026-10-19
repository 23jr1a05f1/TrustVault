"""FastAPI dependencies shared by protected routes."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import AuthenticatedIdentity, require_clerk_identity
from app.config import Settings, get_settings
from app.database import get_db
from app.models import AuditEvent, User


def get_current_user(
    identity: Annotated[AuthenticatedIdentity, Depends(require_clerk_identity)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    """Provision a lowest-privilege local account from a verified Clerk ID."""
    user = db.scalar(select(User).where(User.clerk_id == identity.clerk_id))
    if user is None:
        role = (
            "admin"
            if identity.clerk_id in settings.bootstrap_admin_ids
            else "member"
        )
        user = User(clerk_id=identity.clerk_id, role=role)
        db.add(user)
        try:
            db.flush()
            if role == "admin":
                db.add(
                    AuditEvent(
                        actor_id=user.id,
                        event_type="user.role.bootstrap",
                        outcome="success",
                        resource_type="user",
                        resource_id=str(user.id),
                        details={"role": "admin"},
                    )
                )
            db.commit()
        except IntegrityError:
            # Two concurrent first requests can race on the unique Clerk ID.
            db.rollback()
            user = db.scalar(select(User).where(User.clerk_id == identity.clerk_id))
            if user is None:
                raise
    elif identity.clerk_id in settings.bootstrap_admin_ids and user.role != "admin":
        previous_role = user.role
        user.role = "admin"
        db.add(
            AuditEvent(
                actor_id=user.id,
                event_type="user.role.bootstrap",
                outcome="success",
                resource_type="user",
                resource_id=str(user.id),
                details={"previous_role": previous_role, "role": "admin"},
            )
        )
        db.commit()

    return user
