"""add payroll_modules and payroll_employees

Revision ID: 20260525_01
Revises: 20260507_01
Create Date: 2026-05-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260525_01"
down_revision: Union[str, Sequence[str], None] = "20260507_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payroll_modules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("company_name", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payroll_modules_id"), "payroll_modules", ["id"], unique=False)

    op.create_table(
        "payroll_employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.Column("serial_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("designation", sa.String(length=100), nullable=True),
        sa.Column("attendance", sa.JSON(), nullable=True),
        sa.Column("ot", sa.String(length=32), nullable=True),
        sa.Column("advance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("food", sa.Integer(), nullable=True),
        sa.Column("remarks", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["module_id"], ["payroll_modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payroll_employees_id"), "payroll_employees", ["id"], unique=False)
    op.create_index(op.f("ix_payroll_employees_module_id"), "payroll_employees", ["module_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payroll_employees_module_id"), table_name="payroll_employees")
    op.drop_index(op.f("ix_payroll_employees_id"), table_name="payroll_employees")
    op.drop_table("payroll_employees")
    op.drop_index(op.f("ix_payroll_modules_id"), table_name="payroll_modules")
    op.drop_table("payroll_modules")
