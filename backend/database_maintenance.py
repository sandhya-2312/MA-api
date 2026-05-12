import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from backend.database import Base, SessionLocal, engine
from backend.models import Project, ProjectData, User, UserProject  # noqa: F401

logger = logging.getLogger(__name__)


def apply_database_migrations() -> None:
    base_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(base_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(base_dir / "alembic"))
    command.upgrade(alembic_cfg, "head")
    logger.info("Alembic migrations applied to head.")


def initialize_database_schema() -> None:
    Base.metadata.create_all(bind=engine, checkfirst=True)
    inspector = inspect(engine)
    table_names = sorted(inspector.get_table_names())
    logger.info("Database schema ensured. Tables present: %s.", ", ".join(table_names))


def summarize_database() -> dict[str, int]:
    db = SessionLocal()
    try:
        return {
            "users": db.query(User).count(),
            "projects": db.query(Project).count(),
            "user_project_assignments": db.query(UserProject).count(),
            "project_data_entries": db.query(ProjectData).count(),
        }
    finally:
        db.close()


def log_database_summary() -> dict[str, int]:
    summary = summarize_database()
    logger.info(
        "Database data summary: users=%s, projects=%s, assignments=%s, project_data_entries=%s.",
        summary["users"],
        summary["projects"],
        summary["user_project_assignments"],
        summary["project_data_entries"],
    )
    return summary
