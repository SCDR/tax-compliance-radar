#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BACKEND_DIR}"

echo "[1/4] Sync dependencies"
uv sync

echo "[2/4] Initialize SQLite"
uv run python -m tax_compliance_radar.database.init_db

echo "[3/4] Initialize Chroma"
uv run python -m tax_compliance_radar.database.init_chroma

echo "[4/4] Load regulation markdowns (placeholder for dev/test)"
uv run python scripts/load_regulations.py --reset

echo "Done."
