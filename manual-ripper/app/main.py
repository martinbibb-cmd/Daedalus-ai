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
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel


APP_VERSION = "manual-ripper-0.4-guide"
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
VISUAL_INTENT_TERMS = ("show me", "show", "diagram", "exploded", "image", "picture", "where is", "give me the page", "what page", "open", "table")


class QueryRequest(BaseModel):
    question: str
    limit: int = 5


class SearchRequest(BaseModel):
    query: str
    manual_id: str | None = None
    limit: int = 10


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

    return get_manual_or_404(manual_id)


def load_pages(manual_id: str) -> list[dict[str, Any]]:
    path = extracted_path(manual_id)
    if not path.exists():
        extract_pdf(manual_id)
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("pages", [])


def tokenize(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]{3,}", text.lower()) if token not in {"the", "and", "for", "with", "that", "this"}]


def query_terms(query: str) -> list[str]:
    terms = tokenize(query)
    lowered = query.lower()
    if any(term in lowered for term in ("dimension", "dimensions", "size", "height", "width", "depth", "h x w", "hxw")):
        terms.extend(tokenize(" ".join(DIMENSION_TERMS)))
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
        if manual["extraction_status"] != "complete":
            try:
                manual = extract_pdf(manual["id"])
            except HTTPException:
                continue
        for page in load_pages(manual["id"]):
            text = page.get("text", "")
            lowered = text.lower()
            score = sum(lowered.count(term) for term in terms)
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
    return any(term in lowered for term in ("dimension", "dimensions", "size", "height", "width", "depth", "h x w", "hxw"))


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

    strong_terms = (
        "appliance dimensions",
        "appliance measurements",
        "overall dimensions",
        "dimensional drawing",
        "outline drawing",
        "side view",
    )
    if any(term in lowered for term in strong_terms):
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
    return {
        "answer": "I could not find validated appliance dimension evidence in the extracted manual text. I rejected generic technical data pages because they did not contain dimensions, height, width, depth, H x W x D, appliance/overall dimensions, or a dimensional drawing reference.",
        "confidence": "low",
        "citations": [],
        "evidence": [],
        "visual_assets": [],
        "deterministic": True,
    }


def deterministic_answer(manual_id: str, question: str) -> dict[str, Any] | None:
    pages = load_pages(manual_id)
    if is_dimension_question(question):
        return deterministic_dimension_answer(manual_id, pages, question)
    if is_visual_question(question):
        return deterministic_visual_answer(manual_id, question)
    return None


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


@app.post("/manuals/search")
def search_manuals(request: SearchRequest) -> dict[str, Any]:
    evidence = search_pages(request.query, manual_id=request.manual_id, limit=request.limit)
    return {"results": evidence}
