import logging

from backend.database_maintenance import (
    apply_database_migrations,
    initialize_database_schema,
    log_database_summary,
)
from backend.deployment_accounts import ensure_deployment_accounts, log_deployment_login_accounts

logger = logging.getLogger(__name__)


def bootstrap_database() -> None:
    try:
        apply_database_migrations()
    except Exception:
        logger.exception("Alembic migration during bootstrap failed; continuing with schema ensure.")

    initialize_database_schema()
    created = ensure_deployment_accounts()
    log_deployment_login_accounts()
    log_database_summary()
    if created:
        logger.info("Deployment account bootstrap created %s user(s).", created)
