"""
Remove legacy demo accounts and optionally all projects (local data cleanup).

Usage (from MA-api directory):

  python -m backend.cleanup_demo_data
  python -m backend.cleanup_demo_data --wipe-all-projects
  python -m backend.cleanup_demo_data --remove-legacy-admin

By default deletes users named operator and viewer (old seed accounts).
"""

import argparse

from backend.database import SessionLocal
from backend.models import Project, User


DEMO_USERNAMES = frozenset({"operator", "viewer"})


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove demo users and optionally all projects.")
    parser.add_argument(
        "--wipe-all-projects",
        action="store_true",
        help="Delete every project (and related data via FK cascades).",
    )
    parser.add_argument(
        "--remove-legacy-admin",
        action="store_true",
        help="Also delete user with username 'admin' if present (old seed account).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        removed_users: list[str] = []
        for name in DEMO_USERNAMES:
            u = db.query(User).filter(User.username == name).first()
            if u:
                db.delete(u)
                removed_users.append(name)
        if args.remove_legacy_admin:
            leg = db.query(User).filter(User.username == "admin").first()
            if leg:
                db.delete(leg)
                removed_users.append("admin")

        removed_projects = 0
        if args.wipe_all_projects:
            for p in db.query(Project).all():
                db.delete(p)
                removed_projects += 1

        db.commit()
        if removed_users:
            print(f"Removed users: {', '.join(removed_users)}")
        else:
            print("No demo users (operator/viewer) found to remove.")
        if args.remove_legacy_admin and "admin" not in removed_users:
            print("No legacy 'admin' user found.")
        if args.wipe_all_projects:
            print(f"Removed {removed_projects} project(s).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
