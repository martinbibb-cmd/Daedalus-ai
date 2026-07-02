#!/usr/bin/env bash
set -euo pipefail

AI_ROOT="${AI_SUPPORT_ROOT:-/srv/daedalus}"
ROOT="${MANUAL_RIPPER_STORAGE_ROOT:-$AI_ROOT/manuals}"
if [[ -n "${AI_SUPPORT_ROOT:-}" ]]; then
  DEFAULT_RAW_DIR="$ROOT/raw"
else
  DEFAULT_RAW_DIR="$ROOT/originals"
fi
RAW_DIR="${MANUAL_RIPPER_RAW_DIR:-$DEFAULT_RAW_DIR}"
EXTRACTED_DIR="${MANUAL_RIPPER_EXTRACTED_DIR:-$ROOT/extracted}"
FACTS_DIR="${MANUAL_RIPPER_FACTS_DIR:-$ROOT/facts}"
INDEXES_DIR="${MANUAL_RIPPER_INDEXES_DIR:-$ROOT/indexes}"
ASSETS_DIR="${MANUAL_RIPPER_ASSETS_DIR:-$ROOT/assets}"
DEPOT_EXAMPLES_DIR="${DEPOT_NOTES_EXAMPLES_DIR:-$AI_ROOT/depot-notes/examples}"
REGRESSIONS_DIR="${AI_REGRESSIONS_DIR:-$AI_ROOT/regressions}"
OWNER="${MANUAL_RIPPER_USER:-manual-ripper}"

sudo mkdir -p "$RAW_DIR" "$EXTRACTED_DIR" "$FACTS_DIR" "$INDEXES_DIR" "$ASSETS_DIR" "$DEPOT_EXAMPLES_DIR" "$REGRESSIONS_DIR"
if id "$OWNER" >/dev/null 2>&1; then
  sudo chown -R "$OWNER:$OWNER" "$ROOT" "$DEPOT_EXAMPLES_DIR" "$REGRESSIONS_DIR"
fi
sudo chmod -R 0750 "$ROOT" "$DEPOT_EXAMPLES_DIR" "$REGRESSIONS_DIR"
echo "Manual Ripper storage ready at $ROOT"
echo "Depot Notes examples ready at $DEPOT_EXAMPLES_DIR"
echo "Regression fixtures ready at $REGRESSIONS_DIR"
