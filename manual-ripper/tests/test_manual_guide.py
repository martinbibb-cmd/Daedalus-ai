import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
            "page": 7,
            "text": (
                "APPLIANCE INFORMATION 3 APPLIANCE INFORMATION 3.1 APPLIANCE "
                "Fig. 1 Appliance 390mm 270mm *600mm to top of case front 590mm* "
                "STANDARD PACKAGE"
            ),
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {
                "thumbnail_url": f"/manuals/{manual_id}/assets/page-7-thumb.png",
                "embedded_images": [{"asset_id": "page-7-image-1.png", "type": "embedded-image"}],
            },
        },
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


def seed_manual_with_invalid_technical_data_dimension_page(manual_id="greenstar-ri-page8"):
    pages = [
        {
            "page": 8,
            "text": (
                "APPLIANCE INFORMATION 3.2 TECHNICAL DATA Natural Gas Appliances. "
                "Gas flow rate. Central Heating. Maximum rated heat output. "
                "Maximum flow temperature. Maximum permissible operating pressure. "
                "Packaged appliance weight 31 kg. Total appliance weight 27.4 kg."
            ),
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-8-thumb.png"},
        },
        {
            "page": 22,
            "text": "Pipe work dimensions. Gas 55mm. Condensate 210mm. Flow 285mm. Return 350mm.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-22-thumb.png"},
        },
        {
            "page": 55,
            "text": "Fig. 81 Initial location of the clamping plate. Underside view of the clamping plate.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-55-thumb.png"},
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
    assert "Height: 600 mm" in body["answer"]
    assert "Width: 390 mm" in body["answer"]
    assert "Depth: 270 mm" in body["answer"]
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


def test_visual_question_returns_page_image_without_llm_denial(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "Show me the technical data table", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["deterministic"] is True
    assert "Best match: Page 12" in body["answer"]
    assert "not explicitly" not in body["answer"].lower()
    assert body["evidence"][0]["type"] == "page-image"
    assert body["evidence"][0]["asset_url"] == f"/manuals/{manual_id}/pages/12/image"


def test_dimension_retrieval_rejects_generic_technical_data_page_without_dimensions(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_invalid_technical_data_dimension_page()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What are the appliance dimensions?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["confidence"] == "low"
    assert body["citations"] == []
    assert body["evidence"] == []
    assert "technical data pages" in body["answer"].lower()
    assert "page 8" not in json.dumps(body).lower()
    assert "page 55" not in json.dumps(body).lower()


def test_greenstar_ri_page_7_visual_fallback_returns_case_size_without_depth_inference(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What is the size of the case of this boiler?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    answer = body["answer"].lower()
    assert body["fallback"] == "visual"
    assert body["citations"] == [{"page": 7, "label": "Page 7"}]
    assert body["evidence"][0]["type"] == "visual-dimension"
    assert "width: 390 mm" in answer
    assert "case-front height: 590 mm" in answer
    assert "to top of case front: 600 mm" in answer
    assert "depth: not confirmed" in answer
    assert "270 mm annotation" in answer
    assert "depth: 270 mm" not in answer
