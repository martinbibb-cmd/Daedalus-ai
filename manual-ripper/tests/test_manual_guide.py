import json
import re
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
    monkeypatch.setattr(main, "FACTS_DIR", root / "facts")
    monkeypatch.setattr(main, "INDEXES_DIR", root / "indexes")
    monkeypatch.setattr(main, "ASSETS_DIR", root / "assets")
    monkeypatch.setattr(main, "REGRESSIONS_DIR", root / "regressions")
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
                "600 mm x 390 mm x 270 mm. Lift weight 27.4 kg. "
                "Packaged appliance weight 31 kg. Overall dimensions are listed in millimetres."
            ),
            "layout_blocks": [],
            "tables": [
                {"type": "table-row", "text": "Appliance dimensions H x W x D 600 mm x 390 mm x 270 mm"},
                {"type": "table-row", "text": "Lift weight 27.4 kg"},
                {"type": "table-row", "text": "Packaged appliance weight 31 kg"},
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


def seed_unrelated_manual(manual_id="shower-pack"):
    pages = [
        {
            "page": 31,
            "text": "Other Packs CSHO6027 Deep Cool Touch Bar Mixer Shower price list and fitting pack.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-31-thumb.png"},
        },
        {
            "page": 89,
            "text": "Building regulations and construction stages. Show thermal continuity and insulation details.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-89-thumb.png"},
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
                "shower-packs.pdf",
                "Depot",
                "Shower packs",
                "accessory",
                datetime.now(timezone.utc).isoformat(),
                2,
                "complete",
            ),
        )
    return manual_id


def seed_part_l_manual(manual_id="part-l"):
    pages = [
        {
            "page": 3,
            "text": "Approved Documents provide guidance on the Building Regulations 2010 for England.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-3-thumb.png"},
        },
        {
            "page": 42,
            "text": "Fig. 46 Replacing outer case. Install the bottom panel carefully and observe regulations.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-42-thumb.png"},
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
                "approved-document-l.pdf",
                "HM Government",
                "Approved Document L",
                "building-regulation",
                datetime.now(timezone.utc).isoformat(),
                2,
                "complete",
            ),
        )
    return manual_id


def seed_greenstar_15ri_weight_manual(manual_id="greenstar-15ri"):
    pages = [
        {
            "page": 8,
            "text": "Greenstar 15Ri technical data. Lift weight 27.4 kg. Total appliance weight 27.4 kg. Packaged appliance weight 31 kg.",
            "layout_blocks": [],
            "tables": [
                {"type": "table-row", "text": "Lift weight 27.4 kg"},
                {"type": "table-row", "text": "Total appliance weight 27.4 kg"},
                {"type": "table-row", "text": "Packaged appliance weight 31 kg"},
            ],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-8-thumb.png"},
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
                "greenstar-15ri.pdf",
                "Worcester",
                "Greenstar 15Ri",
                "boiler",
                datetime.now(timezone.utc).isoformat(),
                1,
                "complete",
            ),
        )
    return manual_id


def seed_manual_with_flue_tables(manual_id="greenstar-ri-flue"):
    pages = [
        {
            "page": 20,
            "text": (
                "Terminal position clearances table. "
                "Terminal clearance to an opening, openable window or air vent - 300 mm. "
                "Terminal clearance to internal or external corner - 150 mm."
            ),
            "layout_blocks": [],
            "tables": [
                {"type": "table-row", "text": "Terminal clearance to an opening, openable window or air vent - 300 mm"},
                {"type": "table-row", "text": "Terminal clearance to internal or external corner/change of fabric - 150 mm"},
            ],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-20-thumb.png"},
        },
        {
            "page": 28,
            "text": (
                "Extended horizontal flue. Maximum flue length (mm) 60/100 80/125. "
                "Extended horizontal flue 4,600 13,000. Notice: Effective flue lengths: "
                "each 90 degree bend is equivalent to 2 metres of straight flue; "
                "each 45 degree bend is equivalent to 1 metre of straight flue."
            ),
            "layout_blocks": [],
            "tables": [
                {"type": "table-row", "text": "Extended horizontal flue maximum flue length (mm) 60/100 80/125 4,600 13,000"},
                {"type": "table-row", "text": "Each 90 degree bend is equivalent to 2 metres of straight flue"},
                {"type": "table-row", "text": "Each 45 degree bend is equivalent to 1 metre of straight flue"},
            ],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-28-thumb.png"},
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
                "greenstar-ri-flue.pdf",
                "Worcester",
                "Greenstar Ri",
                "boiler",
                datetime.now(timezone.utc).isoformat(),
                2,
                "complete",
            ),
        )
    return manual_id


def seed_manual_with_collapsed_clearance_table(manual_id="greenstar-ri-collapsed-clearance"):
    pages = [
        {
            "page": 23,
            "text": (
                "Terminal position clearances table. Terminal clearance to an opening, openable window or air vent 300 mm "
                "Terminal clearance to internal or external corner/change of fabric 150 mm"
            ),
            "layout_blocks": [],
            "tables": [
                {
                    "type": "table-row",
                    "text": (
                        "Terminal clearance to an opening, openable window or air vent 300 mm "
                        "Terminal clearance to internal or external corner/change of fabric 150 mm"
                    ),
                },
            ],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-23-thumb.png"},
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
                "greenstar-ri-clearances.pdf",
                "Worcester",
                "Greenstar Ri",
                "boiler",
                datetime.now(timezone.utc).isoformat(),
                1,
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


def seed_manual_with_visual_case_dimensions_only(manual_id="greenstar-ri-visual"):
    pages = [
        {
            "page": 7,
            "text": (
                "APPLIANCE INFORMATION 3.1 APPLIANCE Fig. 1 Appliance "
                "390mm 270mm *600mm to top of case front 590mm* STANDARD PACKAGE"
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
            "page": 8,
            "text": "3.2 TECHNICAL DATA Gas flow rate. Maximum rated heat output. Total appliance weight 27.4 kg.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-8-thumb.png"},
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
    assert "600 mm tall" in body["answer"]
    assert "390 mm wide" in body["answer"]
    assert "270 mm deep" in body["answer"]
    assert "Best matching manual text" not in body["answer"]
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
    assert body["answer"] == main.MISSING_EXACT_FACT_ANSWER
    assert "page 8" not in json.dumps(body).lower()
    assert "page 55" not in json.dumps(body).lower()


def test_greenstar_ri_page_7_visual_fallback_returns_case_size_without_depth_inference(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_visual_case_dimensions_only()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What is the size of the case of this boiler?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    answer = body["answer"].lower()
    assert body["source"] == "evidence-store"
    assert body["citations"] == [{"page": 7, "label": "Page 7"}]
    assert body["evidence"][0]["type"] == "visual-dimension"
    assert "390 mm wide" in answer
    assert "case-front height: 590 mm" in answer
    assert "to top of case front: 600 mm" in answer
    assert "depth: not confirmed" not in answer
    assert "270 mm annotation" not in answer
    assert "depth: 270 mm" not in answer


def test_ingest_stores_greenstar_page_7_dimensions_as_visual_evidence(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_visual_case_dimensions_only()
    client = TestClient(main.app)

    response = client.get(f"/manuals/{manual_id}/evidence")

    assert response.status_code == 200
    evidence = response.json()["evidence"]
    page_7 = [item for item in evidence if item["source_page"] == 7]
    assert {item["field"] for item in page_7} >= {"width", "case_front_height", "top_of_case_front", "depth"}
    assert any(item["field"] == "width" and item["value"] == 390 and item["source_type"] == "visual-dimension" for item in page_7)
    assert any(item["field"] == "depth" and item["value"] is None and item["validation_status"] == "unconfirmed" for item in page_7)


def test_show_page_7_returns_page_image_url(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_visual_case_dimensions_only()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "show the image on page 7", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["citations"] == [{"page": 7, "label": "Page 7", "url": f"/manuals/{manual_id}/pages/7/image"}]
    assert body["visual_assets"][0]["url"] == f"/manuals/{manual_id}/pages/7/image"


def test_no_generated_image_is_treated_as_source_evidence(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_visual_case_dimensions_only()
    client = TestClient(main.app)

    response = client.get(f"/manuals/{manual_id}/evidence")

    assert response.status_code == 200
    assert response.json()["source_policy"]["generated_images_as_source"] is False
    assert all(item["generated"] is False for item in response.json()["evidence"])


def test_global_query_returns_extractive_text_before_llm_for_simple_search(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = "weight-manual"
    pages = [
        {
            "page": 3,
            "text": "Lift weight is listed in the installation data. Appliance lift weight 27.4 kg.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-3-thumb.png"},
        },
        {
            "page": 8,
            "text": "Part L and Part P generic electrical guidance.",
            "layout_blocks": [],
            "tables": [],
            "key_values": [],
            "assets": {"thumbnail_url": f"/manuals/{manual_id}/assets/page-8-thumb.png"},
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
                "weight.pdf",
                "Worcester",
                "Greenstar Ri ErP",
                "boiler",
                datetime.now(timezone.utc).isoformat(),
                2,
                "complete",
            ),
        )
    client = TestClient(main.app)

    response = client.post("/manuals/query", json={"question": "Weight is mentioned on page 3, where is the information?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "extractive-search"
    assert "Page 3:" in body["answer"]
    assert "27.4 kg" in body["answer"]
    assert body["citations"][0]["page"] == 3
    assert body["evidence"][0]["type"] == "page-text"
    assert "Page 3 image is available" not in body["answer"]


def test_global_15ri_weight_uses_weight_fact_not_part_l_text(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    seed_part_l_manual()
    seed_greenstar_15ri_weight_manual()
    client = TestClient(main.app)

    response = client.post("/manuals/query", json={"question": "How heavy is the 15ri?", "limit": 6})

    assert response.status_code == 200
    body = response.json()
    assert body["manual_id"] == "greenstar-15ri"
    assert body["source"] == "typed-weight-facts"
    assert body["answer"] == "Lift weight: 27.4 kg; packaged: 31 kg"
    assert "Approved Documents" not in body["answer"]
    assert all(item["category"] == "weight" for item in body["evidence"])
    assert body["citations"] == [{"page": 8, "label": "Page 8"}]


def test_direct_fact_answers_use_page_reader_not_locator_snippet(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_flue_tables()
    original_search_pages = main.search_pages

    def misleading_locator(query, manual_id=None, limit=10):
        results = original_search_pages(query, manual_id=manual_id, limit=limit)
        for item in results:
            if item["page"] == 20:
                item["snippet"] = "Misleading search snippet says terminal clearance to an opening is 600 mm."
                item["description"] = item["snippet"]
        return results

    monkeypatch.setattr(main, "search_pages", misleading_locator)
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What is the terminal clearance to an openable window?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Terminal clearance to openable window or air vent: 300 mm"
    assert "600 mm" not in body["answer"]
    assert body["debug"]["selected_pages"] == [20]
    assert body["debug"]["final_facts_used"][0]["value"] == 300


def test_direct_fact_answer_numbers_have_fact_objects(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "How big is the Ri?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    numbers = re.findall(r"\d+(?:\.\d+)?", body["answer"])
    fact_values = {str(item["value"]).rstrip("0").rstrip(".") for item in body["evidence"] if item.get("value") is not None}
    assert numbers
    assert all(number.rstrip("0").rstrip(".") in fact_values for number in numbers)
    assert all(item.get("manual_id") and item.get("page") and item.get("snippet") and item.get("type") and item.get("unit") for item in body["evidence"])


def test_global_ri_width_query_uses_matching_boiler_manual_not_unrelated_docs(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    seed_manual("greenstar-ri")
    seed_unrelated_manual("shower-pack")
    client = TestClient(main.app)

    response = client.post("/manuals/query", json={"question": "How wide is the ri?", "limit": 6})

    assert response.status_code == 200
    body = response.json()
    assert body["manual_id"] == "greenstar-ri"
    assert "600 mm tall" in body["answer"]
    assert "390 mm wide" in body["answer"]
    assert "270 mm deep" in body["answer"]
    assert "Lift weight: 27.4 kg; packaged: 31 kg" in body["answer"]
    assert body["citations"][0]["page"] == 12
    assert all(item["manual_id"] == "greenstar-ri" for item in body["evidence"])
    assert "Shower" not in body["answer"]
    assert "building regulations" not in body["answer"].lower()
    assert "Best matching manual text" not in body["answer"]
    assert "Match count" not in body["answer"]


def test_global_specific_ri_query_rejects_unrelated_global_results(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    seed_unrelated_manual("shower-pack")
    client = TestClient(main.app)

    response = client.post("/manuals/query", json={"question": "How wide is the ri?", "limit": 6})

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == main.MISSING_EXACT_FACT_ANSWER
    assert body["confidence"] == "low"
    assert body["evidence"] == []
    assert body["citations"] == []


def test_terminal_clearance_opening_answers_from_matching_table_row(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_flue_tables()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What is the terminal clearance to an openable window?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "typed-table-facts"
    assert body["answer"] == "Terminal clearance to openable window or air vent: 300 mm"
    assert "150 mm" not in body["answer"]
    assert body["citations"] == [{"page": 20, "label": "Page 20"}]
    assert body["evidence"][0]["type"] == "terminal_clearance"
    assert body["evidence"][0]["category"] == "terminal_clearance"
    assert "openable window" in body["evidence"][0]["field"]
    index = main.load_evidence_index(manual_id)
    assert {
        "type": "terminal_clearance",
        "condition": "to openable window or air vent",
        "value_mm": 300,
        "page": 20,
    }.items() <= index["facts"][0].items()
    stored_facts = json.loads(main.facts_path(manual_id).read_text(encoding="utf-8"))
    assert stored_facts["manual_id"] == manual_id
    assert any(item["type"] == "terminal_clearance" and item["value_mm"] == 300 for item in stored_facts["facts"])
    assert "Best matching manual text" not in body["answer"]


def test_terminal_clearance_corner_answers_from_matching_table_row(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_flue_tables()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What clearance is required to an internal corner?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "typed-table-facts"
    assert body["answer"] == "Terminal clearance internal or external corner/change of fabric: 150 mm"
    assert "300 mm" not in body["answer"]
    assert body["citations"] == [{"page": 20, "label": "Page 20"}]
    assert body["evidence"][0]["type"] == "terminal_clearance"
    assert "internal or external corner/change of fabric" in body["evidence"][0]["field"]
    assert "Best matching manual text" not in body["answer"]


def test_collapsed_terminal_clearance_row_selects_only_matching_condition(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_collapsed_clearance_table()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What clearance is required to an internal corner?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "typed-table-facts"
    assert "150 mm" in body["answer"]
    assert "300 mm" not in body["answer"]
    assert body["citations"] == [{"page": 23, "label": "Page 23"}]
    assert "Best matching manual text" not in body["answer"]


def test_terminal_clearance_ambiguous_opening_and_corner_asks_clarification(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_flue_tables()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What is the terminal clearance?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "typed-table-facts"
    assert body["answer"] == "Do you mean an opening/window or an internal corner?"
    assert body["evidence"] == []


def test_max_flue_length_with_90_elbows_uses_flue_facts_not_clearance_table(tmp_path, monkeypatch):
    configure_storage(tmp_path, monkeypatch)
    manual_id = seed_manual_with_flue_tables()
    client = TestClient(main.app)

    response = client.post(f"/manuals/{manual_id}/query", json={"question": "What is the maximum flue length with 90 degree elbows?", "limit": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "typed-table-facts"
    assert "Maximum flue length: 4.6 m for 60/100; 13 m for 80/125" in body["answer"]
    assert "Bend deductions: 45° = 1 m; 90° = 2 m" in body["answer"]
    assert body["citations"] == [{"page": 28, "label": "Page 28"}]
    assert all(item["category"] == "flue_length" for item in body["evidence"])
    assert all(item["value"] is not None and item["unit"] for item in body["evidence"])
    assert "300 mm" not in body["answer"]
    assert "150 mm" not in body["answer"]
    assert "Best matching manual text" not in body["answer"]
