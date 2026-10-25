"""
Document Ingestion and Parsing Service for Engineering Compliance.
Processes text manuals, extracts sections/clauses, chunks, and persists into ChromaDB.
"""

import re
import uuid
import logging
from typing import List, Dict, Any, Tuple
from apps.rag.models import ComplianceStandard, ComplianceDocument
from apps.rag.services.chroma import get_chroma_service

logger = logging.getLogger(__name__)


class ComplianceIngestionService:
    """
    Handles chunking, metadata enrichment, and vector store insertion
    for regulatory and engineering compliance documents.
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chroma_service = get_chroma_service()

    def _extract_clause_or_section(self, text: str) -> str:
        """
        Attempts to identify engineering standard clause/section markers
        such as 'Clause 4.1.2', 'Section VIII Div 1 UG-23', 'Article 5', etc.
        """
        pattern = r"(?:Section|Clause|Article|Paragraph|Part|UG-|UW-|UCS-)\s*([0-9A-Za-z\.\-]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
        return "General Clause"

    def chunk_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Splits raw text into overlapping chunks, capturing the active clause or section.
        Returns a list of tuples: (chunk_text, clause_identifier).
        """
        clean_text = text.replace("\r\n", "\n").strip()
        if not clean_text:
            return []

        # Split primarily on double newlines / paragraph boundaries
        paragraphs = clean_text.split("\n\n")
        chunks: List[Tuple[str, str]] = []
        current_chunk = ""
        current_clause = "General Clause"

        for p in paragraphs:
            p = p.strip()
            if not p:
                continue

            detected_clause = self._extract_clause_or_section(p)
            if detected_clause != "General Clause":
                current_clause = detected_clause

            if len(current_chunk) + len(p) <= self.chunk_size:
                current_chunk += ("\n\n" if current_chunk else "") + p
            else:
                if current_chunk:
                    chunks.append((current_chunk, current_clause))
                
                # If paragraph itself is longer than chunk_size, split by sentences or characters
                if len(p) > self.chunk_size:
                    start = 0
                    while start < len(p):
                        end = start + self.chunk_size
                        sub_text = p[start:end]
                        chunks.append((sub_text, current_clause))
                        start += self.chunk_size - self.chunk_overlap
                    current_chunk = ""
                else:
                    current_chunk = p

        if current_chunk:
            chunks.append((current_chunk, current_clause))

        return chunks

    def ingest_document(
        self,
        title: str,
        standard_code: str,
        content: str,
        source_identifier: str = "manual_entry",
        custom_metadata: Dict[str, Any] = None
    ) -> ComplianceDocument:
        """
        Ingests a full document, persists chunks in ChromaDB, and records audit state.
        """
        standard_obj, _ = ComplianceStandard.objects.get_or_create(
            code=standard_code.upper().strip(),
            defaults={
                "name": f"Standard {standard_code.upper().strip()}",
                "authority": standard_code.split('-')[0].upper() if '-' in standard_code else "Engineering Standard",
            }
        )

        doc = ComplianceDocument.objects.create(
            standard=standard_obj,
            title=title,
            source_identifier=source_identifier,
            status='PROCESSING',
            document_metadata=custom_metadata or {}
        )

        try:
            raw_chunks = self.chunk_text(content)
            if not raw_chunks:
                doc.status = 'FAILED'
                doc.error_message = "Document text is empty or could not be chunked."
                doc.save()
                return doc

            ids = []
            documents = []
            metadatas = []

            for idx, (chunk_text, clause) in enumerate(raw_chunks):
                chunk_id = f"{standard_obj.code}_{doc.id}_chk_{idx}_{uuid.uuid4().hex[:6]}"
                ids.append(chunk_id)
                documents.append(chunk_text)
                metadatas.append({
                    "chunk_id": chunk_id,
                    "document_id": doc.id,
                    "standard_code": standard_obj.code,
                    "standard_name": standard_obj.name,
                    "document_title": title,
                    "clause": clause,
                    "chunk_index": idx,
                    "source": source_identifier,
                })

            # Upsert into ChromaDB
            self.chroma_service.add_chunks(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )

            doc.total_chunks = len(ids)
            doc.status = 'INDEXED'
            doc.error_message = ""
            doc.save()
            logger.info(f"Successfully indexed document '{title}' ({doc.id}) with {len(ids)} chunks.")
            return doc

        except Exception as e:
            logger.error(f"Error during document ingestion for '{title}': {e}", exc_info=True)
            doc.status = 'FAILED'
            doc.error_message = str(e)
            doc.save()
            raise e

    def seed_initial_standards(self):
        """
        Populates default engineering standards into ChromaDB for immediate testing:
        - ISO 9001:2015 (Clause 7.5 Documented Information, Clause 8.5 Production & Service)
        - ASME Section VIII Div 1 (UG-20 Design Temperature, UG-125 Pressure Relief Devices)
        - IEC 61508 (Functional Safety of Electrical/Electronic/Programmable Safety Systems)
        """
        sample_standards = [
            {
                "title": "ISO 9001:2015 Quality Management Systems - Specification",
                "code": "ISO-9001",
                "content": (
                    "Clause 7.5 Documented Information\n\n"
                    "7.5.1 General: The organization's quality management system shall include documented information "
                    "required by this International Standard and documented information determined by the organization as "
                    "being necessary for the effectiveness of the quality management system.\n\n"
                    "7.5.2 Creating and updating: When creating and updating documented information, the organization shall "
                    "ensure appropriate identification, description (e.g. title, date, author, reference number), format "
                    "(e.g. language, software version, graphics), and review and approval for suitability and adequacy.\n\n"
                    "7.5.3 Control of documented information: Documented information shall be controlled to ensure it is "
                    "available and suitable for use, where and when it is needed, and adequately protected from loss of "
                    "confidentiality, improper use, or loss of integrity. For the control of documented information, the "
                    "organization shall address distribution, access, retrieval, storage, preservation, and retention.\n\n"
                    "Clause 8.5 Production and Service Provision\n\n"
                    "8.5.1 Control of production and service provision: The organization shall implement production and service "
                    "provision under controlled conditions. Controlled conditions shall include the availability of documented "
                    "information that defines the characteristics of the products to be produced, the availability and use of "
                    "suitable monitoring and measuring resources, and the implementation of actions to prevent human error."
                ),
                "source": "iso_9001_2015_standard.txt"
            },
            {
                "title": "ASME BPVC Section VIII Division 1 - Rules for Pressure Vessels",
                "code": "ASME-VIII",
                "content": (
                    "Section VIII UG-20 Design Temperature\n\n"
                    "UG-20(a) Maximum Design Temperature: The maximum design temperature shall not be less than the mean metal "
                    "temperature expected under operating conditions for the part considered. If necessary, the metal temperature "
                    "shall be determined by computation or by measurement from equipment in service under equivalent conditions.\n\n"
                    "UG-20(b) Minimum Design Metal Temperature (MDMT): The MDMT marked on the nameplate shall be the coldest "
                    "metal temperature expected in service, taking into account operation upsets, auto-refrigeration, atmospheric "
                    "cooling, and any other relevant cooling sources.\n\n"
                    "Section VIII UG-125 Pressure Relief Devices\n\n"
                    "UG-125(a) All pressure vessels within the scope of this Division, irrespective of size or pressure, shall "
                    "be provided with overpressure protection in accordance with the requirements of UG-125 through UG-138.\n\n"
                    "UG-125(c) Relief valves shall be inspected and tested periodically. Inspection intervals for relief devices "
                    "shall not exceed 5 years in general service, or 3 years in severe corrosive or fouling operating conditions."
                ),
                "source": "asme_bpvc_sec_viii_div1.txt"
            },
            {
                "title": "IEC 61508 Functional Safety of E/E/PE Safety-Related Systems",
                "code": "IEC-61508",
                "content": (
                    "Clause 4.1 Safety Lifecycle Management\n\n"
                    "Safety lifecycle activities shall be documented in a Safety Plan. The safety plan shall specify all "
                    "management, verification, and validation tasks required to achieve and maintain Safety Integrity Level (SIL).\n\n"
                    "Clause 7.4 Hardware Safety Integrity\n\n"
                    "Architectural constraints for hardware safety integrity shall satisfy target SIL ratings (SIL 1 through SIL 4). "
                    "For SIL 3 systems, the Hardware Fault Tolerance (HFT) shall be at least 1 for Type A components with Safe "
                    "Failure Fraction (SFF) between 90% and 99%, or HFT of 2 if SFF is below 90%.\n\n"
                    "Clause 8.2 Proof Testing\n\n"
                    "Periodic proof tests shall be conducted to detect hidden failures that prevent the safety instrumented function "
                    "from responding to a demand. The proof test coverage shall be documented and factored into the PFDavg calculations."
                ),
                "source": "iec_61508_overview.txt"
            }
        ]

        indexed_docs = []
        for item in sample_standards:
            # Check if standard already exists
            if not ComplianceDocument.objects.filter(title=item["title"], status='INDEXED').exists():
                doc = self.ingest_document(
                    title=item["title"],
                    standard_code=item["code"],
                    content=item["content"],
                    source_identifier=item["source"]
                )
                indexed_docs.append(doc)

        return indexed_docs
