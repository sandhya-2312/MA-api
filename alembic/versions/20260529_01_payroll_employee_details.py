"""add payroll employee profile fields

Revision ID: 20260529_01
Revises: 20260525_01
Create Date: 2026-05-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from backend.migration_helpers import add_column_if_missing

revision: str = "20260529_01"
down_revision: Union[str, Sequence[str], None] = "20260525_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    add_column_if_missing("payroll_employees", sa.Column("contact_number", sa.String(length=20), nullable=True))
    add_column_if_missing("payroll_employees", sa.Column("email", sa.String(length=255), nullable=True))
    add_column_if_missing("payroll_employees", sa.Column("address", sa.String(length=500), nullable=True))
    add_column_if_missing("payroll_employees", sa.Column("project", sa.String(length=200), nullable=True))
    add_column_if_missing("payroll_employees", sa.Column("joining_date", sa.String(length=20), nullable=True))
    add_column_if_missing("payroll_employees", sa.Column("bank_name", sa.String(length=150), nullable=True))
    add_column_if_missing("payroll_employees", sa.Column("account_number", sa.String(length=50), nullable=True))
    add_column_if_missing("payroll_employees", sa.Column("ifsc_code", sa.String(length=20), nullable=True))
    add_column_if_missing("payroll_employees", sa.Column("upi_id", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("payroll_employees", "upi_id")
    op.drop_column("payroll_employees", "ifsc_code")
    op.drop_column("payroll_employees", "account_number")
    op.drop_column("payroll_employees", "bank_name")
    op.drop_column("payroll_employees", "joining_date")
    op.drop_column("payroll_employees", "project")
    op.drop_column("payroll_employees", "address")
    op.drop_column("payroll_employees", "email")
    op.drop_column("payroll_employees", "contact_number")
