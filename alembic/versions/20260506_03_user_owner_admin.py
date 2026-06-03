"""add users.created_by_admin_id for scoped member management

Revision ID: 20260506_03
Revises: 20260506_02
Create Date: 2026-05-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.migration_helpers import add_column_if_missing, has_foreign_key, has_index

revision: str = "20260506_03"
down_revision: Union[str, Sequence[str], None] = "20260506_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("users", sa.Column("created_by_admin_id", sa.Integer(), nullable=True))
    if not has_index("users", "ix_users_created_by_admin_id"):
        op.create_index("ix_users_created_by_admin_id", "users", ["created_by_admin_id"], unique=False)
    if not has_foreign_key("users", "fk_users_created_by_admin_id_users"):
        op.create_foreign_key(
            "fk_users_created_by_admin_id_users",
            "users",
            "users",
            ["created_by_admin_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    op.drop_constraint("fk_users_created_by_admin_id_users", "users", type_="foreignkey")
    op.drop_index("ix_users_created_by_admin_id", table_name="users")
    op.drop_column("users", "created_by_admin_id")
