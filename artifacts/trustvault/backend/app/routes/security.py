
"""Protected identity, document-read, sharing, and account-role endpoints."""

from typing import Annotated, Literal
from uuid import UUID

from clerk_backend_api import Clerk
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.authorization import (
    can_manage_permissions,
    can_read,
    effective_document_role,
    load_document,
    record_audit,
)
from app.config import Settings, get_settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Document, DocumentPermission, User

router = APIRouter(prefix="/api", tags=["security"])

CurrentUser = Annotated[User, Depends(get_current_user)]
Database = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


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
    email: EmailStr
    access_level: Literal["read", "edit"]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class PermissionGrantResponse(BaseModel):
    user_id: UUID
    email: str | None = None
    access_level: Literal["read", "edit"]


class DocumentPermissionEntry(BaseModel):
    """One recipient who currently has document-scoped access."""

    user_id: UUID
    email: str | None = None
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document, role


def _find_verified_clerk_user(
    settings: Settings,
    email: str,
):
    """Find a Clerk user with this verified primary email."""
    try:
        with Clerk(
            bearer_auth=settings.clerk_secret_key.get_secret_value()
        ) as clerk:
            clerk_users = clerk.users.list(
                request={
                    "email_address": [email],
                    "limit": 10,
                }
            )
    except Exception as exc:
        # Avoid exposing Clerk errors or credentials to the API caller.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify the recipient with Clerk. Please try again.",
        ) from exc

    for clerk_user in clerk_users:
        primary_email_id = clerk_user.primary_email_address_id

        for address in clerk_user.email_addresses or []:
            verification = address.verification
            raw_status = getattr(verification, "status", None)
            verification_status = getattr(raw_status, "value", raw_status)

            if (
                address.id == primary_email_id
                and address.email_address.strip().lower() == email
                and str(verification_status).lower() == "verified"
            ):
                return clerk_user

    return None


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


@router.get("/documents/{document_id}", response_model=DocumentResponse)
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


@router.get(
    "/documents/{document_id}/permissions",
    response_model=list[DocumentPermissionEntry],
)
def list_document_permissions(
    document_id: UUID,
    user: CurrentUser,
    db: Database,
) -> list[DocumentPermissionEntry]:
    """List current recipients for a document. Owner or admin only."""
    document, _ = _managed_document(
        db,
        user,
        document_id,
        action="manage_permissions",
    )

    rows = db.execute(
        select(DocumentPermission, User)
        .join(User, DocumentPermission.user_id == User.id)
        .where(DocumentPermission.document_id == document.id)
        .order_by(DocumentPermission.created_at.asc(), DocumentPermission.id.asc())
    ).all()

    entries = [
        DocumentPermissionEntry(
            user_id=permission.user_id,
            email=recipient.email,
            access_level=permission.access_level,  # type: ignore[arg-type]
        )
        for permission, recipient in rows
    ]

    record_audit(
        db,
        actor=user,
        event_type="permission.list",
        outcome="success",
        resource_type="document",
        resource_id=str(document.id),
        details={"returned_count": len(entries)},
    )
    db.commit()
    return entries


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
    settings: AppSettings,
) -> PermissionGrantResponse:
    """Grant access to an existing TrustVault account by verified email."""
    document, _ = _managed_document(
        db,
        user,
        document_id,
        action="manage_permissions",
    )

    email = str(body.email).strip().lower()
    clerk_user = _find_verified_clerk_user(settings, email)

    if clerk_user is None:
        _deny_document_action(
            db,
            user,
            event_type="permission.grant.denied",
            document_id=document_id,
            action="recipient_email_not_verified",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verified Clerk account was found for that email.",
        )

    target = db.scalar(
        select(User).where(User.clerk_id == clerk_user.id)
    )

    if target is None:
        _deny_document_action(
            db,
            user,
            event_type="permission.grant.denied",
            document_id=document_id,
            action="recipient_not_registered_in_trustvault",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "This person hasn't signed in to TrustVault yet. "
                "Ask them to sign in first, then try again."
            ),
        )

    if target.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have access to your own document.",
        )

    # Persist the verified recipient email so owners can recognize grants later.
    # Never store Clerk secrets or session tokens on the user row.
    if target.email != email:
        target.email = email

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
        email=target.email,
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
