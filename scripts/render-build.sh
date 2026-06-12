#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
pip install -r requirements.txt
python -c "from backend.database_maintenance import initialize_database_schema; initialize_database_schema()"
python -m alembic upgrade head
