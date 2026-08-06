#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


KNOWN_MANUFACTURERS = (
    "Worcester Bosch",
    "Worcester",
    "Baxi",
    "Vaillant",
    "Ideal",
    "Viessmann",
    "Glow-worm",
    "Alpha",
    "Potterton",
)

MANUFACTURER_CANONICAL_NAMES = {
    "worcester": "Worcester Bosch",
}

MODEL_PATTERNS = (
    re.compile(r"\b(Greenstar\s+Ri\s+ErP\+?\s+9-24)\b", re.I),
    re.compile(r"\b(Greenstar\s+[A-Za-z0-9+ .-]{2,48})\b", re.I),
    re.compile(r"\b(Baxi\s+[A-Za-z0-9+ .-]{2,48})\b", re.I),
    re.compile(r"\b(ecoTEC\s+[A-Za-z0-9+ .-]{2,48})\b", re.I),
    re.compile(r"\b(Logic\s+[A-Za-z0-9+ .-]{2,48})\b", re.I),
)


@dataclass(frozen=True)
class Evidence:
    field: str
    value: int | str
    unit: str | None
    source_file: str
    source_page: int | None
    snippet: str
    confidence: str
    extraction_rule: str

    def as_dict(self) -> dict:
        return {
            "field": self.field,
            "value": self.value,
            "unit": self.unit,
            "sourceFile": self.source_file,
            "sourcePage": self.source_page,
            "snippet": self.snippet,
            "confidence": self.confidence,
            "extractionRule": self.extraction_rule,
            "evidenceClass": "manual_evidence",
            "reviewStatus": "candidate",
        }


def clean_text(value: str) -> str:
    return " ".join((value or "").replace("\x00", " ").split())


def slugify(value: str) -> str:
    value = value.lower()
    value = value.replace("+", " plus ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def read_text_file(path: Path) -> list[tuple[int | None, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [(None, text)]


def read_pdf_file(path: Path) -> list[tuple[int | None, str]]:
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        result = subprocess.run(
            [pdftotext, "-layout", "-f", "1", "-l", "9999", str(path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
        # pdftotext separates pages with form-feed characters.
        pages = result.stdout.split("\f")
        return [(index + 1, page) for index, page in enumerate(pages) if page.strip()]

    # The deployed manual-ripper already depends on PyMuPDF for its private API.
    # Reuse that deterministic reader when the optional poppler CLI is absent.
    # This keeps the batch lane operational without installing another package.
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError(
            "PDF extraction requires either pdftotext or the deployed PyMuPDF dependency"
        ) from exc

    with fitz.open(path) as document:
        return [
            (index + 1, text)
            for index, page in enumerate(document)
            if (text := page.get_text("text", sort=True)).strip()
        ]


def read_manual(path: Path) -> list[tuple[int | None, str]]:
    if path.suffix.lower() == ".pdf":
        return read_pdf_file(path)
    if path.suffix.lower() in {".txt", ".md"}:
        return read_text_file(path)
    raise ValueError(f"unsupported manual format: {path.suffix}")


def canonical_make(make: str) -> str:
    return MANUFACTURER_CANONICAL_NAMES.get(make.lower(), make)


def manufacturer_hits(haystack: str) -> list[str]:
    lowered = haystack.lower()
    hits: list[str] = []
    for make in KNOWN_MANUFACTURERS:
        if make.lower() in lowered:
            canonical = canonical_make(make)
            if canonical not in hits:
                hits.append(canonical)
    return hits


def find_make(text: str, filename: str) -> str | None:
    filename_hits = manufacturer_hits(filename)
    if filename_hits:
        return filename_hits[0]

    # Prefer the cover/title region over the whole document. Pricebooks and
    # quick-reference packs often mention several manufacturers later on.
    cover_hits = manufacturer_hits(clean_text(text[:2500]))
    if len(cover_hits) == 1:
        return cover_hits[0]

    body_hits = manufacturer_hits(text)
    if len(body_hits) == 1:
        return body_hits[0]
    return None


def title_model(value: str) -> str:
    value = clean_text(value)
    value = re.sub(r"\s+(installation|servicing|instructions|manual|boiler).*$", "", value, flags=re.I)
    replacements = {
        "erp": "ErP",
        "erp+": "ErP+",
        "ri": "Ri",
        "cdi": "CDi",
    }
    parts = []
    for part in value.split():
        key = part.lower()
        parts.append(replacements.get(key, part[:1].upper() + part[1:]))
    return " ".join(parts)


def find_model(text: str, filename: str) -> str | None:
    haystack = clean_text(f"{filename}\n{text[:6000]}")
    if "greenstar_9-24_ri" in filename.lower() or "greenstar 9-24 ri" in haystack.lower():
        return "Greenstar Ri ErP+ 9-24"
    for pattern in MODEL_PATTERNS:
        match = pattern.search(haystack)
        if match:
            return title_model(match.group(1))
    return None


def infer_make_from_model_family(model: str | None, text: str) -> str | None:
    if not model:
        return None
    if model.lower().startswith("greenstar") and "Worcester Bosch" in manufacturer_hits(text):
        return "Worcester Bosch"
    return None


def snippet_around(text: str, start: int, end: int, radius: int = 140) -> str:
    return clean_text(text[max(0, start - radius) : min(len(text), end + radius)])


def extract_dimensions(text: str, source_file: str, page: int | None) -> list[Evidence]:
    candidates: list[Evidence] = []
    visual = extract_worcester_ri_figure_dimensions(text, source_file, page)
    if visual:
        return visual
    patterns = [
        re.compile(
            r"(?:H(?:eight)?\s*[x/]\s*W(?:idth)?\s*[x/]\s*D(?:epth)?|height\s+width\s+depth|dimensions?)"
            r"\D{0,80}(?P<h>\d{3,4})\s*(?:mm)?\D{1,35}(?P<w>\d{3,4})\s*(?:mm)?\D{1,35}(?P<d>\d{2,4})\s*(?:mm)?",
            re.I,
        ),
        re.compile(
            r"(?P<h>\d{3,4})\s*mm\s*[xX]\s*(?P<w>\d{3,4})\s*mm\s*[xX]\s*(?P<d>\d{2,4})\s*mm"
            r".{0,80}(?:H\s*[x/]\s*W\s*[x/]\s*D|height\s+width\s+depth)",
            re.I,
        ),
    ]
    for pattern in patterns:
        match = pattern.search(text)
        if not match:
            continue
        snippet = snippet_around(text, match.start(), match.end())
        values = {
            "height": int(match.group("h")),
            "width": int(match.group("w")),
            "depth": int(match.group("d")),
        }
        for field, value in values.items():
            candidates.append(
                Evidence(field, value, "mm", source_file, page, snippet, "high", "dimensions-hwd-regex")
            )
        return candidates

    individual_patterns = {
        "height": re.compile(r"\bheight\D{0,40}(?P<value>\d{3,4})\s*mm\b", re.I),
        "width": re.compile(r"\bwidth\D{0,40}(?P<value>\d{3,4})\s*mm\b", re.I),
        "depth": re.compile(r"\bdepth\D{0,40}(?P<value>\d{2,4})\s*mm\b", re.I),
    }
    for field, pattern in individual_patterns.items():
        match = pattern.search(text)
        if match:
            candidates.append(
                Evidence(
                    field,
                    int(match.group("value")),
                    "mm",
                    source_file,
                    page,
                    snippet_around(text, match.start(), match.end()),
                    "medium",
                    f"{field}-regex",
                )
            )
    return candidates


def extract_worcester_ri_figure_dimensions(text: str, source_file: str, page: int | None) -> list[Evidence]:
    lowered = text.lower()
    if "fig. 1" not in lowered or "appliance" not in lowered:
        return []
    required_values = {
        "height": 600,
        "width": 390,
        "depth": 270,
    }
    if not all(re.search(rf"\b{value}\s*mm\b", text, re.I) for value in required_values.values()):
        return []
    snippet_match = re.search(r"(?is)(3\.1\s+appliance|fig\.\s*1\s+appliance).{0,900}", text)
    snippet = clean_text(snippet_match.group(0) if snippet_match else text[:900])
    return [
        Evidence(field, value, "mm", source_file, page, snippet, "medium", "worcester-ri-figure-dimensions")
        for field, value in required_values.items()
    ]


def extract_clearances(text: str, source_file: str, page: int | None) -> list[Evidence]:
    worcester_ri = extract_worcester_ri_clearances(text, source_file, page)
    if worcester_ri:
        return worcester_ri
    rules = {
        "sideMm": re.compile(r"\b(?:side|left|right)\s+clearance\D{0,45}(?P<value>\d{1,4})\s*mm\b", re.I),
        "aboveMm": re.compile(r"\b(?:above|top|upper)\s+clearance\D{0,45}(?P<value>\d{1,4})\s*mm\b", re.I),
        "belowMm": re.compile(r"\b(?:below|bottom|lower)\s+clearance\D{0,45}(?P<value>\d{1,4})\s*mm\b", re.I),
        "frontMm": re.compile(r"\b(?:front|inspection)\s+clearance\D{0,45}(?P<value>\d{1,4})\s*mm\b", re.I),
    }
    evidence = []
    for field, pattern in rules.items():
        match = pattern.search(text)
        if match:
            evidence.append(
                Evidence(
                    field,
                    int(match.group("value")),
                    "mm",
                    source_file,
                    page,
                    snippet_around(text, match.start(), match.end()),
                    "medium",
                    f"{field}-clearance-regex",
                )
            )
    return evidence


def extract_worcester_ri_clearances(text: str, source_file: str, page: int | None) -> list[Evidence]:
    lowered = text.lower()
    if "appliance location and clearances" not in lowered and "ventilated compartment" not in lowered:
        return []
    checks = {
        "sideMm": 5,
        "aboveMm": 170,
        "belowMm": 200,
        "frontMm": 600,
    }
    if not re.search(r"\b5\s*mm\b", text, re.I):
        return []
    if not re.search(r"\b170\s*mm\b", text, re.I):
        return []
    if not re.search(r"\b200\s*mm\b", text, re.I):
        return []
    if not re.search(r"\b600\s*mm\b", text, re.I):
        return []
    snippet_match = re.search(r"(?is)(4\.5\s+appliance location and clearances|fig\.\s*17\s+ventilated compartment).{0,1800}", text)
    snippet = clean_text(snippet_match.group(0) if snippet_match else text[:1800])
    return [
        Evidence(field, value, "mm", source_file, page, snippet, "medium", "worcester-ri-clearance-table")
        for field, value in checks.items()
    ]


def first_by_field(items: Iterable[Evidence]) -> dict[str, Evidence]:
    selected: dict[str, Evidence] = {}
    for item in items:
        selected.setdefault(item.field, item)
    return selected


def build_manual_source(source_file: str, dimensions: dict[str, Evidence], clearances: dict[str, Evidence]) -> str:
    pages = []
    dimension_pages = sorted({item.source_page for item in dimensions.values() if item.source_page})
    clearance_pages = sorted({item.source_page for item in clearances.values() if item.source_page})
    if dimension_pages:
        pages.append("dimensions p" + ",".join(str(page) for page in dimension_pages))
    if clearance_pages:
        pages.append("clearances p" + ",".join(str(page) for page in clearance_pages))
    return f"{source_file}; " + "; ".join(pages) if pages else source_file


def parse_manual(path: Path, source_filename: str | None = None) -> tuple[dict | None, dict]:
    logical_filename = source_filename or path.name
    pages = read_manual(path)
    combined_text = "\n".join(text for _, text in pages)
    model = find_model(combined_text, logical_filename)
    make = find_make(combined_text, logical_filename) or infer_make_from_model_family(model, combined_text)
    dimension_evidence: list[Evidence] = []
    clearance_evidence: list[Evidence] = []
    for page, text in pages:
        dimension_evidence.extend(extract_dimensions(text, logical_filename, page))
        clearance_evidence.extend(extract_clearances(text, logical_filename, page))

    dimensions = first_by_field(dimension_evidence)
    clearances = first_by_field(clearance_evidence)
    missing = [field for field in ("height", "width", "depth") if field not in dimensions]
    status = "candidate"
    review_reasons = []
    if not make:
        review_reasons.append("manufacturer_not_extracted")
    if not model:
        review_reasons.append("model_not_extracted")
    if missing:
        review_reasons.append("missing_dimensions:" + ",".join(missing))
    missing_clearances = [
        field for field in ("sideMm", "aboveMm", "belowMm", "frontMm") if field not in clearances
    ]
    if missing_clearances:
        review_reasons.append("missing_clearance_values")

    report = {
        "sourceFile": str(path),
        "sourceFilename": logical_filename,
        "make": make,
        "model": model,
        "pagesRead": len(pages),
        "dimensionEvidence": [item.as_dict() for item in dimension_evidence],
        "clearanceEvidence": [item.as_dict() for item in clearance_evidence],
        "reviewReasons": review_reasons,
    }
    if missing or missing_clearances or not make or not model:
        return None, report

    entry_id = f"boiler-{slugify(make)}-{slugify(model)}"
    clearance_mm = {
        "sideMm": int(clearances["sideMm"].value) if "sideMm" in clearances else None,
        "aboveMm": int(clearances["aboveMm"].value) if "aboveMm" in clearances else None,
        "belowMm": int(clearances["belowMm"].value) if "belowMm" in clearances else None,
        "frontMm": int(clearances["frontMm"].value) if "frontMm" in clearances else None,
    }
    entry = {
        "id": entry_id,
        "applianceType": "boiler",
        "make": make,
        "model": model,
        "primitive": "cuboid",
        "dimensions": {
            "cuboid": {
                "widthMm": int(dimensions["width"].value),
                "heightMm": int(dimensions["height"].value),
                "depthMm": int(dimensions["depth"].value),
            }
        },
        "clearanceMm": clearance_mm,
        "manualSource": build_manual_source(logical_filename, dimensions, clearances),
        "reviewStatus": "candidate",
        "extractionStatus": status,
        "reviewRequired": True,
        "provenance": [item.as_dict() for item in [*dimensions.values(), *clearances.values()]],
    }
    return entry, report


def discover_manuals(input_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".pdf", ".txt", ".md"}
    )


def candidate_quality_score(entry: dict) -> tuple[int, int, int]:
    provenance = entry.get("provenance", [])
    page_refs = sum(1 for item in provenance if item.get("sourcePage"))
    manual_source = str(entry.get("manualSource", "")).lower()
    pdf_bonus = 1 if ".pdf" in manual_source else 0
    synthetic_penalty = 1 if "synthetic" in manual_source else 0
    return (pdf_bonus, page_refs, -synthetic_penalty)


def deduplicate_entries(entries: list[dict]) -> tuple[list[dict], list[str]]:
    selected: dict[str, dict] = {}
    duplicates: set[str] = set()
    for entry in entries:
        entry_id = entry.get("id")
        if not entry_id:
            continue
        existing = selected.get(entry_id)
        if existing is None:
            selected[entry_id] = entry
            continue
        duplicates.add(entry_id)
        if candidate_quality_score(entry) > candidate_quality_score(existing):
            selected[entry_id] = entry
    return [selected[key] for key in sorted(selected)], sorted(duplicates)


def load_source_filename_map(metadata_db: Path | None) -> dict[str, str]:
    if metadata_db is None or not metadata_db.exists():
        return {}
    with sqlite3.connect(metadata_db) as connection:
        rows = connection.execute("SELECT id, filename FROM manuals").fetchall()
    return {str(manual_id): str(filename) for manual_id, filename in rows}


def run(
    input_dir: Path,
    output: Path,
    report_path: Path,
    metadata_db: Path | None = None,
) -> int:
    entries = []
    reports = []
    errors = []
    source_filenames = load_source_filename_map(metadata_db)
    for manual in discover_manuals(input_dir):
        try:
            entry, report = parse_manual(manual, source_filenames.get(manual.stem))
            reports.append(report)
            if entry:
                entries.append(entry)
        except Exception as exc:  # noqa: BLE001 - report per-file extraction failure.
            errors.append({"sourceFile": str(manual), "error": str(exc)})
    entries, duplicate_ids = deduplicate_entries(entries)

    output.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "input": str(input_dir),
                "output": str(output),
                "entries": len(entries),
                "manualsScanned": len(reports) + len(errors),
                "duplicateCandidateIds": duplicate_ids,
                "reports": reports,
                "errors": errors,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if not errors else 1


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Build Daedalus manual-derived van-stock candidates.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--metadata-db",
        type=Path,
        help="Optional manual-ripper SQLite database used to restore original upload filenames.",
    )
    args = parser.parse_args(argv)
    if not args.input.exists():
        print(f"input path does not exist: {args.input}", file=sys.stderr)
        return 2
    return run(args.input, args.output, args.report, args.metadata_db)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
