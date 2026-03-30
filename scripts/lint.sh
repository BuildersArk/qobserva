#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
ruff check packages tests
