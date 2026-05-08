"""
Optional dev seed — disabled by default (empty list).

Previously this recreated admin/operator/viewer on every run, which repopulated demo
accounts after you deleted them. To bootstrap a fresh database, use instead:

  python -m backend.create_initial_admin <username> <password>

If you really want scripted demo users again, add tuples to DEV_USERS below
(username, plain_password, UserRole) — not recommended for production.
"""

from backend.database import SessionLocal
from backend.models import User
from backend.models.enums import UserRole
from backend.utils.password import hash_password

# Intentionally empty so `python dev_start.py` / this module do not recreate operator/viewer/admin.
DEV_USERS: tuple[tuple[str, str, UserRole], ...] = ()


def seed() -> int:
    """Create or update users listed in DEV_USERS. Returns rows touched."""
    if not DEV_USERS:
        return 0
    db = SessionLocal()
    changed = 0
    try:
        for username, password, role in DEV_USERS:
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                existing.password_hash = hash_password(password)
                existing.role = role
                existing.first_login = True
                existing.contact_no = None
                changed += 1
                continue
            db.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    role=role,
                    first_login=True,
                    contact_no=None,
                )
            )
            changed += 1
        db.commit()
    finally:
        db.close()
    return changed


if __name__ == "__main__":
    n = seed()
    if not DEV_USERS:
        print("DEV_USERS is empty — no accounts were created or updated.")
        print("Create your first admin with: python -m backend.create_initial_admin <username> <password>")
    else:
        print(f"Reset {n} dev user record(s).")
