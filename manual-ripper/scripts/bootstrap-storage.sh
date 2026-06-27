#!/usr/bin/env bash
set -euo pipefail

ROOT="${MANUAL_RIPPER_STORAGE_ROOT:-/srv/daedalus/manuals}"
OWNER="${MANUAL_RIPPER_USER:-manual-ripper}"

sudo mkdir -p "$ROOT/originals" "$ROOT/extracted" "$ROOT/indexes"
if id "$OWNER" >/dev/null 2>&1; then
  sudo chown -R "$OWNER:$OWNER" "$ROOT"
fi
sudo chmod -R 0750 "$ROOT"
echo "Manual Ripper storage ready at $ROOT"
