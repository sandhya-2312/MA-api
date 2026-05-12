"""
Copy application data from one PostgreSQL database to another.

Usage:
  SOURCE_DATABASE_URL=postgresql://... TARGET_DATABASE_URL=postgresql://... python -m scripts.copy_application_data
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.database import normalize_database_url
from backend.models import Project, ProjectData, User, UserProject

load_dotenv()


def _session_for_url(database_url: str):
    engine = create_engine(normalize_database_url(database_url))
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _copy_rows(source_session, target_session, model, label: str) -> int:
    rows = source_session.query(model).order_by(model.id).all()
    copied = 0
    for row in rows:
        data = {
            column.name: getattr(row, column.name)
            for column in model.__table__.columns
            if column.name != "id"
        }
        target_session.merge(model(id=row.id, **data))
        copied += 1
    target_session.commit()
    print(f"Copied {copied} {label}.")
    return copied


def _reset_sequences(target_session) -> None:
    for table_name in ("users", "projects", "user_projects", "project_data"):
        target_session.execute(
            text(
                f"""
                SELECT setval(
                    pg_get_serial_sequence('{table_name}', 'id'),
                    COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                    (SELECT COUNT(*) > 0 FROM {table_name})
                )
                """
            )
        )
    target_session.commit()


def main() -> None:
    source_url = os.getenv("SOURCE_DATABASE_URL", "").strip()
    target_url = os.getenv("TARGET_DATABASE_URL", "").strip()
    if not source_url or not target_url:
        print("Set SOURCE_DATABASE_URL and TARGET_DATABASE_URL before running.", file=sys.stderr)
        sys.exit(1)

    source_session = _session_for_url(source_url)
    target_session = _session_for_url(target_url)
    try:
        _copy_rows(source_session, target_session, User, "users")
        _copy_rows(source_session, target_session, Project, "projects")
        _copy_rows(source_session, target_session, UserProject, "user-project assignments")
        _copy_rows(source_session, target_session, ProjectData, "project data entries")
        _reset_sequences(target_session)
        print("Application data copy completed.")
    finally:
        source_session.close()
        target_session.close()


if __name__ == "__main__":
    main()
