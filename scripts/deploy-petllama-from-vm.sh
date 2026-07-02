#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  echo "CLOUDFLARE_API_TOKEN is not set in this shell."
  echo "Run: export CLOUDFLARE_API_TOKEN='your-token'"
  exit 1
fi

echo "Pulling latest main..."
git pull --ff-only origin main

npm ci
npm test
npm run deploy

if [[ -x "manual-ripper/.venv/bin/python" ]]; then
  echo "Running Manual Ripper tests..."
  (cd manual-ripper && .venv/bin/python -m pytest tests/test_manual_guide.py)
else
  echo "Skipping Manual Ripper pytest: manual-ripper/.venv/bin/python not found."
fi

if systemctl list-unit-files daedalus-manual-ripper.service >/dev/null 2>&1; then
  echo "Restarting Manual Ripper service..."
  sudo systemctl restart daedalus-manual-ripper
  sudo systemctl --no-pager --lines=20 status daedalus-manual-ripper
else
  echo "Manual Ripper systemd service not found; skipping restart."
fi

echo "Worker health:"
curl -fsS https://petllama.martinbibb.workers.dev/health
printf '\n'

echo "Depot Notes diagnostic:"
curl -fsS https://petllama.martinbibb.workers.dev/depot-notes/debug
printf '\n'
