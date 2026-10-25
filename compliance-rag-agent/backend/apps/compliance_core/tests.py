"""
Unit & Integration Tests for UK Statutory & Engineering Regulation Ingestion.
Tests EAWR 1989 hierarchical parsing, duty holder inference, ESF BPG4 classification, and Pydantic validation.
"""

import os
import sys
import unittest
from pathlib import Path

# Setup paths
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / 'apps'))

# Initialize Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.compliance_core.schemas import RegulatoryChunk, DutyHolderType
from apps.compliance_core.ingestion.parsers.eawr import EAWRParser
from apps.compliance_core.ingestion.parsers.esf_bpg4 import ESFBPG4Parser
from apps.compliance_core.ingestion.service import DocumentIngestionService


from apps.compliance_core.ingestion.extractors import extract_text_from_file


class TestEAWRParser(unittest.TestCase):
    def setUp(self):
        self.parser = EAWRParser()
        self.sample_path = BACKEND_DIR / "data" / "regulations" / "EAW ACT Full.pdf"
        self.raw_text, _ = extract_text_from_file(self.sample_path)

    def test_can_parse(self):
        self.assertTrue(self.parser.can_parse(self.raw_text, "EAW ACT Full.pdf"))
        self.assertFalse(self.parser.can_parse("General unrelated document text", "readme.txt"))

    def test_eawr_hierarchical_extraction(self):
        chunks = self.parser.parse(self.raw_text, "Electricity at Work Regulations 1989")
        self.assertGreater(len(chunks), 10)

        # Map by sub_clause
        chunk_map = {c.sub_clause: c for c in chunks}

        # Verify Regulation 4 sub-clauses
        self.assertIn("Regulation 4(1)", chunk_map)
        self.assertIn("Regulation 4(2)", chunk_map)
        self.assertIn("Regulation 4(3)", chunk_map)
        self.assertIn("Regulation 4(4)", chunk_map)

        # Verify parent title preservation
        self.assertEqual(chunk_map["Regulation 4(1)"].parent_title, "Systems, work activities and protective equipment")

        # Verify statutory duty holder classification:
        # Reg 4(1), 4(2), 4(3) have SFARP qualification -> Reasonably Practicable
        self.assertEqual(chunk_map["Regulation 4(1)"].duty_holder, DutyHolderType.REASONABLY_PRACTICABLE.value)
        self.assertEqual(chunk_map["Regulation 4(2)"].duty_holder, DutyHolderType.REASONABLY_PRACTICABLE.value)
        self.assertEqual(chunk_map["Regulation 4(3)"].duty_holder, DutyHolderType.REASONABLY_PRACTICABLE.value)

        # Reg 4(4) protective equipment is unqualified mandatory -> Absolute
        self.assertEqual(chunk_map["Regulation 4(4)"].duty_holder, DutyHolderType.ABSOLUTE.value)

        # Verify Regulation 14 (Live working) and Regulation 16 (Competence) -> Absolute
        self.assertIn("Regulation 14", chunk_map)
        self.assertEqual(chunk_map["Regulation 14"].duty_holder, DutyHolderType.ABSOLUTE.value)
        self.assertEqual(chunk_map["Regulation 14"].parent_title, "Work on or near live conductors")

        self.assertIn("Regulation 16", chunk_map)
        self.assertEqual(chunk_map["Regulation 16"].duty_holder, DutyHolderType.ABSOLUTE.value)
        self.assertEqual(chunk_map["Regulation 16"].parent_title, "Persons to be competent to prevent danger and injury")

        # Verify raw text is unsevered verbatim text
        clean_reg4_1 = " ".join(chunk_map["Regulation 4(1)"].raw_text.split())
        self.assertIn("All systems shall at all times be of such construction", clean_reg4_1)
        self.assertIn("so far as is reasonably practicable, danger", clean_reg4_1)

        # Verify Regulation 29 statutory defense attribution
        self.assertTrue(chunk_map["Regulation 4(4)"].defense_available)
        self.assertTrue(chunk_map["Regulation 14"].defense_available)
        self.assertTrue(chunk_map["Regulation 16"].defense_available)


class TestESFBPG4Parser(unittest.TestCase):
    def setUp(self):
        self.parser = ESFBPG4Parser()
        self.sample_path = BACKEND_DIR / "data" / "regulations" / "Electrical Safety - best_practice-guide-4_issue-74-v2-dp-170826-protected.pdf"
        self.raw_text, _ = extract_text_from_file(self.sample_path)

    def test_can_parse(self):
        self.assertTrue(self.parser.can_parse(self.raw_text, self.sample_path.name))

    def test_bpg4_classification_code_extraction(self):
        chunks = self.parser.parse(self.raw_text, "Electrical Safety First Best Practice Guide 4")
        self.assertGreater(len(chunks), 10)

        # Check for classification code chunks
        codes = [c.classification_code for c in chunks if c.classification_code]
        self.assertIn("C1", codes)
        self.assertIn("C2", codes)
        self.assertIn("C3", codes)
        self.assertIn("FI", codes)

        c1_chunk = next(c for c in chunks if c.classification_code == "C1")
        self.assertTrue("danger present" in c1_chunk.raw_text.lower() or "c1" in c1_chunk.raw_text.lower())


class TestDocumentIngestionService(unittest.TestCase):
    def test_dry_run_ingest(self):
        service = DocumentIngestionService()
        sample_path = BACKEND_DIR / "data" / "regulations" / "EAW ACT Full.pdf"
        report = service.ingest_file(
            file_path=sample_path,
            store_chroma=False,
            store_db=False
        )
        self.assertEqual(report.standard_name, "Electricity at Work Regulations 1989")
        self.assertGreater(report.total_chunks, 10)
        self.assertIn(DutyHolderType.REASONABLY_PRACTICABLE.value, report.duty_breakdown)
        self.assertIn(DutyHolderType.ABSOLUTE.value, report.duty_breakdown)


class TestRegulationVectorStore(unittest.TestCase):
    def setUp(self):
        from apps.compliance_core.services.vector_store import RegulationVectorStore, LocalSentenceTransformerEmbeddings
        self.vector_store = RegulationVectorStore(
            persist_dir=str(BACKEND_DIR / "test_chroma_storage"),
            collection_name="test_engineering_standards"
        )

    def test_singleton_manager(self):
        from apps.compliance_core.services.vector_store import get_vector_store
        store1 = get_vector_store()
        store2 = get_vector_store()
        self.assertIs(store1, store2)

    def test_clause_identifier_extraction(self):
        # Test regulation and subclause regex extraction
        ids = self.vector_store.extract_clause_identifiers("What does Reg 4(2) require for system maintenance?")
        self.assertTrue(any("4(2)" in i for i in ids))

        ids_live = self.vector_store.extract_clause_identifiers("Is live working permitted under Regulation 14?")
        self.assertTrue(any("14" in i for i in ids_live))

        ids_bs = self.vector_store.extract_clause_identifiers("Verify disconnection time per 411.3.2")
        self.assertIn("411.3.2", ids_bs)

        ids_bpg = self.vector_store.extract_clause_identifiers("Observation classified under Code C1")
        self.assertTrue(any("C1" in i for i in ids_bpg))

    def test_chroma_where_filter_builder(self):
        # Single filter
        filter_single = self.vector_store.build_chroma_where_filter({"duty_holder": "Absolute"})
        self.assertEqual(filter_single, {"duty_holder": "Absolute"})

        # Multiple filters -> $and
        filter_multi = self.vector_store.build_chroma_where_filter({
            "standard": "Electricity at Work Regulations 1989",
            "duty_holder": "Reasonably Practicable",
            "regulation_number": "Regulation 4"
        })
        self.assertIn("$and", filter_multi)
        self.assertEqual(len(filter_multi["$and"]), 3)

    def test_exact_match_scoring(self):
        meta = {
            "sub_clause": "Regulation 4(2)",
            "regulation_number": "Regulation 4",
            "parent_title": "Systems, work activities and protective equipment",
        }
        score, is_exact = self.vector_store._calculate_exact_match_score(
            query_identifiers=["Regulation 4(2)", "4(2)"],
            metadata=meta,
            doc_text="As may be necessary to prevent danger, all systems shall be maintained..."
        )
        self.assertEqual(score, 1.0)
        self.assertTrue(is_exact)


if __name__ == '__main__':
    unittest.main()
