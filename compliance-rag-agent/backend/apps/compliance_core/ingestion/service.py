"""
Document Ingestion Orchestration Service for Regulatory Documents.
Coordinates text extraction, hierarchical parsing, validation, ChromaDB indexing, and DB persistence.
"""

import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from apps.compliance_core.schemas import RegulatoryChunk, IngestionReport
from apps.compliance_core.ingestion.extractors import extract_text_from_file
from apps.compliance_core.ingestion.parsers import get_parser_registry
from apps.compliance_core.services.vector_store import get_vector_store
from apps.rag.services.chroma import get_chroma_service
from apps.rag.models import ComplianceStandard, ComplianceDocument

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    High-level ingestion pipeline for statutory regulations and engineering guidance.
    """

    def __init__(self):
        self.parser_registry = get_parser_registry()

    def ingest_file(
        self,
        file_path: Union[str, Path],
        standard_name: Optional[str] = None,
        store_chroma: bool = False,
        store_db: bool = False,
    ) -> IngestionReport:
        """
        Executes end-to-end ingestion pipeline:
        1. Extract text (PDF / Markdown / Text)
        2. Resolve hierarchical parser
        3. Parse into structured RegulatoryChunk models
        4. (Optional) Persist into ChromaDB vector store
        5. (Optional) Save records in Django ORM
        """
        start_time = time.time()
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        # 1. Text Extraction
        logger.info(f"Extracting content from: {path.name}")
        raw_text, file_meta = extract_text_from_file(path)

        # 2. Canonical Standard Inference
        detected_standard = standard_name or self._infer_standard_title(path.name, raw_text)

        # 3. Parser Resolution
        parser = self.parser_registry.resolve_parser(
            text=raw_text,
            file_name=path.name,
            standard_hint=detected_standard
        )
        logger.info(f"Using parser: {parser.parser_name} for standard '{detected_standard}'")

        # 4. Hierarchical Parsing into validated RegulatoryChunks
        chunks: List[RegulatoryChunk] = parser.parse(
            text=raw_text,
            standard_name=detected_standard,
            file_metadata=file_meta
        )

        if not chunks:
            raise ValueError(f"No regulatory clauses could be extracted from {path.name}")

        # Compute duty breakdown & found regulations
        duty_counts: Dict[str, int] = {}
        regs_found: List[str] = []
        for c in chunks:
            duty_counts[c.duty_holder] = duty_counts.get(c.duty_holder, 0) + 1
            if c.regulation_number not in regs_found:
                regs_found.append(c.regulation_number)

        chroma_success = False
        db_success = False

        # 4. ChromaDB Vector Store Indexing
        if store_chroma:
            chroma_success = self._upsert_to_chroma(chunks)

        # 5. Django ORM Persistence
        if store_db:
            db_success = self._persist_to_database(
                chunks=chunks,
                file_path=path,
                standard_name=detected_standard,
                file_meta=file_meta
            )

        duration = round(time.time() - start_time, 3)

        return IngestionReport(
            source_file=path.name,
            standard_name=detected_standard,
            document_type=chunks[0].document_type if chunks else "Regulation",
            total_chunks=len(chunks),
            regulations_found=regs_found,
            duty_breakdown=duty_counts,
            chroma_upserted=chroma_success,
            database_saved=db_success,
            duration_seconds=duration,
            chunks=chunks
        )

    def _infer_standard_title(self, filename: str, text: str) -> str:
        """Heuristic to infer canonical title if not explicitly supplied."""
        lower_head = text[:2500].lower()
        lower_fn = filename.lower()

        if any(term in lower_fn or term in lower_head for term in ["best_practice", "best-practice", "bpg4", "bpg_4", "bpg-4", "best practice guide 4"]):
            return "Electrical Safety First Best Practice Guide 4 (EICR)"
        if "hsr25" in lower_head or "hsr25" in lower_fn:
            return "HSE HSR25 Memorandum of Guidance (EAWR 1989)"
        if "electricity at work" in lower_head or "eawr" in lower_fn or "eaw act" in lower_fn:
            return "Electricity at Work Regulations 1989"
        if "puwer" in lower_fn or "provision and use of work equipment" in lower_head:
            return "Provision and Use of Work Equipment Regulations 1998 (PUWER)"
        if "hasawa" in lower_fn or "health and safety at work etc. act 1974" in lower_head:
            return "Health and Safety at Work etc. Act 1974 (HASAWA)"
        if "nist" in lower_fn or "artificial intelligence risk management" in lower_head:
            return "NIST AI Risk Management Framework (AI 100-1)"
        if "approved_document" in lower_fn or "approved document" in lower_head:
            return "UK Building Regulations Merged Approved Documents"
        if "bs 7671" in lower_head:
            return "BS 7671 IET Wiring Regulations"

        return filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()

    def _upsert_to_chroma(self, chunks: List[RegulatoryChunk]) -> bool:
        """Upserts regulatory chunks into ChromaDB primary persistent storage."""
        try:
            # Primary vector store for engineering standards with local SentenceTransformers embeddings
            vector_store = get_vector_store()
            vector_store.add_chunks(chunks)

            # Also sync with RAG service collection for unified frontend compatibility
            try:
                chroma = get_chroma_service()
                seen_rag_ids = set()
                rag_ids = []
                for c in chunks:
                    cid = c.chunk_id
                    if cid in seen_rag_ids:
                        s = 2
                        while f"{cid}_v{s}" in seen_rag_ids:
                            s += 1
                        cid = f"{cid}_v{s}"
                    seen_rag_ids.add(cid)
                    rag_ids.append(cid)

                documents = [c.raw_text for c in chunks]
                metadatas = [{
                    "chunk_id": rag_ids[i],
                    "standard": c.standard,
                    "standard_code": self._to_standard_code(c.standard),
                    "regulation_number": c.regulation_number,
                    "sub_clause": c.sub_clause,
                    "clause": c.sub_clause,
                    "duty_holder": c.duty_holder,
                    "parent_title": c.parent_title,
                    "document_type": c.document_type,
                    "defense_available": c.defense_available,
                    "classification_code": c.classification_code or "",
                } for i, c in enumerate(chunks)]
                chroma.add_chunks(ids=rag_ids, documents=documents, metadatas=metadatas)
            except Exception as rag_err:
                logger.debug(f"Secondary RAG sync note: {rag_err}")

            logger.info(f"Successfully upserted {len(chunks)} regulatory chunks into ChromaDB vector store.")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert chunks into ChromaDB: {e}", exc_info=True)
            return False

    def _persist_to_database(
        self,
        chunks: List[RegulatoryChunk],
        file_path: Path,
        standard_name: str,
        file_meta: Dict[str, Any]
    ) -> bool:
        """Persists standards and document entries into Django database."""
        try:
            code = self._to_standard_code(standard_name)
            standard_obj, _ = ComplianceStandard.objects.get_or_create(
                code=code,
                defaults={
                    "name": standard_name,
                    "authority": "HSE / UK Statutory" if "electricity at work" in standard_name.lower() else "Electrical Safety First",
                    "description": f"Imported regulatory standard ({len(chunks)} structured clauses)."
                }
            )

            ComplianceDocument.objects.update_or_create(
                standard=standard_obj,
                source_identifier=file_path.name,
                defaults={
                    "title": standard_name,
                    "status": "INDEXED",
                    "total_chunks": len(chunks),
                    "document_metadata": file_meta
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save document in database: {e}", exc_info=True)
            return False

    @staticmethod
    def _to_standard_code(name: str) -> str:
        """Normalizes standard names to short codes (e.g. 'EAWR-1989', 'ESF-BPG4')."""
        lower = name.lower()
        if "hsr25" in lower:
            return "HSE-HSR25"
        if "electricity at work" in lower or "eawr" in lower:
            return "EAWR-1989"
        if "best practice guide 4" in lower or "bpg4" in lower or "esf" in lower:
            return "ESF-BPG4"
        if "puwer" in lower:
            return "PUWER-1998"
        if "hasawa" in lower or "health and safety at work" in lower:
            return "HASAWA-1974"
        if "nist" in lower:
            return "NIST-AI-100"
        if "bs 7671" in lower:
            return "BS-7671"
        return re.sub(r'[^A-Z0-9]+', '-', name.upper()).strip('-')[:16]
