import logging
import os
import time
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import is_production

load_dotenv()

logger = logging.getLogger(__name__)


def _normalize_database_url(raw_url: str) -> str:
    url = raw_url.strip()
    if not url:
        raise ValueError("DATABASE_URL cannot be empty.")

    if url.startswith("postgres://"):
        url = f"postgresql+psycopg2://{url[len('postgres://'):]}"
    elif url.startswith("postgresql://"):
        url = f"postgresql+psycopg2://{url[len('postgresql://'):]}"

    parsed = make_url(url)
    if parsed.drivername != "postgresql+psycopg2":
        raise ValueError("DATABASE_URL must use the psycopg2 PostgreSQL driver.")

    return url


def normalize_database_url(raw_url: str) -> str:
    return _normalize_database_url(raw_url)


@lru_cache(maxsize=1)
def get_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_url:
        raise RuntimeError("DATABASE_URL is required.")
    return _normalize_database_url(raw_url)


def _build_connect_args(database_url: str) -> dict:
    connect_args: dict = {
        "connect_timeout": int(os.getenv("DATABASE_CONNECT_TIMEOUT", "10")),
    }

    sslmode = os.getenv("DATABASE_SSLMODE", "").strip()
    if not sslmode:
        host = (make_url(database_url).host or "").lower()
        if host.endswith(".render.com"):
            sslmode = "require"

    if sslmode:
        connect_args["sslmode"] = sslmode

    return connect_args


DATABASE_URL = get_database_url()

engine_kwargs: dict = {
    "connect_args": _build_connect_args(DATABASE_URL),
    "pool_pre_ping": True,
    "pool_recycle": int(os.getenv("DATABASE_POOL_RECYCLE", "300")),
    "pool_timeout": int(os.getenv("DATABASE_POOL_TIMEOUT", "30")),
}

if is_production():
    engine_kwargs["pool_size"] = int(os.getenv("DATABASE_POOL_SIZE", "5"))
    engine_kwargs["max_overflow"] = int(os.getenv("DATABASE_MAX_OVERFLOW", "2"))

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def check_database_connection(
    *,
    retries: int | None = None,
    retry_delay_seconds: float | None = None,
) -> tuple[bool, str | None]:
    if retries is None:
        retries = int(os.getenv("DATABASE_STARTUP_RETRIES", "5" if is_production() else "1"))
    if retry_delay_seconds is None:
        retry_delay_seconds = float(os.getenv("DATABASE_STARTUP_RETRY_DELAY_SECONDS", "3"))

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True, None
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                logger.warning(
                    "Database connection attempt %s/%s failed: %s. Retrying in %ss.",
                    attempt,
                    retries,
                    exc,
                    retry_delay_seconds,
                )
                time.sleep(retry_delay_seconds)

    return False, str(last_error) if last_error else "Database connection failed."


def verify_database_connection() -> None:
    connected, error = check_database_connection(retries=1, retry_delay_seconds=0)
    if not connected:
        raise RuntimeError(error or "Database connection failed.")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
