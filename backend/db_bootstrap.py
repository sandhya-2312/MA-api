import logging
import os

from sqlalchemy import func

from backend.database import Base, SessionLocal, engine
from backend.models import Project, ProjectData, User, UserProject  # noqa: F401
from backend.models.enums import UserRole
from backend.utils.password import hash_password

logger = logging.getLogger(__name__)


def initialize_database_schema() -> None:
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("Database schema ensured from SQLAlchemy models.")


def seed_initial_admin_user() -> bool:
    username = os.getenv("INITIAL_ADMIN_USERNAME", "").strip()
    password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
    if not username or not password:
        logger.info("Initial admin seed skipped: INITIAL_ADMIN_USERNAME or INITIAL_ADMIN_PASSWORD is not set.")
        return False
    if len(password) < 8:
        logger.warning("Initial admin seed skipped: INITIAL_ADMIN_PASSWORD must be at least 8 characters.")
        return False

    db = SessionLocal()
    try:
        admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if admin_exists:
            logger.info("Initial admin seed skipped: an admin user already exists.")
            return False

        username_taken = (
            db.query(User).filter(func.lower(User.username) == username.lower()).first()
        )
        if username_taken:
            logger.warning("Initial admin seed skipped: username %s already exists.", username)
            return False

        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
                first_login=True,
                contact_no=None,
            )
        )
        db.commit()
        logger.info("Initial admin user %s created.", username)
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def bootstrap_database() -> None:
    initialize_database_schema()
    seed_initial_admin_user()
