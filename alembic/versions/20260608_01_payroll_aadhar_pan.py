"""add aadhar and pan to payroll employees

Revision ID: 20260608_01
Revises: 20260529_02
Create Date: 2026-06-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.migration_helpers import add_column_if_missing

revision: str = "20260608_01"
down_revision: Union[str, Sequence[str], None] = "20260529_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("payroll_employees", sa.Column("aadhar_number", sa.String(length=12), nullable=True))
    add_column_if_missing("payroll_employees", sa.Column("pan_number", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("payroll_employees", "pan_number")
    op.drop_column("payroll_employees", "aadhar_number")
