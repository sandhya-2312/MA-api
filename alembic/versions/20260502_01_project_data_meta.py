"""add project_data.meta for renewal line items

Revision ID: 20260502_01
Revises: 20260501_02
Create Date: 2026-05-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.migration_helpers import add_column_if_missing

revision: str = "20260502_01"
down_revision: Union[str, Sequence[str], None] = "20260501_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("project_data", sa.Column("meta", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("project_data", "meta")
