import logging
import os
from dataclasses import dataclass

from sqlalchemy import func

from backend.database import SessionLocal
from backend.models import User
from backend.models.enums import UserRole
from backend.utils.password import hash_password, verify_password

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeploymentAccountSpec:
    env_username: str
    env_password: str
    role: UserRole
    env_first_login: str | None = None


DEPLOYMENT_ACCOUNT_SPECS: tuple[DeploymentAccountSpec, ...] = (
    DeploymentAccountSpec("INITIAL_ADMIN_USERNAME", "INITIAL_ADMIN_PASSWORD", UserRole.ADMIN, "INITIAL_ADMIN_FIRST_LOGIN"),
    DeploymentAccountSpec("INITIAL_USER_USERNAME", "INITIAL_USER_PASSWORD", UserRole.USER, "INITIAL_USER_FIRST_LOGIN"),
    DeploymentAccountSpec(
        "INITIAL_VIEWER_USERNAME",
        "INITIAL_VIEWER_PASSWORD",
        UserRole.VIEWER,
        "INITIAL_VIEWER_FIRST_LOGIN",
    ),
)


def _read_env_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def _read_first_login(env_name: str | None) -> bool:
    if not env_name:
        return False
    value = _read_env_value(env_name).lower()
    if not value:
        return False
    return value in {"1", "true", "yes", "on"}


def ensure_deployment_accounts() -> int:
    created = 0
    db = SessionLocal()
    try:
        for spec in DEPLOYMENT_ACCOUNT_SPECS:
            username = _read_env_value(spec.env_username)
            password = _read_env_value(spec.env_password)
            if not username or not password:
                logger.info(
                    "Deployment account seed skipped for %s: %s and %s are not both set.",
                    spec.role.value,
                    spec.env_username,
                    spec.env_password,
                )
                continue
            if len(password) < 8:
                logger.warning(
                    "Deployment account seed skipped for %s: %s must be at least 8 characters.",
                    spec.role.value,
                    spec.env_password,
                )
                continue

            existing_user = (
                db.query(User).filter(func.lower(User.username) == username.lower()).first()
            )
            if existing_user:
                if verify_password(password, existing_user.password_hash):
                    logger.info(
                        "Deployment account ready for %s: user %s already exists with the configured password.",
                        spec.role.value,
                        existing_user.username,
                    )
                else:
                    logger.warning(
                        "Deployment account exists for %s but %s does not match the stored password.",
                        existing_user.username,
                        spec.env_password,
                    )
                continue

            first_login = _read_first_login(spec.env_first_login)
            new_user = User(
                username=username,
                password_hash=hash_password(password),
                role=spec.role,
                first_login=first_login,
                contact_no=None,
            )
            db.add(new_user)
            db.flush()

            if not verify_password(password, new_user.password_hash):
                raise RuntimeError(f"Password verification failed for deployment user {username}.")

            created += 1
            logger.info(
                "Deployment account created for %s: user %s (first_login=%s).",
                spec.role.value,
                new_user.username,
                new_user.first_login,
            )

        if created:
            db.commit()
        return created
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def log_deployment_login_accounts() -> None:
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id).all()
        if not users:
            logger.warning("No login users exist in the database yet.")
            return

        for role in UserRole:
            role_users = [user for user in users if user.role == role]
            if not role_users:
                continue
            usernames = ", ".join(user.username for user in role_users)
            logger.info(
                "Deployment login accounts for %s: %s (first_login flags: %s).",
                role.value,
                usernames,
                ", ".join(f"{user.username}={user.first_login}" for user in role_users),
            )
    finally:
        db.close()
