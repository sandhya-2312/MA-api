import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from backend.database import Base, SessionLocal, engine
from backend.models import PayrollEmployee, PayrollModule, Project, ProjectData, User, UserProject  # noqa: F401

logger = logging.getLogger(__name__)


def _alembic_config() -> Config:
    base_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(base_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(base_dir / "alembic"))
    return alembic_cfg


def reset_migration_history_if_base_tables_missing() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "users" in tables or "alembic_version" not in tables:
        return

    logger.warning("alembic_version exists but base tables are missing; resetting migration history.")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM alembic_version"))


def apply_database_migrations() -> None:
    reset_migration_history_if_base_tables_missing()
    command.upgrade(_alembic_config(), "head")
    logger.info("Alembic migrations applied to head.")


def prepare_database_for_deploy() -> None:
    apply_database_migrations()
    initialize_database_schema()


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
