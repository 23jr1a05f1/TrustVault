"""Create TrustVault identity, document access, and audit tables."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_security_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trustvault_users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("clerk_id", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=16),
            server_default="member",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'member')",
            name="ck_trustvault_users_role",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trustvault_users"),
        sa.UniqueConstraint("clerk_id", name="uq_trustvault_users_clerk_id"),
    )

    op.create_table(
        "trustvault_documents",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("content_type", sa.String(length=150), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "size_bytes >= 0",
            name="ck_trustvault_documents_size",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["trustvault_users.id"],
            name="fk_trustvault_documents_owner_id_trustvault_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trustvault_documents"),
        sa.UniqueConstraint(
            "storage_key",
            name="uq_trustvault_documents_storage_key",
        ),
    )
    op.create_index(
        "ix_trustvault_documents_owner_id",
        "trustvault_documents",
        ["owner_id"],
    )

    op.create_table(
        "trustvault_document_permissions",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("document_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("granted_by_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("access_level", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "access_level IN ('read', 'edit')",
            name="ck_trustvault_permission_access_level",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["trustvault_documents.id"],
            name="fk_trustvault_permission_document",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["trustvault_users.id"],
            name="fk_trustvault_permission_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_id"],
            ["trustvault_users.id"],
            name="fk_trustvault_permission_granted_by",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_trustvault_document_permissions",
        ),
        sa.UniqueConstraint(
            "document_id",
            "user_id",
            name="uq_trustvault_permission_document_user",
        ),
    )
    op.create_index(
        "ix_trustvault_document_permissions_document_id",
        "trustvault_document_permissions",
        ["document_id"],
    )
    op.create_index(
        "ix_trustvault_document_permissions_user_id",
        "trustvault_document_permissions",
        ["user_id"],
    )

    op.create_table(
        "trustvault_audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "outcome IN ('success', 'denied')",
            name="ck_trustvault_audit_outcome",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["trustvault_users.id"],
            name="fk_trustvault_audit_actor",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trustvault_audit_events"),
    )
    op.create_index(
        "ix_trustvault_audit_events_actor_id",
        "trustvault_audit_events",
        ["actor_id"],
    )
    op.create_index(
        "ix_trustvault_audit_events_event_type",
        "trustvault_audit_events",
        ["event_type"],
    )
    op.create_index(
        "ix_trustvault_audit_events_created_at",
        "trustvault_audit_events",
        ["created_at"],
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION trustvault_reject_audit_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'TrustVault audit events are append-only';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trustvault_audit_events_immutable
            BEFORE UPDATE OR DELETE ON trustvault_audit_events
            FOR EACH ROW
            EXECUTE FUNCTION trustvault_reject_audit_mutation()
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trustvault_audit_events_immutable "
            "ON trustvault_audit_events"
        )
        op.execute("DROP FUNCTION IF EXISTS trustvault_reject_audit_mutation()")

    op.drop_index(
        "ix_trustvault_audit_events_created_at",
        table_name="trustvault_audit_events",
    )
    op.drop_index(
        "ix_trustvault_audit_events_event_type",
        table_name="trustvault_audit_events",
    )
    op.drop_index(
        "ix_trustvault_audit_events_actor_id",
        table_name="trustvault_audit_events",
    )
    op.drop_table("trustvault_audit_events")

    op.drop_index(
        "ix_trustvault_document_permissions_user_id",
        table_name="trustvault_document_permissions",
    )
    op.drop_index(
        "ix_trustvault_document_permissions_document_id",
        table_name="trustvault_document_permissions",
    )
    op.drop_table("trustvault_document_permissions")

    op.drop_index(
        "ix_trustvault_documents_owner_id",
        table_name="trustvault_documents",
    )
    op.drop_table("trustvault_documents")
    op.drop_table("trustvault_users")
