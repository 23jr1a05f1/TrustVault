"""Database models for users, document permissions, and audit events."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "trustvault_users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'member')",
            name="ck_trustvault_users_role",
        ),
        UniqueConstraint("clerk_id", name="uq_trustvault_users_clerk_id"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    clerk_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="member",
        server_default="member",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    owned_documents: Mapped[list["Document"]] = relationship(
        back_populates="owner",
        foreign_keys="Document.owner_id",
    )


class Document(Base):
    __tablename__ = "trustvault_documents"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_trustvault_documents_size"),
        UniqueConstraint("storage_key", name="uq_trustvault_documents_storage_key"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    owner_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("trustvault_users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    content_type: Mapped[str] = mapped_column(String(150), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    # This is a private storage locator, never a public or reusable download URL.
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped[User] = relationship(
        back_populates="owned_documents",
        foreign_keys=[owner_id],
    )
    permissions: Mapped[list["DocumentPermission"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentPermission(Base):
    __tablename__ = "trustvault_document_permissions"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "user_id",
            name="uq_trustvault_permission_document_user",
        ),
        CheckConstraint(
            "access_level IN ('read', 'edit')",
            name="ck_trustvault_permission_access_level",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    document_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("trustvault_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("trustvault_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    granted_by_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("trustvault_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    access_level: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped[Document] = relationship(back_populates="permissions")


class AuditEvent(Base):
    __tablename__ = "trustvault_audit_events"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success', 'denied')",
            name="ck_trustvault_audit_outcome",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    actor_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("trustvault_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Keep this as text and do not add a foreign key: audit history must survive
    # deletion of the corresponding resource.
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
