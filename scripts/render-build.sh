#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
pip install -r requirements.txt
python -c "from backend.database_maintenance import prepare_database_for_deploy; prepare_database_for_deploy()"
