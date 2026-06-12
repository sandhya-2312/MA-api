"""
Apply all Alembic migrations and ensure the schema matches the SQLAlchemy models.

Usage:
  DATABASE_URL=postgresql://... python -m scripts.setup_database
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from backend.database import verify_database_connection
from backend.database_maintenance import log_database_summary, prepare_database_for_deploy


def main() -> None:
    verify_database_connection()
    prepare_database_for_deploy()
    log_database_summary()
    print("Database setup complete.")


if __name__ == "__main__":
    main()
