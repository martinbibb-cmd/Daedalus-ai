#!/usr/bin/env python3
"""Publish finalized Manual Ripper results to an immutable NAS run directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone


DEFAULT_SOURCE_ROOT = Path("/srv/daedalus/manuals")
DEFAULT_NAS_ROOT = Path("/mnt/daedalus-nas/Manuals/Results/manual-ripper")
NAS_MOUNT = Path("/mnt/daedalus-nas")
PUBLISHABLE_FILES = (
    Path("reviewed/manual-derived-van-stock.json"),
    Path("reviewed/manual-derived-van-stock.approval.json"),
    Path("reviewed/manual-derived-van-stock.platform.sql"),
    Path("output/manual-ripper-report.json"),
)
REQUIRED_FILES = (
    Path("reviewed/manual-derived-van-stock.json"),
    Path("reviewed/manual-derived-van-stock.approval.json"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish reviewed Manual Ripper outputs to immutable NAS storage."
    )
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--nas-root", type=Path, default=DEFAULT_NAS_ROOT)
    parser.add_argument(
        "--run-id",
        default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
    )
    parser.add_argument(
        "--allow-non-mounted-target",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_commit() -> str:
    repository = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def validate_run_id(run_id: str) -> None:
    if not run_id or any(character not in "0123456789TZ-" for character in run_id):
        raise ValueError("run-id must contain only digits, T, Z, or hyphens")


def validate_target(nas_root: Path, allow_non_mounted_target: bool) -> None:
    if allow_non_mounted_target:
        return
    resolved_root = nas_root.resolve(strict=False)
    resolved_mount = NAS_MOUNT.resolve(strict=False)
    if resolved_mount not in resolved_root.parents:
        raise ValueError(f"NAS result root must be below {NAS_MOUNT}")
    if not os.path.ismount(resolved_mount):
        raise RuntimeError(f"NAS mount is unavailable at {NAS_MOUNT}")


def publish(args: argparse.Namespace) -> Path:
    validate_run_id(args.run_id)
    source_root = args.source_root.resolve(strict=True)
    nas_root = args.nas_root.resolve(strict=False)
    validate_target(nas_root, args.allow_non_mounted_target)

    missing = [str(path) for path in REQUIRED_FILES if not (source_root / path).is_file()]
    if missing:
        raise FileNotFoundError(
            "required reviewed result files are missing: " + ", ".join(missing)
        )

    nas_root.mkdir(parents=True, exist_ok=True, mode=0o755)
    nas_root.chmod(0o755)
    final_directory = nas_root / args.run_id
    staging_directory = nas_root / f".staging-{args.run_id}-{os.getpid()}"
    if final_directory.exists():
        raise FileExistsError(f"published run already exists: {final_directory}")
    if staging_directory.exists():
        raise FileExistsError(f"staging directory already exists: {staging_directory}")

    manifest_files: list[dict[str, object]] = []
    try:
        staging_directory.mkdir(mode=0o755)
        for relative_path in PUBLISHABLE_FILES:
            source_path = source_root / relative_path
            if not source_path.is_file():
                continue
            if source_path.is_symlink():
                raise ValueError(f"refusing to publish symlink: {source_path}")
            destination_path = staging_directory / relative_path
            destination_path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            destination_path.parent.chmod(0o755)
            shutil.copyfile(source_path, destination_path)
            destination_path.chmod(0o644)
            manifest_files.append(
                {
                    "path": relative_path.as_posix(),
                    "bytes": destination_path.stat().st_size,
                    "sha256": sha256(destination_path),
                }
            )

        manifest = {
            "schemaVersion": 1,
            "runId": args.run_id,
            "publishedAt": datetime.now(timezone.utc).isoformat(),
            "sourceRoot": str(source_root),
            "sourceCommit": repository_commit(),
            "tool": "manual-ripper-reviewed-results-publisher-v1",
            "files": manifest_files,
        }
        manifest_path = staging_directory / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        manifest_path.chmod(0o644)
        staging_directory.rename(final_directory)
    except Exception:
        if staging_directory.exists():
            shutil.rmtree(staging_directory)
        raise

    return final_directory


def main() -> int:
    args = parse_args()
    try:
        published_directory = publish(args)
    except Exception as error:
        print(f"publish failed: {error}", file=sys.stderr)
        return 1
    print(published_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
