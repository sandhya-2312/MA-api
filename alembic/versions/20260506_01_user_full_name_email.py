"""add users.full_name and users.email

Revision ID: 20260506_01
Revises: 20260502_01
Create Date: 2026-05-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.migration_helpers import add_column_if_missing, create_index_if_missing

revision: str = "20260506_01"
down_revision: Union[str, Sequence[str], None] = "20260502_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("users", sa.Column("full_name", sa.String(length=255), nullable=True))
    add_column_if_missing("users", sa.Column("email", sa.String(length=255), nullable=True))
    create_index_if_missing("users", "ix_users_email", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "email")
    op.drop_column("users", "full_name")
