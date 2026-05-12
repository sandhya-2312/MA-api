"""
Create the first admin user directly in the database (no API token).

Usage (from MA-api directory, after alembic upgrade head):

  python -m backend.create_initial_admin myadmin 'YourPassword8+'

Requires DATABASE_URL in .env. Password must be at least 8 characters.
"""

import argparse
import sys

from backend.database import SessionLocal
from backend.models import User
from backend.models.enums import UserRole
from backend.utils.password import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an admin user if the username is free.")
    parser.add_argument("username", help="Login username (unique)")
    parser.add_argument("password", help="Initial password (min 8 characters)")
    args = parser.parse_args()
    username = args.username.strip()
    password = args.password
    if len(username) < 1:
        print("Username cannot be empty.", file=sys.stderr)
        sys.exit(1)
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            print(f"User {username!r} already exists. Choose another username or delete that user first.", file=sys.stderr)
            sys.exit(1)
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
        print(f"Admin {username!r} created. Sign in and complete First Login Setup if prompted.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
