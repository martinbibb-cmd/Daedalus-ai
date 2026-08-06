#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sql_string(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def source_filename(entry: dict) -> str:
    return str(entry["manualSource"]).split(";", 1)[0].strip()


def candidate_id(entry: dict) -> str:
    return f"manual-candidate:xeon:{entry['id']}"


def build_sql(entries: list[dict], created_at: str) -> str:
    statements = ["BEGIN TRANSACTION;"]
    for entry in entries:
        filename = source_filename(entry)
        identity = candidate_id(entry)
        provenance = {
            "evidenceClass": "manual_evidence",
            "extractor": "xeon_manual_ripper_batch_v2",
            "manualSource": entry["manualSource"],
            "sourceEvidence": entry.get("provenance", []),
        }
        values = [
            identity,
            entry["applianceType"],
            entry["make"],
            entry["model"],
            entry["primitive"],
            json.dumps(entry["dimensions"], sort_keys=True, separators=(",", ":")),
            json.dumps(entry["clearanceMm"], sort_keys=True, separators=(",", ":")),
            json.dumps(provenance, sort_keys=True, separators=(",", ":")),
            "candidate",
            created_at,
            filename,
            identity,
        ]
        statements.append(
            "INSERT INTO manual_catalogue_candidates ("
            "candidate_id, manual_id, appliance_type, make, model, primitive, "
            "dimensions_json, clearance_json, provenance_json, review_status, created_at"
            ") SELECT "
            + ", ".join(sql_string(value) for value in values[:1])
            + ", manual_id, "
            + ", ".join(sql_string(value) for value in values[1:10])
            + " FROM manual_uploads WHERE source_filename = "
            + sql_string(values[10])
            + " AND NOT EXISTS (SELECT 1 FROM manual_catalogue_candidates WHERE candidate_id = "
            + sql_string(values[11])
            + ") LIMIT 1;"
        )
        report = json.dumps(
            {
                "extractor": "xeon_manual_ripper_batch_v2",
                "candidateCount": 1,
                "notes": "Measurements extracted from the uploaded manual and waiting for review.",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        statements.append(
            "UPDATE manual_uploads SET status = 'candidate_review_required', extraction_report_json = "
            + sql_string(report)
            + " WHERE source_filename = "
            + sql_string(filename)
            + ";"
        )
    statements.append("COMMIT;")
    return "\n".join(statements) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Generate safe D1 SQL for unreviewed manual candidates.")
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    entries = json.loads(args.candidates.read_text(encoding="utf-8"))
    created_at = datetime.now(timezone.utc).isoformat()
    args.output.write_text(build_sql(entries, created_at), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
