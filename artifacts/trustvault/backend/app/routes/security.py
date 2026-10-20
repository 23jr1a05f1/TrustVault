
"""Protected identity, document-read, sharing, and account-role endpoints."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authorization import (
    can_manage_permissions,
    can_read,
    effective_document_role,
    load_document,
    record_audit,
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, DocumentPermission, User

router = APIRouter(prefix="/api", tags=["security"])

CurrentUser = Annotated[User, Depends(get_current_user)]
Database = Annotated[Session, Depends(get_db)]


class CurrentUserResponse(BaseModel):
    id: UUID
    role: Literal["admin", "member"]

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: UUID
    name: str
    category: str
    owner_id: UUID
    role: Literal["admin", "owner", "editor", "viewer"]


class PermissionGrantInput(BaseModel):
    user_id: UUID
    access_level: Literal["read", "edit"]


class PermissionGrantResponse(BaseModel):
    user_id: UUID
    access_level: Literal["read", "edit"]


class AccountRoleInput(BaseModel):
    role: Literal["admin", "member"]


def _deny_document_action(
    db: Session,
    actor: User,
    *,
    event_type: str,
    document_id: UUID,
    action: str,
) -> None:
    record_audit(
        db,
        actor=actor,
        event_type=event_type,
        outcome="denied",
        resource_type="document",
        resource_id=str(document_id),
        details={"action": action},
    )
    db.commit()


def _managed_document(
    db: Session,
    actor: User,
    document_id: UUID,
    *,
    action: str,
) -> tuple[Document, str]:
    document = load_document(db, document_id)

    role = (
        effective_document_role(db, actor, document)
        if document is not None
        else None
    )

    allowed = (
        can_manage_permissions(role)
        if action == "manage_permissions"
        else can_read(role)
    )

    if document is None or not allowed or role is None:
        _deny_document_action(
            db,
            actor,
            event_type=f"document.{action}.denied",
            document_id=document_id,
            action=action,
        )

        # Return the same response for missing and unauthorized documents.
        # This prevents users from discovering documents through their IDs.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document, role


@router.get("/me", response_model=CurrentUserResponse)
def get_me(user: CurrentUser) -> User:
    """Return the server-owned role for the authenticated account."""
    return user


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    user: CurrentUser,
    db: Database,
) -> list[DocumentResponse]:
    """List only documents the current user is allowed to read."""

    documents = db.scalars(
        select(Document).order_by(Document.created_at.desc())
    ).all()

    visible_documents: list[DocumentResponse] = []

    for document in documents:
        role = effective_document_role(db, user, document)

        if role is None or not can_read(role):
            continue

        visible_documents.append(
            DocumentResponse(
                id=document.id,
                name=document.name,
                category=document.category,
                owner_id=document.owner_id,
                role=role,  # type: ignore[arg-type]
            )
        )

    # FIX: record_audit requires resource_id.
    record_audit(
        db,
        actor=user,
        event_type="document.list",
        outcome="success",
        resource_type="document",
        resource_id="/api/documents",
        details={"returned_count": len(visible_documents)},
    )

    db.commit()
    return visible_documents


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
def read_document_metadata(
    document_id: UUID,
    user: CurrentUser,
    db: Database,
) -> DocumentResponse:
    """Return document metadata only when the user has read access."""

    document, role = _managed_document(
        db,
        user,
        document_id,
        action="read",
    )

    record_audit(
        db,
        actor=user,
        event_type="document.read",
        outcome="success",
        resource_type="document",
        resource_id=str(document.id),
    )

    db.commit()

    return DocumentResponse(
        id=document.id,
        name=document.name,
        category=document.category,
        owner_id=document.owner_id,
        role=role,  # type: ignore[arg-type]
    )


@router.post(
    "/documents/{document_id}/permissions",
    response_model=PermissionGrantResponse,
    status_code=status.HTTP_201_CREATED,
)
def grant_document_permission(
    document_id: UUID,
    body: PermissionGrantInput,
    user: CurrentUser,
    db: Database,
) -> PermissionGrantResponse:
    """Grant read or edit permission to another existing user."""

    document, _ = _managed_document(
        db,
        user,
        document_id,
        action="manage_permissions",
    )

    target = db.get(User, body.user_id)

    if target is None:
        _deny_document_action(
            db,
            user,
            event_type="permission.grant.denied",
            document_id=document_id,
            action="grant_to_unknown_user",
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    grant = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == target.id,
        )
    )

    if grant is None:
        grant = DocumentPermission(
            document_id=document.id,
            user_id=target.id,
            granted_by_id=user.id,
            access_level=body.access_level,
        )
        db.add(grant)
    else:
        grant.access_level = body.access_level
        grant.granted_by_id = user.id

    record_audit(
        db,
        actor=user,
        event_type="permission.granted",
        outcome="success",
        resource_type="document",
        resource_id=str(document.id),
        details={
            "target_user_id": str(target.id),
            "access_level": body.access_level,
        },
    )

    db.commit()

    return PermissionGrantResponse(
        user_id=target.id,
        access_level=body.access_level,
    )


@router.delete(
    "/documents/{document_id}/permissions/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_document_permission(
    document_id: UUID,
    target_user_id: UUID,
    user: CurrentUser,
    db: Database,
) -> Response:
    """Revoke an existing document permission."""

    document, _ = _managed_document(
        db,
        user,
        document_id,
        action="manage_permissions",
    )

    grant = db.scalar(
        select(DocumentPermission).where(
            DocumentPermission.document_id == document.id,
            DocumentPermission.user_id == target_user_id,
        )
    )

    if grant is None:
        _deny_document_action(
            db,
            user,
            event_type="permission.revoke.denied",
            document_id=document_id,
            action="revoke_missing_permission",
        )

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found",
        )

    db.delete(grant)

    record_audit(
        db,
        actor=user,
        event_type="permission.revoked",
        outcome="success",
        resource_type="document",
        resource_id=str(document.id),
        details={"target_user_id": str(target_user_id)},
    )

    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/users/{target_user_id}/role",
    response_model=CurrentUserResponse,
)
def change_account_role(
    target_user_id: UUID,
    body: AccountRoleInput,
    user: CurrentUser,
    db: Database,
) -> User:
    """Allow only administrators to change account roles."""

    if user.role != "admin":
        record_audit(
            db,
            actor=user,
            event_type="user.role.change.denied",
            outcome="denied",
            resource_type="user",
            resource_id=str(target_user_id),
            details={"requested_role": body.role},
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )

    target = db.get(User, target_user_id)

    if target is None:
        record_audit(
            db,
            actor=user,
            event_type="user.role.change.denied",
            outcome="denied",
            resource_type="user",
            resource_id=str(target_user_id),
            details={"reason": "unknown_user"},
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    previous_role = target.role
    target.role = body.role

    record_audit(
        db,
        actor=user,
        event_type="user.role.changed",
        outcome="success",
        resource_type="user",
        resource_id=str(target.id),
        details={
            "previous_role": previous_role,
            "role": body.role,
        },
    )

    db.commit()
    return target
