import os

from dotenv import load_dotenv

load_dotenv()


def is_production() -> bool:
    environment = os.getenv("ENVIRONMENT", "").strip().lower()
    if environment in {"production", "prod"}:
        return True
    return os.getenv("RENDER", "").strip().lower() in {"true", "1", "yes"}


def get_secret_key() -> str:
    secret_key = os.getenv("SECRET_KEY", "").strip()
    if secret_key:
        return secret_key
    if is_production():
        raise RuntimeError("SECRET_KEY is required in production.")
    return "dev-only-secret-key"
