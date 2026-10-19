"""Document-scoped access checks and append-only audit event writes."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditEvent, Document, DocumentPermission, User


def effective_document_role(
    db: Session,
    user: User,
    document: Document,
) -> str | None:
    """Resolve the user's role for this document from current database state."""
    if user.role == "admin":
        return "admin"
    if document.owner_id == user.id:
        return "owner"

    grant = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == user.id,
        )
    )
    if grant is None:
        return None
    return "editor" if grant.access_level == "edit" else "viewer"


def can_read(role: str | None) -> bool:
    return role in {"admin", "owner", "editor", "viewer"}


def can_manage_permissions(role: str | None) -> bool:
    return role in {"admin", "owner"}


def record_audit(
    db: Session,
    *,
    actor: User | None,
    event_type: str,
    outcome: str,
    resource_type: str,
    resource_id: str,
    details: dict[str, object] | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_id=actor.id if actor else None,
            event_type=event_type,
            outcome=outcome,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
    )


def load_document(db: Session, document_id: UUID) -> Document | None:
    return db.get(Document, document_id)
