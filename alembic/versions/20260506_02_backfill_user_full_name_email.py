"""backfill users.full_name and users.email from username where null

Revision ID: 20260506_02
Revises: 20260506_01
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

from backend.migration_helpers import has_table

revision: str = "20260506_02"
down_revision: Union[str, Sequence[str], None] = "20260506_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not has_table("users"):
        return

    # Existing rows created before full_name/email existed stay NULL until updated via the app.
    # Fill display-safe defaults so reporting / datasources are not all-null (users can edit in My Profile).
    op.execute(
        text(
            "UPDATE users SET full_name = username WHERE full_name IS NULL OR trim(full_name) = ''"
        )
    )
    op.execute(
        text(
            "UPDATE users SET email = lower(trim(username)) || '@maruthi.local' "
            "WHERE email IS NULL OR trim(email) = ''"
        )
    )


def downgrade() -> None:
    # Cannot reliably undo without storing previous null state; leave data as-is.
    pass
