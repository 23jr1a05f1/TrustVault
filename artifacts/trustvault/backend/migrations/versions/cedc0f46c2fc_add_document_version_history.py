
"""Add document version history.

Revision ID: cedc0f46c2fc
Revises: 97a6d0084bfd
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cedc0f46c2fc"
down_revision: Union[str, None] = "97a6d0084bfd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trustvault_document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=150), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_number >= 1",
            name="ck_trustvault_document_version_number",
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name="ck_trustvault_document_version_size",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["trustvault_documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_id"],
            ["trustvault_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_trustvault_document_version_number",
        ),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_trustvault_document_version_storage_key",
        ),
    )

    op.create_index(
        "ix_trustvault_document_versions_document_id",
        "trustvault_document_versions",
        ["document_id"],
        unique=False,
    )

    # Create version 1 for every existing document.
    # Keep the existing file in place.
    op.execute(
        sa.text(
            """
            INSERT INTO trustvault_document_versions (
                id,
                document_id,
                version_number,
                storage_key,
                content_type,
                size_bytes,
                uploaded_by_id,
                created_at
            )
            SELECT
                id,
                id,
                1,
                storage_key,
                content_type,
                size_bytes,
                owner_id,
                created_at
            FROM trustvault_documents
            """
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_trustvault_document_versions_document_id",
        table_name="trustvault_document_versions",
    )
    op.drop_table("trustvault_document_versions")
