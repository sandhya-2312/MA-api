import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from backend.database import verify_database_connection
from backend.routers import auth, dashboard, projects, users

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        verify_database_connection()
        logger.info("Database connection verified.")
    except Exception:
        logger.exception("Database connection failed during startup.")
        raise
    yield


app = FastAPI(title="MA Backend API", version="1.0.0", lifespan=lifespan)

frontend_origins = os.getenv("FRONTEND_ORIGINS")
frontend_origin_regex = os.getenv(
    "FRONTEND_ORIGIN_REGEX",
    r"^https?://([a-z0-9-]+\.vercel\.app|localhost|127\.0\.0\.1)(:\d+)?$",
)
allow_all_origins = os.getenv("ALLOW_ALL_ORIGINS", "false").lower() == "true"
allowed_origins = (
    [origin.strip() for origin in frontend_origins.split(",") if origin.strip()]
    if frontend_origins
    else [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5173",
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else allowed_origins,
    allow_origin_regex=frontend_origin_regex,
    allow_credentials=False if allow_all_origins else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"message": "MA FastAPI backend is running"}


@app.get("/health")
def health():
    verify_database_connection()
    return {"status": "ok", "database": "connected"}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
