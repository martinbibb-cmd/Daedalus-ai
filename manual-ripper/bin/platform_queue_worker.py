#!/usr/bin/env python3
"""Process queued Platform manuals through the private Xeon ripper."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import requests

import manual_catalogue_ripper


PLATFORM_BASE_URL = os.getenv("DAEDALUS_PLATFORM_BASE_URL", "https://api.daedalus-app.com").rstrip("/")
LOCAL_RIPPER_BASE_URL = os.getenv("MANUAL_RIPPER_LOCAL_URL", "http://127.0.0.1:8791").rstrip("/")
STORAGE_ROOT = Path(os.getenv("MANUAL_RIPPER_STORAGE_ROOT", "/srv/daedalus/manuals"))
ORIGINALS_DIR = Path(os.getenv("MANUAL_RIPPER_RAW_DIR", str(STORAGE_ROOT / "originals")))
STATE_DB = Path(os.getenv("MANUAL_RIPPER_BRIDGE_DB", str(STORAGE_ROOT / "platform-bridge.sqlite")))
MAX_MANUAL_BYTES = int(os.getenv("MANUAL_RIPPER_MAX_UPLOAD_BYTES", str(30 * 1024 * 1024)))
MAX_JOBS_PER_RUN = int(os.getenv("MANUAL_RIPPER_BRIDGE_MAX_JOBS", "4"))


def required_env(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(f"required bridge setting is missing: {name}")
    return value


def platform_headers() -> dict[str, str]:
    return {
        "CF-Access-Client-Id": required_env("CF_ACCESS_CLIENT_ID"),
        "CF-Access-Client-Secret": required_env("CF_ACCESS_CLIENT_SECRET"),
        "X-Daedalus-Manual-Ripper-Key": required_env("MANUAL_RIPPER_BRIDGE_KEY"),
    }


def ensure_state() -> None:
    STATE_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(STATE_DB) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS platform_manual_jobs (
              platform_manual_id TEXT PRIMARY KEY,
              local_manual_id TEXT NOT NULL,
              source_filename TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              completed_at TEXT
            )
            """
        )


def existing_local_manual(platform_manual_id: str) -> str | None:
    ensure_state()
    with sqlite3.connect(STATE_DB) as connection:
        row = connection.execute(
            "SELECT local_manual_id FROM platform_manual_jobs WHERE platform_manual_id = ?",
            (platform_manual_id,),
        ).fetchone()
    return str(row[0]) if row else None


def record_local_manual(
    platform_manual_id: str, local_manual_id: str, source_filename: str, digest: str
) -> None:
    ensure_state()
    with sqlite3.connect(STATE_DB) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO platform_manual_jobs (
              platform_manual_id, local_manual_id, source_filename, sha256, completed_at
            ) VALUES (?, ?, ?, ?, NULL)
            """,
            (platform_manual_id, local_manual_id, source_filename, digest),
        )


def mark_completed(platform_manual_id: str) -> None:
    with sqlite3.connect(STATE_DB) as connection:
        connection.execute(
            "UPDATE platform_manual_jobs SET completed_at = datetime('now') WHERE platform_manual_id = ?",
            (platform_manual_id,),
        )


def upload_to_private_ripper(source_filename: str, content: bytes) -> str:
    response = requests.post(
        f"{LOCAL_RIPPER_BASE_URL}/manuals/upload",
        files={"file": (source_filename, content, "application/pdf")},
        timeout=90,
    )
    response.raise_for_status()
    local_manual_id = str(response.json()["manual"]["id"])
    extract = requests.post(
        f"{LOCAL_RIPPER_BASE_URL}/manuals/{quote(local_manual_id, safe='')}/extract",
        timeout=300,
    )
    extract.raise_for_status()
    return local_manual_id


def submit_failure(platform_manual_id: str, reason: str) -> None:
    requests.post(
        f"{PLATFORM_BASE_URL}/manual-ripper/jobs/{quote(platform_manual_id, safe='')}/failure",
        headers=platform_headers(),
        json={"reason": reason[:500]},
        timeout=60,
    ).raise_for_status()


def process_one() -> bool:
    response = requests.get(
        f"{PLATFORM_BASE_URL}/manual-ripper/jobs/next",
        headers=platform_headers(),
        timeout=90,
    )
    if response.status_code == 204:
        return False
    response.raise_for_status()

    platform_manual_id = unquote(response.headers.get("x-daedalus-manual-id", ""))
    source_filename = unquote(response.headers.get("x-daedalus-source-filename", ""))
    if not platform_manual_id or not source_filename:
        raise RuntimeError("Platform bridge response omitted manual identity headers")
    content = response.content
    if len(content) < 4 or content[:4] != b"%PDF":
        submit_failure(platform_manual_id, "Queued object is not a valid PDF.")
        return True
    if len(content) > MAX_MANUAL_BYTES:
        submit_failure(platform_manual_id, "Queued PDF exceeds the private ripper upload limit.")
        return True

    try:
        local_manual_id = existing_local_manual(platform_manual_id)
        if not local_manual_id:
            local_manual_id = upload_to_private_ripper(source_filename, content)
            record_local_manual(
                platform_manual_id,
                local_manual_id,
                source_filename,
                hashlib.sha256(content).hexdigest(),
            )
        original = ORIGINALS_DIR / f"{local_manual_id}.pdf"
        if not original.is_file():
            raise RuntimeError("Private ripper original is missing for the claimed Platform job")

        candidates, report = manual_catalogue_ripper.parse_manual_candidates(
            original, source_filename
        )
        result = requests.post(
            f"{PLATFORM_BASE_URL}/manual-ripper/jobs/{quote(platform_manual_id, safe='')}/result",
            headers=platform_headers(),
            json={"candidates": candidates, "report": report},
            timeout=90,
        )
        result.raise_for_status()
        mark_completed(platform_manual_id)
        return True
    except Exception as error:
        submit_failure(platform_manual_id, f"Private deterministic extraction failed: {error}")
        raise


def main() -> int:
    try:
        processed = 0
        while processed < MAX_JOBS_PER_RUN and process_one():
            processed += 1
        print(json.dumps({"processed": processed, "status": "ok"}))
        return 0
    except Exception as error:
        print(json.dumps({"processed": 0, "status": "failed", "error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
