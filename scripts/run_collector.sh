#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
qobserva-collector serve --host 127.0.0.1 --port 8080
