"""
Local development entrypoint: start FastAPI with reload.

Does not create or reset users. After a fresh database, run:

  python -m backend.create_initial_admin <username> <password>
"""

import os

import uvicorn


def main() -> None:
    host = os.getenv("BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "8000")))
    print("[dev-start] No automatic user seed. Use create_initial_admin if the database has no logins.")
    print(f"[dev-start] Starting API on http://{host}:{port}")
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
