"""add user email

Revision ID: 97a6d0084bfd
Revises: 0001_security_foundation
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "97a6d0084bfd"
down_revision: Union[str, None] = "0001_security_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "trustvault_users",
        sa.Column("email", sa.String(length=320), nullable=True),
    )
    op.create_index(
        "ix_trustvault_users_email",
        "trustvault_users",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_trustvault_users_email",
        table_name="trustvault_users",
    )
    op.drop_column("trustvault_users", "email")
