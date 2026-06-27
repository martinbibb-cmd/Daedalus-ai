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
from pydantic import BaseModel


APP_VERSION = "manual-ripper-0.1"
MAX_UPLOAD_BYTES = int(os.getenv("MANUAL_RIPPER_MAX_UPLOAD_BYTES", str(30 * 1024 * 1024)))
STORAGE_ROOT = Path(os.getenv("MANUAL_RIPPER_STORAGE_ROOT", "/srv/daedalus/manuals"))
ORIGINALS_DIR = STORAGE_ROOT / "originals"
EXTRACTED_DIR = STORAGE_ROOT / "extracted"
INDEXES_DIR = STORAGE_ROOT / "indexes"
DB_PATH = STORAGE_ROOT / "metadata.sqlite"


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
    for path in (ORIGINALS_DIR, EXTRACTED_DIR, INDEXES_DIR):
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
                pages.append({"page": index, "text": text})
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


def search_pages(query: str, manual_id: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    terms = tokenize(query)
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
            if score <= 0:
                continue
            snippet = make_snippet(text, terms)
            results.append({
                "manual_id": manual["id"],
                "manual": display_manual_name(manual),
                "page": page["page"],
                "snippet": snippet,
                "score": score,
                "confidence": confidence_for_score(score),
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


@app.post("/manuals/{manual_id}/query")
def query_manual(manual_id: str, request: QueryRequest) -> dict[str, Any]:
    get_manual_or_404(manual_id)
    evidence = search_pages(request.question, manual_id=manual_id, limit=request.limit)
    if not evidence:
        return {"answer": "No relevant manual evidence was found.", "manual_id": manual_id, "evidence": []}
    answer = ask_gateway(request.question, evidence)
    return {
        "answer": answer,
        "manual_id": manual_id,
        "evidence": [
            {"page": item["page"], "snippet": item["snippet"], "confidence": item["confidence"]}
            for item in evidence
        ],
    }


@app.post("/manuals/search")
def search_manuals(request: SearchRequest) -> dict[str, Any]:
    evidence = search_pages(request.query, manual_id=request.manual_id, limit=request.limit)
    return {"results": evidence}
