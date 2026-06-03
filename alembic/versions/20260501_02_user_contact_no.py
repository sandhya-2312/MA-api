"""add users.contact_no

Revision ID: 20260501_02
Revises: 20260430_01
Create Date: 2026-05-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.migration_helpers import add_column_if_missing

revision: str = "20260501_02"
down_revision: Union[str, Sequence[str], None] = "20260430_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("users", sa.Column("contact_no", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "contact_no")
