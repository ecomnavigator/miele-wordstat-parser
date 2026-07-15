#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

git pull --ff-only
source .venv/bin/activate
python -m miele_wordstat.cli run-batch --limit "${1:-200}"
