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

from apps.compliance_core.schemas import (
    RegulatoryChunk,
    DutyHolderType,
    ComplianceStatus,
    CitedClause,
    ComplianceResponse,
    StreamingChunk,
)
import json
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
        self.assertIsNotNone(filter_multi)
        assert filter_multi is not None
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


# ==============================================================================
# Compliance Reasoning Engine Tests
# ==============================================================================

class TestComplianceResponseSchema(unittest.TestCase):
    """
    Tests Pydantic v2 Compliance Response Schema, Enums, and Validators.
    """
    def test_compliance_status_enum(self):
        # Verify all 5 required status values
        self.assertEqual(ComplianceStatus.COMPLIANT.value, "COMPLIANT")
        self.assertEqual(ComplianceStatus.POTENTIALLY_DANGEROUS.value, "POTENTIALLY_DANGEROUS")
        self.assertEqual(ComplianceStatus.IMMEDIATE_DANGER.value, "IMMEDIATE_DANGER")
        self.assertEqual(ComplianceStatus.IMPROVEMENT_RECOMMENDED.value, "IMPROVEMENT_RECOMMENDED")
        self.assertEqual(ComplianceStatus.INSUFFICIENT_DATA_FURTHER_INVESTIGATION.value, "INSUFFICIENT_DATA_FURTHER_INVESTIGATION")

    def test_cited_clause_validation(self):
        clause = CitedClause(
            standard="Electricity at Work Regulations 1989",
            clause_number="Regulation 4(4)",
            verbatim_quote="All equipment provided for protecting persons at work shall be suitable for use."
        )
        self.assertEqual(clause.standard, "Electricity at Work Regulations 1989")
        self.assertEqual(clause.clause_number, "Regulation 4(4)")
        self.assertIn("protecting persons", clause.verbatim_quote)

        # Empty quote validation error
        with self.assertRaises(Exception):
            CitedClause(standard="EAWR", clause_number="Reg 4", verbatim_quote="")

    def test_compliance_response_model(self):
        resp = ComplianceResponse(
            compliance_status=ComplianceStatus.IMMEDIATE_DANGER,
            summary_verdict="Immediate danger detected due to exposed live parts on consumer unit. Urgent isolation required.",
            cited_clauses=[
                CitedClause(
                    standard="ESF Best Practice Guide 4",
                    clause_number="Code C1",
                    verbatim_quote="Conductive parts have become live as the result of a fault."
                )
            ],
            mandatory_requirements=[
                "[Regulation 4(4) - Absolute Duty]: Protective equipment shall be suitable and properly maintained."
            ],
            inspection_checks=[
                "Immediately isolate supply circuit.",
                "Verify absence of voltage with GS38 voltage indicator."
            ],
            confidence_score=0.98,
            model_used="llama3.1:8b",
            latency_ms=125.4,
            retrieved_chunks_count=3
        )
        self.assertEqual(resp.compliance_status, ComplianceStatus.IMMEDIATE_DANGER.value)
        self.assertEqual(len(resp.cited_clauses), 1)
        self.assertEqual(len(resp.mandatory_requirements), 1)
        self.assertEqual(len(resp.inspection_checks), 2)
        self.assertEqual(resp.confidence_score, 0.98)

    def test_confidence_score_clamping(self):
        resp = ComplianceResponse(
            compliance_status=ComplianceStatus.COMPLIANT,
            summary_verdict="Valid compliance assessment verified against statutory requirements.",
            confidence_score=1.5  # Out of upper bound -> clamped to 1.0
        )
        self.assertEqual(resp.confidence_score, 1.0)

        resp2 = ComplianceResponse(
            compliance_status=ComplianceStatus.INSUFFICIENT_DATA_FURTHER_INVESTIGATION,
            summary_verdict="Insufficient evidence to substantiate compliance.",
            confidence_score=-0.2  # Out of lower bound -> clamped to 0.0
        )
        self.assertEqual(resp2.confidence_score, 0.0)


class TestSystemPromptDirectives(unittest.TestCase):
    """
    Tests strict zero-hallucination compliance system prompt requirements.
    """
    def test_system_prompt_philosophy_and_constraints(self):
        from apps.compliance_core.services.compliance_engine import COMPLIANCE_SYSTEM_PROMPT

        # Core operating philosophy
        self.assertIn("Show the engineer why the answer was reached, not just the answer", COMPLIANCE_SYSTEM_PROMPT)
        self.assertIn("Never fabricate compliance decisions", COMPLIANCE_SYSTEM_PROMPT)

        # Strict adherence to retrieved context
        self.assertIn("STRICT ADHERENCE TO RETRIEVED CONTEXT", COMPLIANCE_SYSTEM_PROMPT)
        self.assertIn("EXPLICITLY FORBIDDEN", COMPLIANCE_SYSTEM_PROMPT)

        # Force status when context does not cover
        self.assertIn("INSUFFICIENT_DATA_FURTHER_INVESTIGATION", COMPLIANCE_SYSTEM_PROMPT)

        # Taxonomy
        self.assertIn("IMMEDIATE_DANGER", COMPLIANCE_SYSTEM_PROMPT)
        self.assertIn("POTENTIALLY_DANGEROUS", COMPLIANCE_SYSTEM_PROMPT)
        self.assertIn("IMPROVEMENT_RECOMMENDED", COMPLIANCE_SYSTEM_PROMPT)
        self.assertIn("COMPLIANT", COMPLIANCE_SYSTEM_PROMPT)


class TestStreamingJSONValidator(unittest.TestCase):
    """
    Tests streaming token accumulation, partial parsing, and resilient JSON repair.
    """
    def test_incremental_streaming_tokens(self):
        from apps.compliance_core.services.compliance_engine import StreamingJSONValidator

        validator = StreamingJSONValidator()
        stream_chunks = [
            '```json\n',
            '{\n  "compliance_status": "POTENTIALLY_DANGEROUS",\n',
            '  "summary_verdict": "Absence of basic protection on circuit protective conductor.',
            ' Urgent remedial action required to eliminate risk of shock.",\n',
            '  "cited_clauses": [\n',
            '    {\n      "standard": "Electricity at Work Regulations 1989",\n',
            '      "clause_number": "Regulation 8",\n',
            '      "verbatim_quote": "Precautions shall be taken, either by earthing or by other suitable means."\n',
            '    }\n  ],\n',
            '  "mandatory_requirements": ["Regulation 8 absolute duty on earthing."],\n',
            '  "inspection_checks": ["Test loop impedance Zs on circuit."],\n',
            '  "confidence_score": 0.94\n}',
            '\n```'
        ]

        partial_states = []
        for token in stream_chunks:
            p = validator.feed(token)
            if p:
                partial_states.append(p)

        self.assertGreater(len(partial_states), 0)
        final_resp = validator.finalize(model_name="test-stream-model", chunks_count=2)
        self.assertEqual(final_resp.compliance_status, ComplianceStatus.POTENTIALLY_DANGEROUS.value)
        self.assertEqual(len(final_resp.cited_clauses), 1)
        self.assertEqual(final_resp.cited_clauses[0].clause_number, "Regulation 8")
        self.assertEqual(final_resp.confidence_score, 0.94)

    def test_broken_json_repair(self):
        from apps.compliance_core.services.compliance_engine import StreamingJSONValidator

        validator = StreamingJSONValidator()
        # Incomplete, unclosed JSON snippet missing braces
        malformed = '{"compliance_status": "C1", "summary_verdict": "Severe hazard present on panel,'
        validator.feed(malformed)
        resp = validator.finalize()
        self.assertEqual(resp.compliance_status, ComplianceStatus.IMMEDIATE_DANGER.value)

    def test_unparseable_fallback(self):
        from apps.compliance_core.services.compliance_engine import StreamingJSONValidator

        validator = StreamingJSONValidator()
        validator.feed("Random nonsensical text that cannot be parsed into JSON at all.")
        resp = validator.finalize()
        self.assertEqual(resp.compliance_status, ComplianceStatus.INSUFFICIENT_DATA_FURTHER_INVESTIGATION.value)
        self.assertEqual(resp.confidence_score, 0.10)


class TestLLMClientProviders(unittest.TestCase):
    """
    Tests Ollama, Groq, Anthropic, and Deterministic LLM client providers.
    """
    def test_ollama_client_configuration(self):
        from apps.compliance_core.services.compliance_engine import OllamaLLMClient
        client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3.1:8b")
        self.assertEqual(client.name, "ollama")
        self.assertEqual(client.model, "llama3.1:8b")
        self.assertEqual(client.base_url, "http://localhost:11434")

    def test_groq_client_configuration(self):
        from apps.compliance_core.services.compliance_engine import GroqLLMClient
        client = GroqLLMClient(api_key="gsk_test123", model="llama-3.3-70b-versatile")
        self.assertEqual(client.name, "groq")
        self.assertTrue(client.is_available())

    def test_anthropic_client_configuration(self):
        from apps.compliance_core.services.compliance_engine import AnthropicLLMClient
        client = AnthropicLLMClient(api_key="sk-ant-test123", model="claude-3-5-sonnet-20241022")
        self.assertEqual(client.name, "anthropic")
        self.assertTrue(client.is_available())

    def test_deterministic_evaluator(self):
        from apps.compliance_core.services.compliance_engine import (
            DeterministicComplianceEvaluator,
            COMPLIANCE_SYSTEM_PROMPT,
            build_compliance_user_prompt
        )
        client = DeterministicComplianceEvaluator()
        self.assertTrue(client.is_available())

        # Test with context containing C1 observation
        sample_context = """--- [CHUNK 1] ---
Standard: Electrical Safety First Best Practice Guide 4
Regulation / Section: Section 4
Sub-Clause / Item: Observation Code C1
Statutory Duty Nature: Immediate Action (Danger Present)
Parent Title: Examples of items warranting classification code C1
Observation Code: C1
Verbatim Statutory Text:
\"\"\"
A circuit protective device is missing from a consumer unit and a suitable and securely fitted blanking piece is not in place, resulting in accessible live parts.
\"\"\""""

        prompt = build_compliance_user_prompt("missing blanking piece on consumer unit danger", sample_context)
        output = client.generate(prompt=prompt, system_prompt=COMPLIANCE_SYSTEM_PROMPT)
        parsed = json.loads(output)
        self.assertEqual(parsed["compliance_status"], ComplianceStatus.IMMEDIATE_DANGER.value)
        self.assertGreater(len(parsed["inspection_checks"]), 0)

    def test_ollama_streaming_mock(self):
        from unittest.mock import patch, MagicMock
        from apps.compliance_core.services.compliance_engine import OllamaLLMClient
        with patch("httpx.stream") as mock_stream:
            mock_resp = MagicMock()
            mock_resp.iter_lines.return_value = [
                json.dumps({"message": {"content": '{"compliance_status": '}}),
                json.dumps({"message": {"content": '"COMPLIANT", '}}),
                json.dumps({"message": {"content": '"summary_verdict": "Verified."}'}}),
            ]
            mock_stream.return_value.__enter__.return_value = mock_resp

            client = OllamaLLMClient()
            tokens = list(client.stream("query", "system"))
            self.assertEqual("".join(tokens), '{"compliance_status": "COMPLIANT", "summary_verdict": "Verified."}')

    def test_groq_streaming_mock(self):
        from unittest.mock import patch, MagicMock
        from apps.compliance_core.services.compliance_engine import GroqLLMClient
        with patch("httpx.stream") as mock_stream:
            mock_resp = MagicMock()
            mock_resp.iter_lines.return_value = [
                'data: ' + json.dumps({"choices": [{"delta": {"content": '{"compliance_status": '}}]}),
                'data: ' + json.dumps({"choices": [{"delta": {"content": '"IMMEDIATE_DANGER"}'}}]}),
                'data: [DONE]'
            ]
            mock_stream.return_value.__enter__.return_value = mock_resp

            client = GroqLLMClient(api_key="gsk_mock")
            tokens = list(client.stream("query", "system"))
            self.assertEqual("".join(tokens), '{"compliance_status": "IMMEDIATE_DANGER"}')

    def test_anthropic_streaming_mock(self):
        from unittest.mock import patch, MagicMock
        from apps.compliance_core.services.compliance_engine import AnthropicLLMClient
        with patch("httpx.stream") as mock_stream:
            mock_resp = MagicMock()
            mock_resp.iter_lines.return_value = [
                'data: ' + json.dumps({"type": "content_block_delta", "delta": {"text": '{"compliance_status": '}}),
                'data: ' + json.dumps({"type": "content_block_delta", "delta": {"text": '"POTENTIALLY_DANGEROUS"}'}}),
            ]
            mock_stream.return_value.__enter__.return_value = mock_resp

            client = AnthropicLLMClient(api_key="sk-ant-mock")
            tokens = list(client.stream("query", "system"))
            self.assertEqual("".join(tokens), '{"compliance_status": "POTENTIALLY_DANGEROUS"}')



class TestComplianceReasoningEngineIntegration(unittest.TestCase):
    """
    End-to-end integration tests for ComplianceReasoningEngine with vector store.
    """
    def setUp(self):
        from apps.compliance_core.services.compliance_engine import get_compliance_engine
        self.engine = get_compliance_engine()

    def test_reasoning_exact_eawr_reg4_maintenance(self):
        # Query EAWR Reg 4(2) maintenance requirements
        response = self.engine.reason(
            query="What does Reg 4(2) require for system maintenance?",
            top_k=3,
            provider="deterministic"
        )
        self.assertEqual(response.compliance_status, ComplianceStatus.COMPLIANT.value)
        self.assertGreater(len(response.cited_clauses), 0)
        self.assertTrue(any("4(2)" in c.clause_number for c in response.cited_clauses))
        self.assertGreater(len(response.mandatory_requirements), 0)
        self.assertGreater(len(response.inspection_checks), 0)
        self.assertGreater(response.confidence_score, 0.80)

    def test_reasoning_immediate_danger_c1(self):
        # Query C1 blanking piece defect
        response = self.engine.reason(
            query="missing blanking piece on consumer unit danger exposed parts",
            top_k=3,
            provider="deterministic"
        )
        self.assertEqual(response.compliance_status, ComplianceStatus.IMMEDIATE_DANGER.value)
        self.assertIn("C1", response.summary_verdict)
        self.assertGreater(len(response.inspection_checks), 0)
        self.assertTrue(any("isolate" in check.lower() for check in response.inspection_checks))

    def test_zero_hallucination_out_of_scope_query(self):
        # Query completely outside scope of electrical regulations -> must be INSUFFICIENT_DATA
        response = self.engine.reason(
            query="medical diagnosis for fever and bacterial infection symptoms",
            top_k=3,
            provider="deterministic"
        )
        self.assertEqual(response.compliance_status, ComplianceStatus.INSUFFICIENT_DATA_FURTHER_INVESTIGATION.value)
        self.assertEqual(len(response.cited_clauses), 0)  # Never fabricate citations!

    def test_empty_retrieved_context_guard(self):
        # Explicit evaluation with empty chunks
        response = self.engine.evaluate_from_chunks(
            query="Any technical query",
            chunks=[],
            client=None
        )
        self.assertEqual(response.compliance_status, ComplianceStatus.INSUFFICIENT_DATA_FURTHER_INVESTIGATION.value)
        self.assertEqual(len(response.cited_clauses), 0)
        self.assertEqual(response.confidence_score, 0.0)

    def test_streaming_reasoning(self):
        # Test full generator streaming
        events = list(self.engine.stream_reason(
            query="missing blanking piece on consumer unit danger",
            top_k=3,
            provider="deterministic"
        ))
        event_types = [e.event for e in events]
        self.assertIn("token", event_types)
        self.assertIn("validated_response", event_types)

        final_chunk = next(e for e in events if e.event == "validated_response")
        self.assertIsNotNone(final_chunk.validated_response)
        assert final_chunk.validated_response is not None
        self.assertEqual(final_chunk.validated_response.compliance_status, ComplianceStatus.IMMEDIATE_DANGER.value)


if __name__ == '__main__':
    unittest.main()

