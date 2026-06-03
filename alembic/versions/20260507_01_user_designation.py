"""add users.designation

Revision ID: 20260507_01
Revises: 20260506_03
Create Date: 2026-05-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.migration_helpers import add_column_if_missing

revision: str = "20260507_01"
down_revision: Union[str, Sequence[str], None] = "20260506_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("users", sa.Column("designation", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "designation")
