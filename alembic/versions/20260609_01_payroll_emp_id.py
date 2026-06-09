"""add emp_id to payroll employees

Revision ID: 20260609_01
Revises: 20260608_01
Create Date: 2026-06-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.migration_helpers import add_column_if_missing

revision: str = "20260609_01"
down_revision: Union[str, Sequence[str], None] = "20260608_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("payroll_employees", sa.Column("emp_id", sa.String(length=5), nullable=True))


def downgrade() -> None:
    op.drop_column("payroll_employees", "emp_id")
