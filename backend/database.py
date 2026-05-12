import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import is_production

load_dotenv()


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


def _build_local_database_url() -> str:
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USERNAME", "postgres")
    db_password = os.getenv("DB_PASSWORD", "postgres")
    db_name = os.getenv("DB_DATABASE", "ma_db")
    return URL.create(
        "postgresql+psycopg2",
        username=db_user,
        password=db_password,
        host=db_host,
        port=int(db_port),
        database=db_name,
    ).render_as_string(hide_password=False)


@lru_cache(maxsize=1)
def get_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if raw_url:
        return _normalize_database_url(raw_url)

    if is_production():
        raise RuntimeError("DATABASE_URL is required in production.")

    return _normalize_database_url(_build_local_database_url())


DATABASE_URL = get_database_url()

engine_kwargs: dict = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

if is_production():
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 2

sslmode = os.getenv("DATABASE_SSLMODE", "").strip()
if sslmode:
    engine_kwargs["connect_args"] = {"sslmode": sslmode}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def verify_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
