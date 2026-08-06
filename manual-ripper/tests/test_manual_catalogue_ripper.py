import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import fitz

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import manual_catalogue_ripper as ripper
import platform_candidate_sql as platform_sql
import promote_reviewed_catalogue as promoter


class ManualCatalogueRipperTests(unittest.TestCase):
    def test_platform_candidate_import_preserves_existing_review_decisions(self):
        entry = {
            "id": "boiler-vaillant-ecofit-pure-combi",
            "applianceType": "boiler",
            "make": "Vaillant",
            "model": "ecoFIT pure Combi",
            "primitive": "cuboid",
            "dimensions": {"cuboid": {"widthMm": 390, "heightMm": 702, "depthMm": 295}},
            "clearanceMm": {"sideMm": None, "aboveMm": None, "belowMm": None, "frontMm": None},
            "manualSource": "manufacturer's-manual.pdf; dimensions p7",
            "provenance": [{"field": "width", "value": 390}],
        }

        sql = platform_sql.build_sql([entry], "2026-08-06T00:00:00+00:00")

        self.assertIn("INSERT INTO manual_catalogue_candidates", sql)
        self.assertNotIn("INSERT OR REPLACE", sql)
        self.assertIn("AND NOT EXISTS", sql)
        self.assertNotIn("BEGIN TRANSACTION", sql)
        self.assertNotIn("COMMIT", sql)
        self.assertIn("manual-candidate:xeon:boiler-vaillant-ecofit-pure-combi", sql)
        self.assertIn("manufacturer''s-manual.pdf", sql)

    def test_uses_original_filename_from_metadata_for_uuid_named_manuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manual_id = "6a088cff-853f-4a76-8f01-be24c778b00a"
            manual = root / f"{manual_id}.txt"
            manual.write_text(
                "\n".join(
                    [
                        "Worcester Bosch installation instructions for open vented boilers.",
                        "Appliance dimensions H x W x D 600 mm x 390 mm x 270 mm.",
                        "Minimum side clearance 5 mm.",
                        "Above clearance 170 mm.",
                        "Below clearance 200 mm.",
                        "Front clearance 600 mm.",
                    ]
                ),
                encoding="utf-8",
            )
            metadata_db = root / "metadata.sqlite"
            with sqlite3.connect(metadata_db) as connection:
                connection.execute("CREATE TABLE manuals (id TEXT, filename TEXT)")
                connection.execute(
                    "INSERT INTO manuals (id, filename) VALUES (?, ?)",
                    (
                        manual_id,
                        "Greenstar_9-24_Ri_Installation_and_Servicing_Instructions.pdf",
                    ),
                )

            output = root / "candidates.json"
            report = root / "report.json"
            self.assertEqual(ripper.run(root, output, report, metadata_db), 0)

            entries = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(entries[0]["model"], "Greenstar Ri ErP+ 9-24")
            self.assertIn("Greenstar_9-24_Ri", entries[0]["manualSource"])

    def test_reads_pdf_with_existing_pymupdf_when_pdftotext_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            manual = Path(tmp) / "manual.pdf"
            with fitz.open() as document:
                page = document.new_page()
                page.insert_text((72, 72), "Appliance dimensions H x W x D 600 mm x 390 mm x 270 mm")
                document.save(manual)

            real_which = shutil.which
            with mock.patch.object(
                ripper.shutil,
                "which",
                side_effect=lambda command: None if command == "pdftotext" else real_which(command),
            ):
                pages = ripper.read_pdf_file(manual)

            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0][0], 1)
            self.assertIn("600 mm x 390 mm x 270 mm", pages[0][1])

    def test_builds_candidate_with_dimensions_clearances_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manual = root / "Greenstar_9-24_Ri_Installation_and_Servicing_Instructions.txt"
            manual.write_text(
                "\n".join(
                    [
                        "Worcester Bosch Greenstar Ri ErP+ 9-24 Installation and Servicing Instructions",
                        "Appliance dimensions H x W x D 600 mm x 390 mm x 270 mm.",
                        "Minimum side clearance 5 mm.",
                        "Above clearance 170 mm.",
                        "Below clearance 200 mm.",
                        "Front clearance 600 mm.",
                    ]
                ),
                encoding="utf-8",
            )

            output = root / "manual-derived-van-stock.candidates.json"
            report = root / "manual-ripper-report.json"

            self.assertEqual(ripper.run(root, output, report), 0)

            entries = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            self.assertEqual(entry["make"], "Worcester Bosch")
            self.assertEqual(entry["model"], "Greenstar Ri ErP+ 9-24")
            self.assertEqual(
                entry["dimensions"]["cuboid"],
                {"widthMm": 390, "heightMm": 600, "depthMm": 270},
            )
            self.assertEqual(
                entry["clearanceMm"],
                {"sideMm": 5, "aboveMm": 170, "belowMm": 200, "frontMm": 600},
            )
            self.assertEqual(entry["reviewStatus"], "candidate")
            self.assertTrue(entry["reviewRequired"])
            self.assertTrue(all(item["evidenceClass"] == "manual_evidence" for item in entry["provenance"]))

    def test_does_not_create_stock_entry_when_dimensions_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manual = root / "boiler.txt"
            manual.write_text("Worcester Bosch Greenstar Ri manual. Above clearance 170 mm.", encoding="utf-8")

            output = root / "candidates.json"
            report = root / "report.json"

            self.assertEqual(ripper.run(root, output, report), 0)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), [])
            report_json = json.loads(report.read_text(encoding="utf-8"))
            self.assertIn("missing_dimensions:height,width,depth", report_json["reports"][0]["reviewReasons"])

    def test_keeps_reviewable_dimensions_when_clearances_are_not_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manual = root / "ecofit-pure-combi-installation-and-maintenance-instructions.pdf.txt"
            manual.write_text(
                "Appliance dimensions H x W x D 720 mm x 440 mm x 338 mm.",
                encoding="utf-8",
            )

            output = root / "candidates.json"
            report = root / "report.json"
            self.assertEqual(ripper.run(root, output, report), 0)

            entries = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["make"], "Vaillant")
            self.assertEqual(entries[0]["model"], "ecoFIT pure Combi")
            self.assertEqual(entries[0]["extractionStatus"], "candidate_partial")
            self.assertEqual(
                entries[0]["clearanceMm"],
                {"sideMm": None, "aboveMm": None, "belowMm": None, "frontMm": None},
            )

    def test_extracts_labelled_appliance_dimension_table(self):
        evidence = ripper.extract_dimensions(
            """Table 3 Appliance and flue outlet dimensions
Description
Dimensions (mm)
X
Appliance width
400
Y
Appliance height
724
Z
Appliance depth
310
""",
            "Greenstar-4000-Combi-IM.pdf",
            9,
        )

        self.assertEqual(
            {item.field: item.value for item in evidence},
            {"height": 724, "width": 400, "depth": 310},
        )

    def test_extracts_repeated_variant_dimension_table_without_repeating_width(self):
        evidence = ripper.extract_dimensions(
            """Product dimensions, width
390 mm
390 mm
390 mm
Product dimensions, depth
280 mm
280 mm
280 mm
Product dimensions, height
702 mm
702 mm
702 mm
Net weight
32 kg
""",
            "Energy7-combi.pdf",
            9,
        )

        self.assertEqual(
            {item.field: item.value for item in evidence},
            {"height": 702, "width": 390, "depth": 280},
        )

    def test_rejects_family_dimension_when_variants_have_different_depths(self):
        evidence = ripper.extract_dimensions(
            """Boiler dimension, width
440 mm
440 mm
Boiler dimension, height
720 mm
720 mm
Boiler dimension, depth
338 mm
372 mm
Mounting weight
36 kg
""",
            "ecotec-plus-combi-and-system.pdf",
            8,
        )

        self.assertEqual(evidence, [])

    def test_does_not_treat_a_clearance_reduction_as_the_clearance(self):
        evidence = ripper.extract_clearances(
            "The front servicing clearance can be reduced by 150mm when other criteria are met.",
            "Greenstar-4000-Combi.pdf",
            18,
        )

        self.assertEqual(evidence, [])

    def test_excludes_preheat_kits_from_boiler_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            manual = Path(tmp) / "Greenstar-4000-Combi-Preheat-Kit-Inst-Serv.pdf.txt"
            manual.write_text(
                "Worcester Bosch Greenstar 4000 preheat kit. Dimensions 100 x 100 x 100 mm.",
                encoding="utf-8",
            )

            entry, report = ripper.parse_manual(manual)

            self.assertIsNone(entry)
            self.assertEqual(report["reviewReasons"], ["unsupported_appliance_type:preheat_kit"])

    def test_prefers_filename_manufacturer_over_cross_brand_mentions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manual = root / "Ideal System Boiler Quick Reference Guide.txt"
            manual.write_text(
                "\n".join(
                    [
                        "Ideal Logic System 24kW",
                        "Dimensions: H-700mm W-395mm D-278mm.",
                        "Competitor comparison includes Worcester Bosch and Vaillant.",
                    ]
                ),
                encoding="utf-8",
            )

            output = root / "candidates.json"
            report = root / "report.json"

            self.assertEqual(ripper.run(root, output, report), 0)
            report_json = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(report_json["reports"][0]["make"], "Ideal")
            self.assertNotEqual(report_json["reports"][0]["make"], "Worcester Bosch")

    def test_ambiguous_multi_brand_document_does_not_invent_manufacturer(self):
        self.assertIsNone(
            ripper.find_make(
                "This comparison covers Worcester Bosch, Ideal and Vaillant boilers.",
                "boiler-comparison.txt",
            )
        )

    def test_greenstar_model_family_can_resolve_worcester_make(self):
        text = "\n".join(
            [
                "Greenstar Ri ErP+ 9-24 Installation and Servicing Instructions",
                "Worcester Bosch appears in the manual footer.",
                "Ideal appears in a standards or comparison note.",
            ]
        )

        model = ripper.find_model(text, "Greenstar_9-24_Ri_Installation_and_Servicing_Instructions.txt")
        self.assertEqual(model, "Greenstar Ri ErP+ 9-24")
        self.assertIsNone(ripper.find_make(text, "Greenstar_9-24_Ri_Installation_and_Servicing_Instructions.txt"))
        self.assertEqual(ripper.infer_make_from_model_family(model, text), "Worcester Bosch")

    def test_promotes_reviewed_candidate_to_capture_catalogue_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.json"
            output = root / "manual-derived-van-stock.json"
            approval = root / "approval.json"
            candidates.write_text(
                json.dumps(
                    [
                        {
                            "id": "boiler-worcester-bosch-greenstar-ri-erp-plus-9-24",
                            "applianceType": "boiler",
                            "make": "Worcester Bosch",
                            "model": "Greenstar Ri ErP+ 9-24",
                            "primitive": "cuboid",
                            "dimensions": {"cuboid": {"widthMm": 390, "heightMm": 600, "depthMm": 270}},
                            "clearanceMm": {"sideMm": 5, "aboveMm": 170, "belowMm": 200, "frontMm": 600},
                            "manualSource": "manual.pdf; dimensions p7; clearances p20,p32",
                            "reviewStatus": "candidate",
                            "provenance": [{"field": "width", "value": 390}],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                promoter.promote(candidates, output, approval, "unit-test-reviewer"),
                0,
            )

            promoted = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(promoted), 1)
            self.assertNotIn("provenance", promoted[0])
            self.assertNotIn("reviewStatus", promoted[0])
            self.assertEqual(promoted[0]["clearanceMm"]["frontMm"], 600)
            approval_record = json.loads(approval.read_text(encoding="utf-8"))
            self.assertEqual(approval_record["promotedEntries"], 1)

    def test_deduplicates_candidates_and_prefers_real_manual_sources(self):
        synthetic = {
            "id": "boiler-worcester-bosch-greenstar-ri-erp-plus-9-24",
            "manualSource": "worcester-greenstar-ri-synthetic-manual.txt",
            "provenance": [{"field": "width", "sourcePage": None}],
        }
        real = {
            "id": "boiler-worcester-bosch-greenstar-ri-erp-plus-9-24",
            "manualSource": "Greenstar_9-24_Ri_Installation_and_Servicing_Instructions.pdf; dimensions p7",
            "provenance": [{"field": "width", "sourcePage": 7}],
        }

        entries, duplicates = ripper.deduplicate_entries([synthetic, real])

        self.assertEqual(duplicates, ["boiler-worcester-bosch-greenstar-ri-erp-plus-9-24"])
        self.assertEqual(len(entries), 1)
        self.assertIn(".pdf", entries[0]["manualSource"])


if __name__ == "__main__":
    unittest.main()
