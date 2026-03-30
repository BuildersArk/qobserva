#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e packages/qobserva_agent -e packages/qobserva_collector
pip install pytest httpx ruff
python assemble_repo.py --check
echo "Bootstrap complete."
