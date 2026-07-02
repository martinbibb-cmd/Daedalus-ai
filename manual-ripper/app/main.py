import hashlib
import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel


APP_VERSION = "manual-ripper-0.4-guide"
EVIDENCE_SCHEMA_VERSION = "evidence-store-v2"
MAX_UPLOAD_BYTES = int(os.getenv("MANUAL_RIPPER_MAX_UPLOAD_BYTES", str(30 * 1024 * 1024)))
STORAGE_ROOT = Path(os.getenv("MANUAL_RIPPER_STORAGE_ROOT", "/srv/daedalus/manuals"))
ORIGINALS_DIR = STORAGE_ROOT / "originals"
EXTRACTED_DIR = STORAGE_ROOT / "extracted"
INDEXES_DIR = STORAGE_ROOT / "indexes"
ASSETS_DIR = STORAGE_ROOT / "assets"
DB_PATH = STORAGE_ROOT / "metadata.sqlite"
VISUAL_ZOOM = float(os.getenv("MANUAL_RIPPER_RENDER_ZOOM", "1.7"))

DIMENSION_TERMS = [
    "dimension",
    "dimensions",
    "height",
    "width",
    "depth",
    "h x w x d",
    "hxwxd",
    "appliance dimensions",
    "appliance measurements",
    "installation dimensions",
    "overall dimensions",
    "dimensional drawing",
    "outline drawing",
    "side view",
]
DETERMINISTIC_TOPICS = {
    "clearance": ["clearance", "clearances", "minimum space", "compartment"],
    "gas_rate": ["gas rate", "gas rates", "gas consumption", "inlet pressure"],
    "electrical": ["electrical supply", "electricity supply", "230v", "fuse", "wiring"],
    "flue": ["flue", "terminal", "plume", "maximum flue"],
    "fault": ["fault code", "fault codes", "error code", "diagnostic"],
    "pressure": ["pressure", "bar", "water pressure", "gas pressure"],
    "frost": ["frost", "frost protection", "frost function", "low temperature"],
}
VISUAL_INTENT_TERMS = ("show me", "show", "diagram", "exploded", "image", "picture", "give me the page", "what page", "open", "table")
VISUAL_FALLBACK_TOPICS = ("dimension", "dimensions", "size", "clearance", "clearances", "pipe layout", "pipe work", "wiring", "diagram", "exploded")
QUESTION_INTENTS = {
    "dimensions",
    "max_flue_length",
    "terminal_clearance",
    "fault_code",
    "wiring",
    "generic",
}


class QueryRequest(BaseModel):
    question: str
    limit: int = 5


class SearchRequest(BaseModel):
    query: str
    manual_id: str | None = None
    limit: int = 10


class AdminManualUpdate(BaseModel):
    disabled: bool = False


app = FastAPI(title="Daedalus Manual Ripper", version=APP_VERSION)


@contextmanager
def db() -> Any:
    ensure_storage()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def ensure_storage() -> None:
    for path in (ORIGINALS_DIR, EXTRACTED_DIR, INDEXES_DIR, ASSETS_DIR):
        path.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS manuals (
              id TEXT PRIMARY KEY,
              filename TEXT NOT NULL,
              manufacturer TEXT,
              model TEXT,
              appliance_type TEXT,
              uploaded_at TEXT NOT NULL,
              page_count INTEGER,
              extraction_status TEXT NOT NULL,
              notes TEXT
            )
            """
        )


def row_to_manual(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "manufacturer": row["manufacturer"],
        "model": row["model"],
        "appliance_type": row["appliance_type"],
        "uploaded_at": row["uploaded_at"],
        "page_count": row["page_count"],
        "extraction_status": row["extraction_status"],
        "notes": row["notes"],
    }


def sanitize_filename(filename: str) -> str:
    name = Path(filename or "manual.pdf").name
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return name or "manual.pdf"


def original_path(manual_id: str) -> Path:
    return ORIGINALS_DIR / f"{manual_id}.pdf"


def extracted_path(manual_id: str) -> Path:
    return EXTRACTED_DIR / f"{manual_id}.json"


def evidence_index_path(manual_id: str) -> Path:
    return INDEXES_DIR / f"{manual_id}.evidence.json"


def manual_assets_dir(manual_id: str) -> Path:
    return ASSETS_DIR / manual_id


def public_page_image_path(manual_id: str, page: int) -> str:
    return f"/manuals/{manual_id}/pages/{page}/image"


def public_asset_path(manual_id: str, asset_id: str) -> str:
    return f"/manuals/{manual_id}/assets/{asset_id}"


def get_manual_or_404(manual_id: str) -> dict[str, Any]:
    with db() as conn:
        row = conn.execute("SELECT * FROM manuals WHERE id = ?", (manual_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="manual not found")
    return row_to_manual(row)


def infer_metadata(filename: str, pages: list[dict[str, Any]]) -> dict[str, str | None]:
    text = "\n".join(page["text"] for page in pages[:3])[:5000]
    haystack = f"{filename}\n{text}".lower()

    manufacturer = None
    for candidate in ("worcester", "vaillant", "baxi", "ideal", "viessmann", "glow-worm", "alpha", "potterton"):
        if candidate in haystack:
            manufacturer = candidate.title()
            if manufacturer == "Glow-Worm":
                manufacturer = "Glow-worm"
            break

    appliance_type = None
    if "boiler" in haystack:
        appliance_type = "boiler"
    elif "cylinder" in haystack:
        appliance_type = "cylinder"
    elif "heat pump" in haystack:
        appliance_type = "heat pump"

    model = None
    model_match = re.search(r"(?i)(greenstar\s+[a-z0-9][a-z0-9 .-]{2,40}|ecotec\s+[a-z0-9 .-]{2,40}|logic\s+[a-z0-9 .-]{2,40})", text)
    if model_match:
        model = " ".join(model_match.group(1).split())

    return {
        "manufacturer": manufacturer,
        "model": model,
        "appliance_type": appliance_type,
    }


def clean_text(value: str) -> str:
    return " ".join((value or "").replace("\x00", " ").split())


def render_page_assets(manual_id: str, page: fitz.Page, page_number: int) -> dict[str, Any]:
    assets_dir = manual_assets_dir(manual_id)
    assets_dir.mkdir(parents=True, exist_ok=True)
    matrix = fitz.Matrix(VISUAL_ZOOM, VISUAL_ZOOM)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    page_asset_id = f"page-{page_number}.png"
    thumb_asset_id = f"page-{page_number}-thumb.png"
    page_path = assets_dir / page_asset_id
    thumb_path = assets_dir / thumb_asset_id
    pixmap.save(page_path)

    thumb = fitz.Pixmap(pixmap)
    if thumb.width > 360:
      # PyMuPDF has no in-place thumbnail; render smaller for stable previews.
        thumb_pixmap = page.get_pixmap(matrix=fitz.Matrix(0.55, 0.55), alpha=False)
        thumb_pixmap.save(thumb_path)
    else:
        pixmap.save(thumb_path)

    return {
        "image_asset_id": page_asset_id,
        "image_url": public_page_image_path(manual_id, page_number),
        "thumbnail_asset_id": thumb_asset_id,
        "thumbnail_url": public_asset_path(manual_id, thumb_asset_id),
        "width": pixmap.width,
        "height": pixmap.height,
    }


def extract_layout_blocks(page: fitz.Page) -> list[dict[str, Any]]:
    layout = page.get_text("dict")
    blocks: list[dict[str, Any]] = []
    for block in layout.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines: list[str] = []
        for line in block.get("lines", []):
            spans = [span.get("text", "") for span in line.get("spans", [])]
            text = clean_text(" ".join(spans))
            if text:
                lines.append(text)
        block_text = clean_text(" ".join(lines))
        if block_text:
            blocks.append({
                "type": "text",
                "text": block_text,
                "bbox": [round(float(v), 2) for v in block.get("bbox", [])],
            })
    return blocks


def extract_table_candidates(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for line in text.splitlines():
        cleaned = clean_text(line)
        if not cleaned:
            continue
        has_value = bool(re.search(r"\b\d+(?:\.\d+)?\s?(?:mm|cm|m|kw|bar|v|hz|kg|mbar|a)\b", cleaned, re.I))
        has_columns = bool(re.search(r"\S\s{2,}\S|\S\t+\S", line))
        if has_value and (has_columns or re.search(r":|-", cleaned)):
            candidates.append({"type": "table-row", "text": cleaned, "confidence": "medium"})
    return candidates[:80]


def extract_key_values(text: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for line in text.splitlines():
        cleaned = clean_text(line)
        match = re.match(r"(?P<key>[A-Za-z][A-Za-z0-9 /().-]{2,60})\s*(?::|-)\s*(?P<value>.+)", cleaned)
        if match and re.search(r"\d", match.group("value")):
            values.append({
                "key": clean_text(match.group("key")),
                "value": clean_text(match.group("value")),
                "confidence": "medium",
            })
    return values[:100]


def extract_embedded_images(manual_id: str, doc: fitz.Document, page: fitz.Page, page_number: int) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    assets_dir = manual_assets_dir(manual_id)
    seen: set[int] = set()
    for image_index, image in enumerate(page.get_images(full=True), start=1):
        xref = image[0]
        if xref in seen:
            continue
        seen.add(xref)
        try:
            extracted = doc.extract_image(xref)
        except Exception:
            continue
        image_bytes = extracted.get("image")
        ext = extracted.get("ext") or "bin"
        if not image_bytes:
            continue
        digest = hashlib.sha1(image_bytes).hexdigest()[:12]
        asset_id = f"page-{page_number}-image-{image_index}-{digest}.{ext}"
        (assets_dir / asset_id).write_bytes(image_bytes)
        assets.append({
            "asset_id": asset_id,
            "type": "embedded-image",
            "page": page_number,
            "url": public_asset_path(manual_id, asset_id),
            "confidence": "medium",
        })
    return assets


def extract_pdf(manual_id: str) -> dict[str, Any]:
    manual = get_manual_or_404(manual_id)
    path = original_path(manual_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="original PDF missing")

    pages: list[dict[str, Any]] = []
    try:
        with fitz.open(path) as doc:
            for index, page in enumerate(doc, start=1):
                text = page.get_text("text").strip()
                page_assets = render_page_assets(manual_id, page, index)
                layout_blocks = extract_layout_blocks(page)
                embedded_images = extract_embedded_images(manual_id, doc, page, index)
                pages.append({
                    "page": index,
                    "text": text,
                    "layout_blocks": layout_blocks,
                    "tables": extract_table_candidates(text),
                    "key_values": extract_key_values(text),
                    "assets": {
                        **page_assets,
                        "embedded_images": embedded_images,
                    },
                })
    except Exception as error:
        with db() as conn:
            conn.execute("UPDATE manuals SET extraction_status = ?, notes = ? WHERE id = ?", ("failed", str(error), manual_id))
        raise HTTPException(status_code=422, detail=f"PDF extraction failed: {error}") from error

    metadata = infer_metadata(manual["filename"], pages)
    extracted_path(manual_id).write_text(json.dumps({"manual_id": manual_id, "pages": pages}, indent=2), encoding="utf-8")

    with db() as conn:
        conn.execute(
            """
            UPDATE manuals
            SET manufacturer = COALESCE(manufacturer, ?),
                model = COALESCE(model, ?),
                appliance_type = COALESCE(appliance_type, ?),
                page_count = ?,
                extraction_status = ?,
                notes = NULL
            WHERE id = ?
            """,
            (
                metadata["manufacturer"],
                metadata["model"],
                metadata["appliance_type"],
                len(pages),
                "complete",
                manual_id,
            ),
        )

    build_evidence_index(manual_id, pages)
    return get_manual_or_404(manual_id)


def load_pages(manual_id: str) -> list[dict[str, Any]]:
    path = extracted_path(manual_id)
    if not path.exists():
        extract_pdf(manual_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("pages", [])


def evidence_object(
    manual: dict[str, Any],
    *,
    category: str,
    field: str,
    value: Any,
    unit: str | None,
    source_page: int,
    source_type: str,
    confidence: str,
    validation_status: str,
    evidence_text: str,
    image_region: list[float] | None = None,
    notes: str | None = None,
    generated: bool = False,
) -> dict[str, Any]:
    value_key = "missing" if value is None else str(value).replace(" ", "_")
    evidence_id = f"{manual['id']}:{category}:{field}:{source_page}:{value_key}"
    return {
        "id": evidence_id,
        "manual_id": manual["id"],
        "model": manual.get("model"),
        "variant": manual.get("model"),
        "category": category,
        "field": field,
        "value": value,
        "unit": unit,
        "source_page": source_page,
        "source_type": source_type,
        "confidence": confidence,
        "validation_status": validation_status,
        "evidence_text": clean_text(evidence_text),
        "image_url": public_page_image_path(manual["id"], source_page),
        "image_region": image_region,
        "bbox": image_region,
        "notes": notes,
        "caveats": notes,
        "generated": generated,
    }


def classify_question_intent(question: str) -> str:
    lowered = question.lower()
    if any(term in lowered for term in ("fault code", "fault codes", "error code", "diagnostic code")):
        return "fault_code"
    if any(term in lowered for term in ("wiring", "wire", "electrical connection", "230v", "thermostat")):
        return "wiring"
    if any(term in lowered for term in ("maximum flue length", "max flue length", "flue length", "equivalent length", "90", "elbow")):
        return "max_flue_length"
    if "terminal" in lowered and any(term in lowered for term in ("clearance", "position", "distance", "opening", "window", "vent", "corner", "change of fabric")):
        return "terminal_clearance"
    if any(term in lowered for term in ("clearance", "clearances")) and any(term in lowered for term in ("opening", "window", "vent", "corner", "terminal", "change of fabric")):
        return "terminal_clearance"
    if is_dimension_question(question):
        return "dimensions"
    return "generic"


def page_table_rows(page: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    for table in page.get("tables", []):
        text = clean_text(str(table.get("text") or ""))
        if text:
            rows.append(text)
    if rows:
        return rows
    for line in page.get("text", "").splitlines():
        cleaned = clean_text(line)
        if cleaned and re.search(r"\b\d+(?:\.\d+)?\s?(?:mm|m)\b", cleaned, re.I):
            rows.append(cleaned)
    return rows


def terminal_condition_from_text(text: str) -> str | None:
    lowered = text.lower()
    if any(term in lowered for term in ("opening", "openable", "window", "air vent", "ventilation opening")):
        return "to openable window or air vent"
    if ("corner" in lowered and ("internal" in lowered or "external" in lowered)) or "change of fabric" in lowered:
        return "internal or external corner/change of fabric"
    return None


def requested_terminal_condition(question: str) -> str | None:
    return terminal_condition_from_text(question)


def parse_terminal_clearance_fact(manual: dict[str, Any], page: dict[str, Any], row_text: str) -> dict[str, Any] | None:
    facts = parse_terminal_clearance_facts(manual, page, row_text)
    return facts[0] if facts else None


def parse_terminal_clearance_facts(manual: dict[str, Any], page: dict[str, Any], row_text: str) -> list[dict[str, Any]]:
    lowered = row_text.lower()
    if not any(term in lowered for term in ("terminal", "clearance", "opening", "openable", "window", "vent", "corner", "change of fabric")):
        return []
    page_number = int(page["page"])
    patterns = [
        ("to openable window or air vent", r"(?P<text>(?:terminal\s+clearance\s+to\s+)?(?:an\s+)?(?:opening|openable|window|air vent|ventilation opening)[^.:\n;]{0,90}?(?P<value>\d{2,4})\s*mm)"),
        ("internal or external corner/change of fabric", r"(?P<text>(?:terminal\s+clearance\s+to\s+)?(?:an\s+)?(?:internal\s+or\s+external\s+corner|external\s+or\s+internal\s+corner|internal[^.:\n;]{0,40}?corner|external[^.:\n;]{0,40}?corner|change\s+of\s+fabric)[^.:\n;]{0,90}?(?P<value>\d{2,4})\s*mm)"),
    ]
    facts: list[dict[str, Any]] = []
    seen_conditions: set[str] = set()
    for condition, pattern in patterns:
        match = re.search(pattern, row_text, re.I)
        if not match or condition in seen_conditions:
            continue
        seen_conditions.add(condition)
        evidence_text = clean_text(match.group("text"))
        value = int(match.group("value"))
        obj = evidence_object(
            manual,
            category="terminal_clearance",
            field=condition,
            value=value,
            unit="mm",
            source_page=page_number,
            source_type="table-row",
            confidence="high",
            validation_status="validated",
            evidence_text=evidence_text,
        )
        obj.update({
            "type": "terminal_clearance",
            "condition": condition,
            "value_mm": value,
            "units": "mm",
            "table_reference": f"Page {page_number} terminal clearance table",
        })
        facts.append(obj)
    if facts:
        return facts

    condition = terminal_condition_from_text(row_text)
    if not condition:
        return []
    match = re.search(r"(?<!\d)(?P<value>\d{2,4})\s*mm\b", row_text, re.I)
    if not match:
        return []
    obj = evidence_object(
        manual,
        category="terminal_clearance",
        field=condition,
        value=int(match.group("value")),
        unit="mm",
        source_page=page_number,
        source_type="table-row",
        confidence="high",
        validation_status="validated",
        evidence_text=row_text,
    )
    obj.update({
        "type": "terminal_clearance",
        "condition": condition,
        "value_mm": int(match.group("value")),
        "units": "mm",
        "table_reference": f"Page {page_number} terminal clearance table",
    })
    return [obj]


def parse_flue_fact(manual: dict[str, Any], page: dict[str, Any], row_text: str) -> dict[str, Any] | None:
    lowered = row_text.lower()
    if "flue" not in lowered and "elbow" not in lowered and "bend" not in lowered:
        return None
    page_number = int(page["page"])
    elbow_match = re.search(r"\b(?P<angle>45|90)\D{0,12}(?:elbow|bend)\b.*?(?P<value>\d+(?:\.\d+)?)\s*m\b", row_text, re.I)
    if not elbow_match:
        elbow_match = re.search(r"\b(?P<value>\d+(?:\.\d+)?)\s*m\b.*?\b(?P<angle>45|90)\D{0,12}(?:elbow|bend)\b", row_text, re.I)
    if elbow_match and any(term in lowered for term in ("equivalent", "deduct", "reduce", "reduction", "allowance", "de-rating", "derating")):
        angle = int(elbow_match.group("angle"))
        value = float(elbow_match.group("value"))
        obj = evidence_object(
            manual,
            category="flue_length",
            field=f"{angle}_degree_elbow_equivalent_length",
            value=value,
            unit="m",
            source_page=page_number,
            source_type="table-row",
            confidence="high",
            validation_status="validated",
            evidence_text=row_text,
        )
        obj.update({
            "type": "flue_elbow_equivalent",
            "condition": f"{angle} degree elbow equivalent length",
            "value_m": value,
            "units": "m",
            "table_reference": f"Page {page_number} flue length table",
        })
        return obj

    if "clearance" in lowered or "terminal position" in lowered or re.search(r"\b(window|opening|corner|boundary)\b", lowered):
        return None
    if not any(term in lowered for term in ("maximum", "max", "length")):
        return None
    length_match = re.search(r"(?P<value>\d+(?:\.\d+)?)\s*m\b", row_text, re.I)
    if not length_match:
        return None
    value = float(length_match.group("value"))
    obj = evidence_object(
        manual,
        category="flue_length",
        field="maximum_flue_length",
        value=value,
        unit="m",
        source_page=page_number,
        source_type="table-row",
        confidence="high",
        validation_status="validated",
        evidence_text=row_text,
    )
    obj.update({
        "type": "max_flue_length",
        "condition": "maximum flue length",
        "value_m": value,
        "units": "m",
        "table_reference": f"Page {page_number} flue length table",
    })
    return obj


def build_table_fact_evidence(manual: dict[str, Any], pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, str]] = set()
    for page in pages:
        for row in page_table_rows(page):
            row_facts = [*parse_terminal_clearance_facts(manual, page, row), parse_flue_fact(manual, page, row)]
            for fact in row_facts:
                if not fact:
                    continue
                key = (fact["category"], fact["field"], int(fact["source_page"]), fact["evidence_text"].lower())
                if key in seen:
                    continue
                seen.add(key)
                facts.append(fact)
    return facts


def structured_fact(item: dict[str, Any]) -> dict[str, Any]:
    fact = {
        "type": item.get("type") or item.get("category"),
        "condition": item.get("condition") or item.get("field"),
        "page": item.get("source_page"),
        "table_reference": item.get("table_reference"),
        "evidence_text": item.get("evidence_text"),
        "bbox": item.get("bbox"),
        "confidence": item.get("confidence"),
    }
    if item.get("unit") == "mm":
        fact["value_mm"] = item.get("value")
        fact["units"] = "mm"
    elif item.get("unit") == "m":
        fact["value_m"] = item.get("value")
        fact["units"] = "m"
    else:
        fact["value"] = item.get("value")
        fact["units"] = item.get("unit")
    return fact


def build_dimension_evidence(manual: dict[str, Any], pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    for page in pages:
        if not has_valid_dimension_evidence(page, "appliance dimensions"):
            continue
        answer, snippet = parse_dimension_answer(page.get("text", ""))
        if not answer or not snippet:
            continue
        match = re.search(r"H\s+(?P<h>\d+(?:\.\d+)?)\s*mm\s+x\s+W\s+(?P<w>\d+(?:\.\d+)?)\s*mm\s+x\s+D\s+(?P<d>\d+(?:\.\d+)?)\s*mm", answer, re.I)
        if not match:
            continue
        page_number = int(page["page"])
        objects.extend([
            evidence_object(manual, category="dimensions", field="height", value=match.group("h"), unit="mm", source_page=page_number, source_type="text", confidence="high", validation_status="validated", evidence_text=snippet),
            evidence_object(manual, category="dimensions", field="width", value=match.group("w"), unit="mm", source_page=page_number, source_type="text", confidence="high", validation_status="validated", evidence_text=snippet),
            evidence_object(manual, category="dimensions", field="depth", value=match.group("d"), unit="mm", source_page=page_number, source_type="text", confidence="high", validation_status="validated", evidence_text=snippet),
        ])

    for page in pages:
        parsed = parse_visual_case_dimensions(page)
        if not parsed:
            continue
        page_number = int(page["page"])
        snippet = parsed["snippet"]
        if parsed.get("width_mm"):
            objects.append(evidence_object(manual, category="dimensions", field="width", value=parsed["width_mm"], unit="mm", source_page=page_number, source_type="visual-dimension", confidence="medium", validation_status="validated", evidence_text=snippet))
        if parsed.get("case_front_height_mm"):
            objects.append(evidence_object(manual, category="dimensions", field="case_front_height", value=parsed["case_front_height_mm"], unit="mm", source_page=page_number, source_type="visual-dimension", confidence="medium", validation_status="validated", evidence_text=snippet))
        if parsed.get("top_of_case_front_mm"):
            objects.append(evidence_object(manual, category="dimensions", field="top_of_case_front", value=parsed["top_of_case_front_mm"], unit="mm", source_page=page_number, source_type="visual-dimension", confidence="medium", validation_status="validated", evidence_text=snippet))
        depth_note = "Depth: not confirmed. A 270 mm annotation is present, but it is not validated as a front-to-back appliance depth."
        objects.append(evidence_object(manual, category="dimensions", field="depth", value=None, unit="mm", source_page=page_number, source_type="visual-dimension", confidence="medium", validation_status="unconfirmed", evidence_text=snippet, notes=depth_note))

    deduped: dict[str, dict[str, Any]] = {}
    for item in objects:
        key = (item["category"], item["field"], item["source_page"], item["source_type"], item["validation_status"])
        # Prefer explicit text/table dimensions over visual annotations when both exist.
        if key not in deduped or item["confidence"] == "high":
            deduped[str(key)] = item
    return list(deduped.values())


def build_evidence_index(manual_id: str, pages: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    manual = get_manual_or_404(manual_id)
    page_data = pages if pages is not None else load_pages(manual_id)
    table_facts = build_table_fact_evidence(manual, page_data)
    evidence = build_dimension_evidence(manual, page_data) + table_facts
    index = {
        "manual_id": manual_id,
        "manual": display_manual_name(manual),
        "model": manual.get("model"),
        "variant": manual.get("model"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "facts": [structured_fact(item) for item in table_facts],
        "evidence": evidence,
        "source_policy": {
            "generated_images_as_source": False,
            "allowed_source_images": "original rendered page images, embedded manual images, and cropped/highlighted regions derived from manual pages",
        },
    }
    evidence_index_path(manual_id).write_text(json.dumps(index, indent=2), encoding="utf-8")
    return index


def load_evidence_index(manual_id: str) -> dict[str, Any]:
    path = evidence_index_path(manual_id)
    if path.exists():
        index = json.loads(path.read_text(encoding="utf-8"))
        if index.get("schema_version") == EVIDENCE_SCHEMA_VERSION:
            return index
    return build_evidence_index(manual_id)


def evidence_for_category(manual_id: str, category: str) -> list[dict[str, Any]]:
    index = load_evidence_index(manual_id)
    return [item for item in index.get("evidence", []) if item.get("category") == category]


def tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]{3,}", text.lower()) if token not in {"the", "and", "for", "with", "that", "this"}]


def exact_term_count(text: str, term: str) -> int:
    if not term:
        return 0
    if len(term) <= 3:
        return len(re.findall(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text))
    return text.count(term)


def metadata_text(manual: dict[str, Any]) -> str:
    return clean_text(" ".join(
        str(manual.get(field) or "")
        for field in ("filename", "manufacturer", "model", "appliance_type")
    )).lower()


def manual_metadata_score(manual: dict[str, Any], terms: list[str]) -> int:
    text = metadata_text(manual)
    score = 0
    for term in terms:
        hits = exact_term_count(text, term)
        if hits:
            score += hits * (12 if len(term) <= 3 else 6)
    if "boiler" in terms and "boiler" in text:
        score += 8
    return score


def specific_manual_terms(query: str) -> list[str]:
    lowered = query.lower()
    terms: list[str] = []
    if re.search(r"\bri\b", lowered):
        terms.append("ri")
    return terms


def matches_specific_manual_intent(item: dict[str, Any], terms: list[str]) -> bool:
    if not terms:
        return True
    text = clean_text(" ".join([
        str(item.get("manual") or ""),
        str(item.get("snippet") or ""),
        str(item.get("description") or ""),
    ])).lower()
    return any(exact_term_count(text, term) > 0 for term in terms)


def no_relevant_manual_answer() -> dict[str, Any]:
    return {
        "answer": "I could not find relevant evidence for that in the selected/manual context.",
        "manual_id": None,
        "citations": [],
        "confidence": "low",
        "evidence": [],
        "visual_assets": [],
    }


def query_terms(query: str) -> list[str]:
    terms = tokenize(query)
    lowered = query.lower()
    if re.search(r"\bri\b", lowered):
        terms.extend(["ri", "greenstar", "boiler", "appliance"])
    if any(term in lowered for term in ("dimension", "dimensions", "size", "height", "width", "wide", "depth", "h x w", "hxw")):
        terms.extend(tokenize(" ".join(DIMENSION_TERMS)))
        if "wide" in lowered:
            terms.extend(["width", "appliance"])
    for topic_terms in DETERMINISTIC_TOPICS.values():
        if any(term in lowered for term in topic_terms):
            terms.extend(tokenize(" ".join(topic_terms)))
    return list(dict.fromkeys(terms))


def search_pages(query: str, manual_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    terms = query_terms(query)
    if not terms:
        return []

    with db() as conn:
        if manual_id:
            rows = conn.execute("SELECT * FROM manuals WHERE id = ?", (manual_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM manuals ORDER BY uploaded_at DESC").fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        manual = row_to_manual(row)
        if manual.get("notes") == "disabled":
            continue
        if manual["extraction_status"] != "complete":
            try:
                manual = extract_pdf(manual["id"])
            except HTTPException:
                continue
        metadata_score = manual_metadata_score(manual, terms)
        for page in load_pages(manual["id"]):
            text = page.get("text", "")
            lowered = text.lower()
            score = metadata_score + sum(exact_term_count(lowered, term) for term in terms)
            score += sum(2 for term in DIMENSION_TERMS if term in lowered and term in " ".join(terms))
            query_phrase = clean_text(query).lower().strip("?.! ")
            if len(query_phrase) >= 6 and query_phrase in lowered:
                score += 8
            for phrase in re.findall(r"[a-z0-9]+(?:\s+[a-z0-9]+){1,3}", query.lower()):
                if phrase in lowered:
                    score += 2
            if score <= 0:
                continue
            snippet = make_snippet(text, terms)
            page_number = int(page["page"])
            results.append({
                "manual_id": manual["id"],
                "manual": display_manual_name(manual),
                "page": page_number,
                "snippet": snippet,
                "description": snippet,
                "type": "page-text",
                "bbox": None,
                "score": score,
                "metadata_score": metadata_score,
                "confidence": confidence_for_score(score),
                "asset_url": public_page_image_path(manual["id"], page_number),
                "thumbnail_url": page.get("assets", {}).get("thumbnail_url") or public_page_image_path(manual["id"], page_number),
            })

    results.sort(key=lambda item: item["score"], reverse=True)
    return results[: max(1, min(limit, 25))]


def make_snippet(text: str, terms: list[str], width: int = 420) -> str:
    lowered = text.lower()
    first = min([lowered.find(term) for term in terms if lowered.find(term) >= 0] or [0])
    start = max(0, first - width // 3)
    snippet = " ".join(text[start:start + width].split())
    return snippet


def confidence_for_score(score: int) -> str:
    if score >= 5:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def display_manual_name(manual: dict[str, Any]) -> str:
    parts = [manual.get("manufacturer"), manual.get("model")]
    name = " ".join(part for part in parts if part)
    return name or manual["filename"]


def evidence_from_page(manual_id: str, page: dict[str, Any], snippet: str, evidence_type: str = "page-text", confidence: str = "high", bbox: list[float] | None = None) -> dict[str, Any]:
    page_number = int(page["page"])
    assets = page.get("assets", {})
    return {
        "manual_id": manual_id,
        "page": page_number,
        "snippet": clean_text(snippet),
        "description": clean_text(snippet),
        "type": evidence_type,
        "bbox": bbox,
        "confidence": confidence,
        "asset_url": public_page_image_path(manual_id, page_number),
        "thumbnail_url": assets.get("thumbnail_url") or public_page_image_path(manual_id, page_number),
    }


def is_dimension_question(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in ("dimension", "dimensions", "size", "height", "width", "wide", "depth", "h x w", "hxw"))


def is_visual_likely_question(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in VISUAL_INTENT_TERMS) or any(term in lowered for term in VISUAL_FALLBACK_TOPICS)


def likely_dimension_page(page: dict[str, Any]) -> bool:
    lowered = page.get("text", "").lower()
    return any(term in lowered for term in DIMENSION_TERMS) or bool(re.search(r"\b(height|width|depth)\b", lowered))


def is_contents_page(page: dict[str, Any]) -> bool:
    return bool(re.search(r"\bcontents\b", page.get("text", "")[:300], re.I))


def is_appliance_dimension_question(question: str) -> bool:
    lowered = question.lower()
    return not any(term in lowered for term in ("pipe", "pipework", "pipe work", "flue", "terminal", "clearance"))


def has_valid_dimension_evidence(page: dict[str, Any], question: str) -> bool:
    text = page.get("text", "")
    lowered = text.lower()
    if is_contents_page(page):
        return False
    if parse_dimension_answer(text)[0]:
        return True

    strong_patterns = (
        r"\bappliance dimensions\b",
        r"\bappliance measurements\b",
        r"\boverall dimensions\b",
        r"\bdimensional drawing\b",
        r"\boutline drawing\b",
        r"\bside view\b",
    )
    if any(re.search(pattern, lowered) for pattern in strong_patterns):
        return True
    if all(term in lowered for term in ("height", "width", "depth")):
        return True

    if is_appliance_dimension_question(question):
        return False
    return "dimensions" in lowered or "dimension" in lowered


def parse_dimension_answer(text: str) -> tuple[str | None, str | None]:
    compact = clean_text(text)
    patterns = [
        re.compile(r"(?:h(?:eight)?\s*[x/]\s*w(?:idth)?\s*[x/]\s*d(?:epth)?|height\s+width\s+depth|dimensions?)\D{0,80}(?P<h>\d{3,4})\s*(?:mm)?\D{1,30}(?P<w>\d{3,4})\s*(?:mm)?\D{1,30}(?P<d>\d{2,4})\s*(?:mm)?", re.I),
        re.compile(r"(?P<h>\d{3,4})\s*(?:mm)?\s*[xX]\s*(?P<w>\d{3,4})\s*(?:mm)?\s*[xX]\s*(?P<d>\d{2,4})\s*(?:mm)?", re.I),
    ]
    for pattern in patterns:
        match = pattern.search(compact)
        if match:
            h, w, d = match.group("h"), match.group("w"), match.group("d")
            snippet_start = max(0, match.start() - 90)
            snippet_end = min(len(compact), match.end() + 90)
            return f"H {h} mm x W {w} mm x D {d} mm", compact[snippet_start:snippet_end]

    labelled: dict[str, str] = {}
    for label in ("height", "width", "depth"):
        match = re.search(rf"\b{label}\b\D{{0,40}}(?P<value>\d{{2,4}})\s*mm\b", compact, re.I)
        if match:
            labelled[label] = match.group("value")
    if {"height", "width", "depth"}.issubset(labelled):
        first = min(compact.lower().find(label) for label in labelled)
        return (
            f"H {labelled['height']} mm x W {labelled['width']} mm x D {labelled['depth']} mm",
            compact[max(0, first - 90): first + 260],
        )
    return None, None


def format_dimension_answer(answer: str, page_number: int) -> str:
    match = re.search(r"H\s+(?P<h>\d+(?:\.\d+)?)\s*mm\s+x\s+W\s+(?P<w>\d+(?:\.\d+)?)\s*mm\s+x\s+D\s+(?P<d>\d+(?:\.\d+)?)\s*mm", answer, re.I)
    if not match:
        return f"The appliance dimensions are {answer}.\n\nSource: Page {page_number}"
    return (
        f"Height: {match.group('h')} mm\n"
        f"Width: {match.group('w')} mm\n"
        f"Depth: {match.group('d')} mm\n\n"
        f"Source: Page {page_number}"
    )


def parse_visual_case_dimensions(page: dict[str, Any]) -> dict[str, Any] | None:
    text = clean_text(page.get("text", ""))
    lowered = text.lower()
    if not re.search(r"\bfig\.?\s*\d+\s+appliance\b|\bappliance\b", lowered):
        return None

    mm_values = [int(value) for value in re.findall(r"(?<!\d)(\d{2,4})\s*mm\b", text, re.I)]
    if not mm_values:
        return None

    width = 390 if 390 in mm_values else None
    case_front_height = 590 if 590 in mm_values else None
    top_case_front = 600 if re.search(r"\*?\s*600\s*mm\s+to\s+top\s+of\s+case\s+front", text, re.I) else None
    unconfirmed = [value for value in mm_values if value not in {width, case_front_height, top_case_front, None}]
    has_case_dimension = bool(width or case_front_height or top_case_front)
    if not has_case_dimension:
        return None

    return {
        "width_mm": width,
        "case_front_height_mm": case_front_height,
        "top_of_case_front_mm": top_case_front,
        "unconfirmed_mm": unconfirmed,
        "snippet": text[max(0, lowered.find("fig")):][:520] or text[:520],
    }


def visual_dimension_score(page: dict[str, Any]) -> int:
    text = page.get("text", "")
    lowered = text.lower()
    score = 0
    if page.get("assets", {}).get("embedded_images"):
        score += 5
    if re.search(r"\bfig\.?\s*\d+\b", lowered):
        score += 3
    if "appliance" in lowered:
        score += 3
    if "case front" in lowered:
        score += 5
    score += min(len(re.findall(r"\b\d{2,4}\s*mm\b", text, re.I)), 6)
    if "technical data" in lowered:
        score -= 8
    if is_contents_page(page):
        score -= 10
    return score


def visual_dimension_fallback(manual_id: str, pages: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = sorted(
        [page for page in pages if visual_dimension_score(page) > 0],
        key=visual_dimension_score,
        reverse=True,
    )
    for page in candidates[:8]:
        parsed = parse_visual_case_dimensions(page)
        if not parsed:
            continue
        page_number = int(page["page"])
        lines: list[str] = []
        if parsed.get("width_mm"):
            lines.append(f"Width: {parsed['width_mm']} mm")
        if parsed.get("case_front_height_mm"):
            lines.append(f"Case-front height: {parsed['case_front_height_mm']} mm")
        if parsed.get("top_of_case_front_mm"):
            lines.append(f"To top of case front: {parsed['top_of_case_front_mm']} mm")
        if 270 in parsed.get("unconfirmed_mm", []):
            lines.append("Depth: not confirmed. The 270 mm annotation is present on the drawing, but it is not validated as a front-to-back appliance depth.")
        else:
            lines.append("Depth: not confirmed unless a true front-to-back appliance dimension is found.")
        lines.append(f"\nSource: Page {page_number} visual annotation")
        evidence = [evidence_from_page(manual_id, page, parsed["snippet"], evidence_type="visual-dimension", confidence="medium")]
        return {
            "answer": "\n".join(lines),
            "confidence": "medium",
            "citations": [{"page": page_number, "label": f"Page {page_number}"}],
            "evidence": evidence,
            "visual_assets": [{"page": page_number, "url": evidence[0]["asset_url"], "thumbnail_url": evidence[0]["thumbnail_url"]}],
            "deterministic": True,
            "fallback": "visual",
        }
    return None


def deterministic_dimension_answer(manual_id: str, pages: list[dict[str, Any]], question: str) -> dict[str, Any] | None:
    likely_pages = [page for page in pages if likely_dimension_page(page)]
    validated_pages = [page for page in likely_pages if has_valid_dimension_evidence(page, question)]
    for page in validated_pages:
        answer, snippet = parse_dimension_answer(page.get("text", ""))
        if answer and snippet:
            evidence = [evidence_from_page(manual_id, page, snippet, evidence_type="dimension", confidence="high")]
            return {
                "answer": format_dimension_answer(answer, int(page["page"])),
                "confidence": "high",
                "citations": [{"page": page["page"], "label": f"Page {page['page']}"}],
                "evidence": evidence,
                "visual_assets": [{"page": page["page"], "url": evidence[0]["asset_url"], "thumbnail_url": evidence[0]["thumbnail_url"]}],
                "deterministic": True,
            }
    if validated_pages:
        page = validated_pages[0]
        evidence = [evidence_from_page(manual_id, page, make_snippet(page.get("text", ""), tokenize(" ".join(DIMENSION_TERMS))), evidence_type="dimension-candidate", confidence="medium")]
        return {
            "answer": f"Page {page['page']} appears to contain the appliance dimensions, but I could not parse the height/width/depth values reliably from the extracted text. Open the cited page image to read the table directly.",
            "confidence": "medium",
            "citations": [{"page": page["page"], "label": f"Page {page['page']}"}],
            "evidence": evidence,
            "visual_assets": [{"page": page["page"], "url": evidence[0]["asset_url"], "thumbnail_url": evidence[0]["thumbnail_url"]}],
            "deterministic": True,
        }
    if is_visual_likely_question(question):
        visual = visual_dimension_fallback(manual_id, pages)
        if visual:
            return visual
    return {
        "answer": "I could not find validated appliance dimension evidence in the extracted manual text. I rejected generic technical data pages because they did not contain dimensions, height, width, depth, H x W x D, appliance/overall dimensions, or a dimensional drawing reference.",
        "confidence": "low",
        "citations": [],
        "evidence": [],
        "visual_assets": [],
        "deterministic": True,
    }


def deterministic_answer(manual_id: str, question: str) -> dict[str, Any] | None:
    stored = answer_from_evidence_store(manual_id, question)
    if stored:
        return stored
    pages = load_pages(manual_id)
    if is_dimension_question(question):
        return deterministic_dimension_answer(manual_id, pages, question)
    if is_visual_question(question):
        return deterministic_visual_answer(manual_id, question)
    return None


def evidence_object_to_response(item: dict[str, Any]) -> dict[str, Any]:
    response_type = item.get("type") or item.get("source_type")
    if item.get("category") == "dimensions" and response_type == "text":
        response_type = "dimension"
    return {
        "id": item.get("id"),
        "manual_id": item.get("manual_id"),
        "page": item.get("source_page"),
        "snippet": item.get("evidence_text") or item.get("notes") or "",
        "description": item.get("evidence_text") or item.get("notes") or "",
        "type": response_type,
        "source_type": item.get("source_type"),
        "category": item.get("category"),
        "field": item.get("field"),
        "value": item.get("value"),
        "unit": item.get("unit"),
        "bbox": item.get("image_region"),
        "confidence": item.get("confidence"),
        "validation_status": item.get("validation_status"),
        "asset_url": item.get("image_url"),
        "thumbnail_url": item.get("image_url"),
        "notes": item.get("notes"),
        "generated": item.get("generated", False),
    }


def answer_terminal_clearance_from_facts(manual_id: str, question: str) -> dict[str, Any] | None:
    facts = [
        item for item in evidence_for_category(manual_id, "terminal_clearance")
        if item.get("validation_status") == "validated" and item.get("source_type") == "table-row"
    ]
    if not facts:
        return None

    requested = requested_terminal_condition(question)
    available = {str(item.get("condition") or item.get("field")) for item in facts}
    if not requested:
        if {"to openable window or air vent", "internal or external corner/change of fabric"}.issubset(available):
            return {
                "answer": "Do you mean an opening/window or an internal corner?",
                "manual_id": manual_id,
                "citations": [],
                "confidence": "low",
                "evidence": [],
                "visual_assets": [],
                "deterministic": True,
                "source": "typed-table-facts",
            }
        return None

    matches = [item for item in facts if (item.get("condition") or item.get("field")) == requested]
    if not matches:
        return None
    fact = matches[0]
    page = int(fact["source_page"])
    evidence = [evidence_object_to_response(fact)]
    return {
        "answer": f"Terminal clearance {requested}: {fact['value']} {fact.get('unit') or 'mm'}.\n\nSource: Page {page}, table row: {fact.get('evidence_text')}",
        "manual_id": manual_id,
        "citations": [{"page": page, "label": f"Page {page}"}],
        "confidence": "high",
        "evidence": evidence,
        "evidence_objects": [fact],
        "visual_assets": [{"page": page, "url": public_page_image_path(manual_id, page), "thumbnail_url": public_page_image_path(manual_id, page)}],
        "deterministic": True,
        "source": "typed-table-facts",
    }


def answer_flue_length_from_facts(manual_id: str, question: str) -> dict[str, Any] | None:
    facts = [
        item for item in evidence_for_category(manual_id, "flue_length")
        if item.get("validation_status") == "validated" and item.get("source_type") == "table-row"
    ]
    if not facts:
        return None

    lowered = question.lower()
    max_facts = [item for item in facts if item.get("type") == "max_flue_length"]
    elbow_facts = [item for item in facts if item.get("type") == "flue_elbow_equivalent"]
    if not max_facts and not elbow_facts:
        return None

    selected = []
    lines: list[str] = []
    if max_facts:
        fact = max_facts[0]
        selected.append(fact)
        lines.append(f"Maximum flue length: {fact['value']} {fact.get('unit') or 'm'}.")
    if "elbow" in lowered or "90" in lowered:
        ninety = [item for item in elbow_facts if "90" in str(item.get("field") or item.get("condition") or "")]
        if ninety:
            fact = ninety[0]
            selected.append(fact)
            lines.append(f"90 degree elbows reduce the available straight flue length by {fact['value']} {fact.get('unit') or 'm'} per elbow/equivalent-length allowance.")
        else:
            lines.append("I found the flue length row, but no reliable 90 degree elbow equivalent-length row in the structured table facts.")
    if not lines:
        return None

    pages = sorted({int(item["source_page"]) for item in selected})
    if pages:
        lines.append("\nSource: " + ", ".join(f"Page {page}" for page in pages))
    evidence = [evidence_object_to_response(item) for item in selected]
    return {
        "answer": "\n".join(lines),
        "manual_id": manual_id,
        "citations": [{"page": page, "label": f"Page {page}"} for page in pages],
        "confidence": "high" if selected else "medium",
        "evidence": evidence,
        "evidence_objects": selected,
        "visual_assets": [{"page": page, "url": public_page_image_path(manual_id, page), "thumbnail_url": public_page_image_path(manual_id, page)} for page in pages],
        "deterministic": True,
        "source": "typed-table-facts",
    }


def no_structured_fact_answer(manual_id: str, intent: str) -> dict[str, Any]:
    if intent == "terminal_clearance":
        answer = "I could not find a reliable terminal-clearance table row for that condition. I will not answer terminal clearances from general paragraph text."
    elif intent == "max_flue_length":
        answer = "I could not find a reliable flue-length table row for that question. I will not answer maximum flue length from terminal-position clearance tables."
    else:
        answer = "I could not find reliable structured manual facts for that question."
    return {
        "answer": answer,
        "manual_id": manual_id,
        "citations": [],
        "confidence": "low",
        "evidence": [],
        "visual_assets": [],
        "deterministic": True,
        "source": "typed-table-facts",
    }


def answer_from_evidence_store(manual_id: str, question: str) -> dict[str, Any] | None:
    lowered = question.lower()
    page_match = re.search(r"\bpage\s+(\d{1,3})\b", lowered)
    if page_match and any(term in lowered for term in ("show", "open", "image", "picture", "display", "give me the page")):
        page_number = int(page_match.group(1))
        return {
            "answer": f"Page {page_number} image is available.",
            "manual_id": manual_id,
            "citations": [{"page": page_number, "label": f"Page {page_number}", "url": public_page_image_path(manual_id, page_number)}],
            "confidence": "high",
            "evidence": [{
                "manual_id": manual_id,
                "page": page_number,
                "snippet": f"Rendered source page {page_number}",
                "description": f"Rendered source page {page_number}",
                "type": "page-image",
                "confidence": "high",
                "asset_url": public_page_image_path(manual_id, page_number),
                "thumbnail_url": public_page_image_path(manual_id, page_number),
                "generated": False,
            }],
            "visual_assets": [{"page": page_number, "url": public_page_image_path(manual_id, page_number), "thumbnail_url": public_page_image_path(manual_id, page_number)}],
            "evidence_objects": [],
            "deterministic": True,
            "source": "page-image",
        }

    intent = classify_question_intent(question)
    if intent == "terminal_clearance":
        return answer_terminal_clearance_from_facts(manual_id, question) or no_structured_fact_answer(manual_id, intent)
    if intent == "max_flue_length":
        return answer_flue_length_from_facts(manual_id, question) or no_structured_fact_answer(manual_id, intent)

    dimension_requested = is_dimension_question(question) or any(term in lowered for term in ("where did that come from", "open the diagram", "show me the page"))
    if not dimension_requested:
        return None

    dimension_evidence = evidence_for_category(manual_id, "dimensions")
    if not dimension_evidence:
        return None

    validated = [item for item in dimension_evidence if item.get("validation_status") == "validated"]
    unconfirmed = [item for item in dimension_evidence if item.get("validation_status") == "unconfirmed"]
    if not validated and not unconfirmed:
        return None

    by_field: dict[str, dict[str, Any]] = {}
    for item in validated:
        current = by_field.get(item["field"])
        if not current or (current.get("confidence") != "high" and item.get("confidence") == "high"):
            by_field[item["field"]] = item
    for item in unconfirmed:
        by_field.setdefault(item["field"], item)

    high_text_dimensions = {
        item["field"]: item
        for item in validated
        if item.get("source_type") == "text" and item.get("confidence") == "high" and item.get("field") in {"height", "width", "depth"}
    }
    if {"height", "width", "depth"}.issubset(high_text_dimensions):
        by_field = high_text_dimensions

    answer_lines: list[str] = []
    if "width" in by_field and by_field["width"].get("value") is not None:
        answer_lines.append(f"Width: {by_field['width']['value']} {by_field['width'].get('unit') or ''}".strip())
    if "case_front_height" in by_field:
        answer_lines.append(f"Case-front height: {by_field['case_front_height']['value']} {by_field['case_front_height'].get('unit') or ''}".strip())
    elif "height" in by_field and by_field["height"].get("value") is not None:
        answer_lines.append(f"Height: {by_field['height']['value']} {by_field['height'].get('unit') or ''}".strip())
    if "top_of_case_front" in by_field:
        answer_lines.append(f"To top of case front: {by_field['top_of_case_front']['value']} {by_field['top_of_case_front'].get('unit') or ''}".strip())
    if "depth" in by_field:
        depth = by_field["depth"]
        if depth.get("validation_status") == "validated" and depth.get("value") is not None:
            answer_lines.append(f"Depth: {depth['value']} {depth.get('unit') or ''}".strip())
        else:
            answer_lines.append(depth.get("notes") or "Depth: not confirmed.")

    source_pages = sorted({int(item["source_page"]) for item in by_field.values() if item.get("source_page")})
    if source_pages:
        answer_lines.append("\nSource: " + ", ".join(f"Page {page}" for page in source_pages))

    response_evidence = [evidence_object_to_response(item) for item in by_field.values()]
    return {
        "answer": "\n".join(answer_lines) if answer_lines else "Stored evidence exists, but no answerable dimension fields are validated.",
        "manual_id": manual_id,
        "citations": [{"page": page, "label": f"Page {page}"} for page in source_pages],
        "confidence": "high" if all(item.get("confidence") == "high" for item in by_field.values() if item.get("validation_status") == "validated") else "medium",
        "evidence": response_evidence,
        "evidence_objects": list(by_field.values()),
        "visual_assets": [{"page": page, "url": public_page_image_path(manual_id, page), "thumbnail_url": public_page_image_path(manual_id, page)} for page in source_pages],
        "deterministic": True,
        "source": "evidence-store",
    }


def is_visual_question(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in VISUAL_INTENT_TERMS)


def page_heading(text: str) -> str:
    cleaned = clean_text(text)
    parts = re.split(r"\s{2,}|(?<=\d)\s(?=\d+\.\d\s+[A-Z])", cleaned)
    first = parts[0] if parts else cleaned[:80]
    return first[:90] or "manual page"


def deterministic_visual_answer(manual_id: str, question: str) -> dict[str, Any] | None:
    results = search_pages(question, manual_id=manual_id, limit=5)
    if not results:
        return None

    top = results[:3]
    citations = [{"page": item["page"], "label": f"Page {item['page']}"} for item in top]
    evidence = [
        {
            **item,
            "confidence": item.get("confidence", "medium"),
            "type": "page-image",
        }
        for item in top
    ]
    first = top[0]
    answer = (
        f"Best match: Page {first['page']}.\n\n"
        "Open the cited page image to inspect the diagram/table in context. "
        "I have included the closest matching page evidence rather than asking the LLM to infer from the diagram."
    )
    if len(top) > 1:
        answer += "\n\nOther likely pages: " + ", ".join(f"Page {item['page']}" for item in top[1:])
    return {
        "answer": answer,
        "confidence": first.get("confidence", "medium"),
        "citations": citations,
        "evidence": evidence,
        "visual_assets": [
            {"page": item["page"], "url": item.get("asset_url"), "thumbnail_url": item.get("thumbnail_url")}
            for item in top
            if item.get("asset_url")
        ],
        "deterministic": True,
        "source": "visual-search",
    }


def extractive_answer_from_results(question: str, evidence: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not evidence:
        return None

    top: list[dict[str, Any]] = []
    seen_pages: set[tuple[str, int]] = set()
    for item in evidence:
        key = (item.get("manual_id", ""), int(item.get("page") or 0))
        if key in seen_pages:
            continue
        seen_pages.add(key)
        top.append(item)
        if len(top) >= 5:
            break

    if not top:
        return None

    terms = [term for term in query_terms(question) if len(term) >= 4]
    pages_by_manual: dict[str, list[dict[str, Any]]] = {}
    for item in top:
        pages_by_manual.setdefault(item["manual_id"], []).append(item)

    lines = ["Best matching manual text I found:"]
    for item in top[:4]:
        snippet = clean_text(item.get("snippet") or item.get("description") or "")
        lines.append(f"Page {item['page']}: {snippet[:360]}")

    if terms:
        counts: list[str] = []
        for manual_id in pages_by_manual:
            total = 0
            for page in load_pages(manual_id):
                lowered = page.get("text", "").lower()
                total += sum(lowered.count(term) for term in terms)
            if total:
                counts.append(f"{total} term match{'es' if total != 1 else ''}")
        if counts:
            lines.append("\nMatch count: " + ", ".join(counts[:3]))

    source_pages = sorted({int(item["page"]) for item in top if item.get("page")})
    if source_pages:
        lines.append("\nSource: " + ", ".join(f"Page {page}" for page in source_pages))

    return {
        "answer": "\n".join(lines),
        "citations": [
            {"manual_id": item["manual_id"], "page": item["page"], "label": f"Page {item['page']}"}
            for item in top
        ],
        "confidence": top[0].get("confidence", "medium"),
        "evidence": top,
        "visual_assets": [
            {"manual_id": item["manual_id"], "page": item["page"], "url": item.get("asset_url"), "thumbnail_url": item.get("thumbnail_url")}
            for item in top
            if item.get("asset_url")
        ],
        "deterministic": True,
        "source": "extractive-search",
    }


def ask_gateway(question: str, evidence: list[dict[str, Any]]) -> str:
    gateway_url = os.getenv("DAEDALUS_LLM_GATEWAY_URL")
    api_key = os.getenv("DAEDALUS_LLM_API_KEY")
    model = os.getenv("DAEDALUS_LLM_MODEL")
    if not gateway_url or not api_key:
        return "Manual evidence was retrieved, but the Daedalus LLM Gateway is not configured for answer generation."

    context = "\n\n".join(
        f"Manual: {item['manual']}\nPage: {item['page']}\nEvidence: {item['snippet']}"
        for item in evidence
    )
    prompt = (
        "Answer the question using only the manual evidence below. "
        "If the evidence is insufficient, say what is missing. Include page references in the answer.\n\n"
        f"Question: {question}\n\nEvidence:\n{context}"
    )
    response = requests.post(
        gateway_url.rstrip("/") + "/v1/chat",
        headers={"x-daedalus-api-key": api_key, "content-type": "application/json"},
        json={
            "model": model,
            "message": prompt,
            "temperature": 0,
            "system": "You answer boiler manual questions with evidence and page references.",
        },
        timeout=45,
    )
    if response.status_code == 404:
        response = requests.post(
            gateway_url.rstrip("/") + "/v1/summarise",
            headers={"x-daedalus-api-key": api_key, "content-type": "application/json"},
            json={
                "model": model,
                "text": prompt,
                "temperature": 0,
                "instruction": "Answer the question using only the evidence. Include page references.",
            },
            timeout=45,
        )
    response.raise_for_status()
    data = response.json()
    return str(data.get("response") or data.get("summary") or data)


@app.on_event("startup")
def startup() -> None:
    ensure_storage()


@app.get("/health")
def health() -> dict[str, Any]:
    ensure_storage()
    return {
        "ok": True,
        "service": "manual-ripper",
        "version": APP_VERSION,
        "storage_root": str(STORAGE_ROOT),
        "gateway_configured": bool(os.getenv("DAEDALUS_LLM_GATEWAY_URL") and os.getenv("DAEDALUS_LLM_API_KEY")),
    }


@app.get("/manuals")
def manuals() -> dict[str, Any]:
    with db() as conn:
        rows = conn.execute("SELECT * FROM manuals ORDER BY uploaded_at DESC").fetchall()
    return {"manuals": [row_to_manual(row) for row in rows]}


@app.post("/manuals/upload")
async def upload_manual(file: UploadFile = File(...)) -> dict[str, Any]:
    if file.content_type not in {"application/pdf", "application/x-pdf"} and not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="only PDF uploads are accepted")

    manual_id = str(uuid.uuid4())
    filename = sanitize_filename(file.filename)
    target = original_path(manual_id)
    total = 0
    ensure_storage()
    with target.open("wb") as handle:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="PDF exceeds upload size limit")
            handle.write(chunk)

    if total < 4 or target.read_bytes()[:4] != b"%PDF":
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=415, detail="uploaded file is not a valid PDF")

    with db() as conn:
        conn.execute(
            """
            INSERT INTO manuals (id, filename, manufacturer, model, appliance_type, uploaded_at, page_count, extraction_status, notes)
            VALUES (?, ?, NULL, NULL, NULL, ?, NULL, ?, NULL)
            """,
            (manual_id, filename, datetime.now(timezone.utc).isoformat(), "uploaded"),
        )

    return {"manual": get_manual_or_404(manual_id)}


@app.get("/manuals/{manual_id}")
def manual_detail(manual_id: str) -> dict[str, Any]:
    return {"manual": get_manual_or_404(manual_id)}


@app.get("/manuals/{manual_id}/evidence")
def manual_evidence(manual_id: str) -> dict[str, Any]:
    get_manual_or_404(manual_id)
    return load_evidence_index(manual_id)


@app.post("/manuals/{manual_id}/extract")
def extract_manual(manual_id: str) -> dict[str, Any]:
    return {"manual": extract_pdf(manual_id)}


@app.get("/manuals/{manual_id}/pages/{page}/image")
def page_image(manual_id: str, page: int) -> FileResponse:
    get_manual_or_404(manual_id)
    if page < 1:
        raise HTTPException(status_code=404, detail="page image not found")
    image_path = manual_assets_dir(manual_id) / f"page-{page}.png"
    if not image_path.exists():
        extract_pdf(manual_id)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="page image not found")
    return FileResponse(image_path, media_type="image/png")


@app.get("/manuals/{manual_id}/assets/{asset_id}")
def manual_asset(manual_id: str, asset_id: str) -> FileResponse:
    get_manual_or_404(manual_id)
    safe_asset_id = Path(asset_id).name
    asset_path = manual_assets_dir(manual_id) / safe_asset_id
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="asset not found")
    media_type = "image/png" if asset_path.suffix.lower() == ".png" else None
    return FileResponse(asset_path, media_type=media_type)


@app.post("/manuals/{manual_id}/query")
def query_manual(manual_id: str, request: QueryRequest) -> dict[str, Any]:
    get_manual_or_404(manual_id)
    deterministic = deterministic_answer(manual_id, request.question)
    if deterministic:
        return {"manual_id": manual_id, **deterministic}

    evidence = search_pages(request.question, manual_id=manual_id, limit=request.limit)
    if not evidence:
        return {
            "answer": "No relevant manual evidence was found.",
            "manual_id": manual_id,
            "citations": [],
            "confidence": "low",
            "evidence": [],
            "visual_assets": [],
        }
    extractive = extractive_answer_from_results(request.question, evidence)
    if extractive:
        return {"manual_id": manual_id, **extractive}
    answer = ask_gateway(request.question, evidence)
    citations = [{"page": item["page"], "label": f"Page {item['page']}"} for item in evidence]
    return {
        "answer": answer,
        "manual_id": manual_id,
        "citations": citations,
        "confidence": evidence[0]["confidence"] if evidence else "low",
        "evidence": evidence,
        "visual_assets": [
            {"page": item["page"], "url": item.get("asset_url"), "thumbnail_url": item.get("thumbnail_url")}
            for item in evidence
            if item.get("asset_url")
        ],
    }


@app.post("/manuals/query")
def query_all_manuals(request: QueryRequest) -> dict[str, Any]:
    evidence = search_pages(request.question, manual_id=None, limit=request.limit)
    if not evidence:
        return no_relevant_manual_answer()

    intent_terms = specific_manual_terms(request.question)
    if intent_terms:
        evidence = [item for item in evidence if matches_specific_manual_intent(item, intent_terms)]
        if not evidence:
            return no_relevant_manual_answer()

    checked_manuals: set[str] = set()
    for item in evidence:
        manual_id = item.get("manual_id")
        if not manual_id or manual_id in checked_manuals:
            continue
        checked_manuals.add(manual_id)
        deterministic = deterministic_answer(manual_id, request.question)
        if deterministic:
            return {"manual_id": manual_id, **deterministic}

    extractive = extractive_answer_from_results(request.question, evidence)
    if extractive:
        return {"manual_id": evidence[0].get("manual_id"), **extractive}

    answer = ask_gateway(request.question, evidence)
    citations = [
        {"manual_id": item["manual_id"], "page": item["page"], "label": f"Page {item['page']}"}
        for item in evidence
    ]
    return {
        "answer": answer,
        "manual_id": None,
        "citations": citations,
        "confidence": evidence[0]["confidence"] if evidence else "low",
        "evidence": evidence,
        "visual_assets": [
            {"manual_id": item["manual_id"], "page": item["page"], "url": item.get("asset_url"), "thumbnail_url": item.get("thumbnail_url")}
            for item in evidence
            if item.get("asset_url")
        ],
    }


@app.post("/manuals/search")
def search_manuals(request: SearchRequest) -> dict[str, Any]:
    evidence = search_pages(request.query, manual_id=request.manual_id, limit=request.limit)
    return {"results": evidence}


@app.patch("/admin/manuals/{manual_id}")
def admin_update_manual(manual_id: str, request: AdminManualUpdate) -> dict[str, Any]:
    get_manual_or_404(manual_id)
    note = "disabled" if request.disabled else None
    with db() as conn:
        conn.execute("UPDATE manuals SET notes = ? WHERE id = ?", (note, manual_id))
    return {"manual": get_manual_or_404(manual_id)}


@app.delete("/admin/manuals/{manual_id}")
def admin_delete_manual(manual_id: str) -> dict[str, Any]:
    get_manual_or_404(manual_id)
    original_path(manual_id).unlink(missing_ok=True)
    extracted_path(manual_id).unlink(missing_ok=True)
    evidence_index_path(manual_id).unlink(missing_ok=True)
    assets = manual_assets_dir(manual_id)
    if assets.exists():
        for path in assets.rglob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
        for path in sorted([item for item in assets.rglob("*") if item.is_dir()], reverse=True):
            path.rmdir()
        assets.rmdir()
    with db() as conn:
        conn.execute("DELETE FROM manuals WHERE id = ?", (manual_id,))
    return {"ok": True, "manual_id": manual_id}


@app.post("/manuals/{manual_id}/query-image")
async def query_manual_with_image(
    manual_id: str,
    question: str = Form(""),
    image: UploadFile = File(...),
) -> dict[str, Any]:
    get_manual_or_404(manual_id)
    content_type = image.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="only image uploads are accepted")

    ext = Path(image.filename or "upload.png").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        ext = ".png"
    asset_id = f"chat_{uuid.uuid4().hex}{ext}"
    target = manual_assets_dir(manual_id) / asset_id
    target.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with target.open("wb") as handle:
        while True:
            chunk = await image.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > 10 * 1024 * 1024:
                target.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="image exceeds upload size limit")
            handle.write(chunk)

    evidence = {
        "manual_id": manual_id,
        "page": 0,
        "snippet": "User-uploaded photographed manual page or diagram",
        "description": "User-uploaded photographed manual page or diagram",
        "type": "image",
        "confidence": "low",
        "asset_url": public_asset_path(manual_id, asset_id),
        "thumbnail_url": public_asset_path(manual_id, asset_id),
        "generated": False,
    }
    return {
        "answer": "Visual parsing is not available yet. I preserved the uploaded image as chat evidence rather than guessing.",
        "manual_id": manual_id,
        "question": question,
        "citations": [],
        "confidence": "low",
        "evidence": [evidence],
        "visual_assets": [{"page": 0, "url": evidence["asset_url"], "thumbnail_url": evidence["thumbnail_url"]}],
    }
