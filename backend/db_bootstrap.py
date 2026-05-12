import logging
import os

from sqlalchemy import func

from backend.database import SessionLocal
from backend.database_maintenance import (
    apply_database_migrations,
    initialize_database_schema,
    log_database_summary,
)
from backend.models import User
from backend.models.enums import UserRole
from backend.utils.password import hash_password, verify_password

logger = logging.getLogger(__name__)


def _read_env_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def _read_initial_admin_credentials() -> tuple[str, str] | None:
    username = _read_env_value("INITIAL_ADMIN_USERNAME")
    password = _read_env_value("INITIAL_ADMIN_PASSWORD")
    if not username or not password:
        return None
    return username, password


def _count_users(db) -> tuple[int, int]:
    total_users = db.query(User).count()
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).count()
    return total_users, admin_users


def seed_initial_admin_user() -> bool:
    credentials = _read_initial_admin_credentials()
    if credentials is None:
        logger.warning(
            "Initial admin seed skipped: set INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD on the server."
        )
        return False

    username, password = credentials
    if len(password) < 8:
        logger.warning("Initial admin seed skipped: INITIAL_ADMIN_PASSWORD must be at least 8 characters.")
        return False

    logger.info("Initial admin seed requested for username %s.", username)

    db = SessionLocal()
    try:
        total_users, admin_users = _count_users(db)
        logger.info("Current user counts before seed: total=%s, admin=%s.", total_users, admin_users)

        existing_user = (
            db.query(User).filter(func.lower(User.username) == username.lower()).first()
        )
        if existing_user:
            if verify_password(password, existing_user.password_hash):
                logger.info(
                    "Initial admin seed skipped: user %s already exists with the configured password.",
                    existing_user.username,
                )
            else:
                logger.warning(
                    "Initial admin seed skipped: user %s already exists but does not match INITIAL_ADMIN_PASSWORD.",
                    existing_user.username,
                )
            return False

        if admin_users > 0:
            logger.info(
                "Creating configured initial admin %s even though %s admin user(s) already exist.",
                username,
                admin_users,
            )

        admin_user = User(
            username=username,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            first_login=True,
            contact_no=None,
        )
        db.add(admin_user)
        db.flush()

        if not verify_password(password, admin_user.password_hash):
            raise RuntimeError("Initial admin password verification failed after hashing.")

        db.commit()
        db.refresh(admin_user)
        logger.info(
            "Initial admin user %s created (id=%s, first_login=%s).",
            admin_user.username,
            admin_user.id,
            admin_user.first_login,
        )
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def log_login_user_status() -> None:
    db = SessionLocal()
    try:
        total_users, admin_users = _count_users(db)
        if total_users == 0:
            logger.warning(
                "No login users exist yet. Set INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD, then redeploy."
            )
            return

        admin_usernames = [
            user.username
            for user in db.query(User).filter(User.role == UserRole.ADMIN).order_by(User.id).all()
        ]
        logger.info(
            "Login users ready: total=%s, admin=%s, admin_usernames=%s.",
            total_users,
            admin_users,
            admin_usernames,
        )
    finally:
        db.close()


def bootstrap_database() -> None:
    try:
        apply_database_migrations()
    except Exception:
        logger.exception("Alembic migration during bootstrap failed; continuing with schema ensure.")

    initialize_database_schema()
    created = seed_initial_admin_user()
    log_login_user_status()
    log_database_summary()
    if created:
        logger.info("Initial admin bootstrap completed successfully.")
