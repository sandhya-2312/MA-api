"""initial schema

Revision ID: 20260430_01
Revises:
Create Date: 2026-04-30 20:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from backend.migration_helpers import has_index, has_table


# revision identifiers, used by Alembic.
revision: str = "20260430_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not has_table("projects"):
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("parameters", sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_index("projects", op.f("ix_projects_id")):
        op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    if not has_index("projects", op.f("ix_projects_name")):
        op.create_index(op.f("ix_projects_name"), "projects", ["name"], unique=True)

    if not has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=100), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column(
                "role",
                sa.Enum("Admin", "User", "Viewer", name="user_role", native_enum=False),
                nullable=False,
            ),
            sa.Column("first_login", sa.Boolean(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_index("users", op.f("ix_users_id")):
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    if not has_index("users", op.f("ix_users_role")):
        op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    if not has_index("users", op.f("ix_users_username")):
        op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    if not has_table("project_data"):
        op.create_table(
            "project_data",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("value", sa.Float(), nullable=False),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_index("project_data", op.f("ix_project_data_id")):
        op.create_index(op.f("ix_project_data_id"), "project_data", ["id"], unique=False)

    if not has_table("user_projects"):
        op.create_table(
            "user_projects",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_index("user_projects", op.f("ix_user_projects_id")):
        op.create_index(op.f("ix_user_projects_id"), "user_projects", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_projects_id"), table_name="user_projects")
    op.drop_table("user_projects")
    op.drop_index(op.f("ix_project_data_id"), table_name="project_data")
    op.drop_table("project_data")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_projects_name"), table_name="projects")
    op.drop_index(op.f("ix_projects_id"), table_name="projects")
    op.drop_table("projects")
