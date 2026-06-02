"""add monthly_salary to payroll employees

Revision ID: 20260529_02
Revises: 20260529_01
Create Date: 2026-05-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_02"
down_revision: Union[str, Sequence[str], None] = "20260529_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payroll_employees",
        sa.Column("monthly_salary", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("payroll_employees", "monthly_salary")
