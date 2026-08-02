#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


CAPTURE_FIELDS = (
    "id",
    "applianceType",
    "make",
    "model",
    "primitive",
    "dimensions",
    "clearanceMm",
    "manualSource",
)


def promote(candidates_path: Path, output_path: Path, approval_path: Path, approved_by: str) -> int:
    candidates = json.loads(candidates_path.read_text(encoding="utf-8"))
    promoted = []
    rejected = []
    for entry in candidates:
        missing = [field for field in CAPTURE_FIELDS if field not in entry]
        if missing:
            rejected.append({"id": entry.get("id"), "reason": "missing_fields", "fields": missing})
            continue
        if entry.get("reviewStatus") not in {"candidate", "approved"}:
            rejected.append({"id": entry.get("id"), "reason": "unsupported_review_status"})
            continue
        promoted.append({field: entry[field] for field in CAPTURE_FIELDS})

    output_path.parent.mkdir(parents=True, exist_ok=True)
    approval_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(promoted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    approval_path.write_text(
        json.dumps(
            {
                "approvedAt": datetime.now(timezone.utc).isoformat(),
                "approvedBy": approved_by,
                "source": str(candidates_path),
                "output": str(output_path),
                "promotedEntries": len(promoted),
                "rejectedEntries": rejected,
                "note": "Promotion records that a human accepted candidate extraction for Capture catalogue use.",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if promoted else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Promote reviewed manual-derived catalogue candidates.")
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--approved-by", required=True)
    args = parser.parse_args(argv)
    if not args.candidates.exists():
        print(f"candidate file does not exist: {args.candidates}", file=sys.stderr)
        return 2
    return promote(args.candidates, args.output, args.approval, args.approved_by)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

