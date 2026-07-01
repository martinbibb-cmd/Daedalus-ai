import json
import sqlite3
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import main


def configure_storage(tmp_path, monkeypatch):
    root = tmp_path / "manuals"
    monkeypatch.setattr(main, "STORAGE_ROOT", root)
    monkeypatch.setattr(main, "ORIGINALS_DIR", root / "originals")
    monkeypatch.setattr(main, "EXTRACTED_DIR", root / "extracted")
    monkeypatch.setattr(main, "INDEXES_DIR", root / "indexes")
    monkeypatch.setattr(main, "ASSETS_DIR", root / "assets")
    monkeypatch.setattr(main, "DB_PATH", root / "metadata.sqlite")
    main.ensure_storage()
    return root


def seed_manual(manual_id="greenstar-ri"):
    pages = [
        {
            "page": 4,
            "text": "Warnings and clearances. Minimum side clearance 5 mm. Keep combustibles away.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-4-thumb.png"},
        },
        {
            "page": 12,
            "text": (
                "Greenstar Ri ErP technical data. Appliance dimensions H x W x D "
                "600 mm x 390 mm x 270 mm. Overall dimensions are listed in millimetres."
            ),
            "layout_blocks": [],
            "tables": [
                {"type": "table-row", "text": "Appliance dimensions H x W x D 600 mm x 390 mm x 270 mm"}
            ],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-12-thumb.png"},
        },
    ]
    main.extracted_path(manual_id).write_text(json.dumps({"manual_id": manual_id, "pages": pages}), encoding="utf-8")
    with sqlite3.connect(main.DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO manuals (id, filename, manufacturer, model, appliance_type, uploaded_at, page_count, extraction_status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                manual_id,
                "greenstar-ri-erp.pdf",
                "Worcester",
                "Greenstar Ri ErP",
                "boiler",
                datetime.now(timezone.utc).isoformat(),
                2,
                "complete",
            ),
        )
    return manual_id


def test_greenstar_ri_erp_dimensions_are_answered_with_visual_evidence(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What are the dimensions?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert "H 600 mm x W 390 mm x D 270 mm" in body["answer"]
    assert body["confidence"] == "high"
    assert body["citations"] == [{"page": 12, "label": "Page 12"}]
    assert body["evidence"][0]["type"] == "dimension"
    assert body["evidence"][0]["asset_url"] == f"/manuals/{manual_id}/pages/12/image"
    assert body["visual_assets"][0]["url"] == f"/manuals/{manual_id}/pages/12/image"


def test_dimension_answer_does_not_say_not_specified_when_evidence_exists(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "Is the width specified?", "limit": 5})

    assert response.status_code == 200
    answer = response.json()["answer"].lower()
    assert "not specified" not in answer
    assert "not in the manual" not in answer
    assert "390 mm" in answer


def test_dimension_answer_does_not_dump_unrelated_clearance_warning(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "Give me the boiler dimensions", "limit": 5})

    assert response.status_code == 200
    serialized = json.dumps(response.json()).lower()
    assert "minimum side clearance" not in serialized
    assert "combustibles" not in serialized
