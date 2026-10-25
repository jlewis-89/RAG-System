"""
Parser Registry and Auto-Detector for Regulatory & Engineering Standards.
"""

import re
import logging
from typing import List, Optional, Dict, Any
from ...schemas import RegulatoryChunk, DutyHolderType, DocumentType
from .base import AbstractBaseRegulationParser
from .eawr import EAWRParser
from .esf_bpg4 import ESFBPG4Parser

logger = logging.getLogger(__name__)


class GenericRegulationParser(AbstractBaseRegulationParser):
    """
    Fallback hierarchical parser for general engineering standards, BS 7671, ISO, or IEC specifications.
    Splits by clauses (e.g. 'Clause 4.1', 'Section 7.3') while preserving unsevered text.
    """

    @property
    def parser_name(self) -> str:
        return "Generic Standard & Regulation Parser"

    def can_parse(self, text: str, file_name: Optional[str] = None) -> bool:
        return True  # Fallback matches everything

    def parse(
        self,
        text: str,
        standard_name: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RegulatoryChunk]:
        standard = standard_name or "Engineering Standard Specification"
        clean_text = text.replace('\r\n', '\n').strip()
        chunks: List[RegulatoryChunk] = []

        # Match section / clause markers (e.g., 'Clause 4.1', 'Section 7.2.1', 'Rule 10')
        clause_pattern = re.compile(
            r'(?:^|\n)(?:###?\s*)?((?:Clause|Section|Article|Regulation|Part|Rule|UG-|UW-|UCS-)\s*[0-9A-Za-z\.\-]+)(?:[.:\s—-]+([^\n]+))?\n(.*?)(?=(?:\n(?:###?\s*)?(?:Clause|Section|Article|Regulation|Part|Rule|UG-|UW-|UCS-)\s*[0-9A-Za-z\.\-]+)|$)',
            re.IGNORECASE | re.DOTALL
        )

        matches = list(clause_pattern.finditer(clean_text))

        if matches:
            for m in matches:
                clause_marker = m.group(1).strip()
                clause_title = (m.group(2) or "").strip()
                clause_body = m.group(3).strip()
                parent_title = clause_title or f"{clause_marker} Provisions"

                full_text = f"{clause_marker} {clause_title}\n{clause_body}".strip() if clause_title else f"{clause_marker}\n{clause_body}".strip()
                duty = self.infer_statutory_duty_holder(full_text)

                chunks.append(RegulatoryChunk(
                    standard=standard,
                    regulation_number=clause_marker,
                    sub_clause=clause_marker,
                    duty_holder=duty,
                    parent_title=parent_title,
                    raw_text=full_text,
                    document_type=DocumentType.TECHNICAL_SPECIFICATION.value,
                    metadata={"file_metadata": file_metadata or {}}
                ))
        else:
            # Paragraph breakdown fallback
            paragraphs = clean_text.split("\n\n")
            for idx, p in enumerate(paragraphs):
                p = p.strip()
                if len(p) < 20:
                    continue
                chunks.append(RegulatoryChunk(
                    standard=standard,
                    regulation_number="Section 1",
                    sub_clause=f"Clause 1.{idx + 1}",
                    duty_holder=self.infer_statutory_duty_holder(p),
                    parent_title="General Technical Requirements",
                    raw_text=p,
                    document_type=DocumentType.TECHNICAL_SPECIFICATION.value,
                    metadata={"file_metadata": file_metadata or {}}
                ))

        return chunks


class RegulationParserRegistry:
    """
    Manages registered parsers and resolves the best parser for a given document.
    """

    def __init__(self):
        # Order matters: specialized guide parsers first, statutory parsers, generic fallback last
        self.parsers: List[AbstractBaseRegulationParser] = [
            ESFBPG4Parser(),
            EAWRParser(),
            GenericRegulationParser(),
        ]

    def resolve_parser(
        self,
        text: str,
        file_name: Optional[str] = None,
        standard_hint: Optional[str] = None
    ) -> AbstractBaseRegulationParser:
        """
        Resolves the appropriate parser based on standard hint, file name, or content inspection.
        """
        hint_lower = (standard_hint or "").lower()
        fn_lower = (file_name or "").lower()

        # Check explicit hint or file name first
        if any(k in hint_lower or k in fn_lower for k in ["best_practice", "best practice", "bpg4", "bpg_4", "bpg-4", "esf"]):
            return self.parsers[0]  # ESFBPG4Parser
        if any(k in hint_lower or k in fn_lower for k in ["electricity at work", "eawr", "hsr25", "eaw act"]):
            return self.parsers[1]  # EAWRParser

        # Otherwise probe content
        for parser in self.parsers:
            if parser.can_parse(text, file_name):
                return parser

        return self.parsers[-1]  # Generic fallback


# Singleton registry instance
_default_registry = RegulationParserRegistry()

def get_parser_registry() -> RegulationParserRegistry:
    return _default_registry
