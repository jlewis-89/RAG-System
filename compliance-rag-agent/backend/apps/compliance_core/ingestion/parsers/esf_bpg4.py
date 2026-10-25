"""
Hierarchical Parser for Electrical Safety First (ESF) Best Practice Guide 4 (BPG4).
Covers Electrical Installation Condition Reporting (EICR) and Classification Codes (C1, C2, C3, FI).
Extracts high-fidelity observation examples, categories, classification codes, and guidance narratives.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from apps.compliance_core.schemas import RegulatoryChunk, DutyHolderType, DocumentType
from apps.compliance_core.ingestion.parsers.base import AbstractBaseRegulationParser

logger = logging.getLogger(__name__)

BPG4_SECTIONS: Dict[str, str] = {
    "1": "Introduction & Scope",
    "2": "Electrical Installation Condition Reporting (EICR)",
    "3": "Purpose of Periodic Inspection, Testing and Reporting",
    "4": "The Inspector",
    "5": "Periodic Inspection and Testing Procedures",
    "6": "Classification Codes",
    "7": "Summary of the Conditions of the Installation",
    "8": "Distributor and Supplier Equipment",
    "9": "Examples of the Use of Classification Codes",
}


class ESFBPG4Parser(AbstractBaseRegulationParser):
    """
    Parser for Electrical Safety First Best Practice Guide 4 (ESF BPG4).
    Extracts inspection observation guidance, classification codes (C1, C2, C3, FI),
    and practical engineering decision rules for EICRs.
    """

    @property
    def parser_name(self) -> str:
        return "Electrical Safety First Best Practice Guide 4 Parser (ESF BPG4)"

    def can_parse(self, text: str, file_name: Optional[str] = None) -> bool:
        if file_name:
            fn_lower = file_name.lower()
            if any(term in fn_lower for term in ["best_practice", "best-practice", "bpg4", "bpg_4", "bpg-4", "esf"]):
                return True

        lower_head = text[:3000].lower()
        if "best practice guide 4" in lower_head or "best practice guide" in lower_head:
            return True
        if "electrical safety first" in lower_head and ("classification codes" in lower_head or "eicr" in lower_head):
            return True
        if "code c1" in lower_head and "code c2" in lower_head and "code c3" in lower_head:
            return True

        return False

    def parse(
        self,
        text: str,
        standard_name: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RegulatoryChunk]:
        standard = standard_name or "Electrical Safety First Best Practice Guide 4"
        doc_type = DocumentType.INDUSTRY_BEST_PRACTICE.value

        # Clean running headers, footers, and table repeating headers
        clean_text = text.replace('\r\n', '\n').strip()
        clean_text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', clean_text)
        clean_text = re.sub(r'electricalsafetyfirst\.org\.uk[^\n]*', '', clean_text)
        clean_text = re.sub(r'BEST PRACTICE GUIDE 4:[^\n]*', '', clean_text)
        clean_text = re.sub(r'Powering change \+ saving lives[^\n]*', '', clean_text)
        clean_text = re.sub(r'Category\s+Code\s+Description', '', clean_text)

        chunks: List[RegulatoryChunk] = []

        # Split text into narrative sections (1 to 8) and classification examples table (Section 9)
        idx_s9 = clean_text.find('EXAMPLES OF THE USE OF')
        narrative_text = clean_text[:idx_s9] if idx_s9 != -1 else clean_text
        s9_text = clean_text[idx_s9:] if idx_s9 != -1 else ""

        # 1. Parse Narrative Sections 1 to 8
        sec_pattern = re.compile(r'(?:^|\n)\s*(\d)\.\s*([A-Z\s,/&-]+)(?=\n)', re.MULTILINE)
        sec_matches = list(sec_pattern.finditer(narrative_text))

        for i, sm in enumerate(sec_matches):
            sec_num = sm.group(1).strip()
            sec_raw_title = sm.group(2).strip().title()
            parent_title = BPG4_SECTIONS.get(sec_num, f"Section {sec_num} - {sec_raw_title}")
            reg_number = f"Section {sec_num}"

            start_pos = sm.end()
            end_pos = sec_matches[i+1].start() if i + 1 < len(sec_matches) else len(narrative_text)
            sec_body = narrative_text[start_pos:end_pos].strip()

            # Section 6: Classification Codes Definitions (C1, C2, C3, FI)
            if sec_num == "6":
                code_def_pattern = re.compile(
                    r'(?:^|\n)\s*(?:CODE\s*)?(C[123]|FI|FURTHER\s*INVESTIGATION)\b[\s.:—-]*(.*?)(?=(?:\n\s*(?:CODE\s*)?(?:C[123]|FI|FURTHER\s*INVESTIGATION)\b)|$)',
                    re.DOTALL | re.IGNORECASE
                )
                c_matches = list(code_def_pattern.finditer(sec_body))
                if c_matches:
                    for cm in c_matches:
                        c_label = cm.group(1).strip().upper()
                        clean_code = "C1" if "1" in c_label else "C2" if "2" in c_label else "C3" if "3" in c_label else "FI"
                        c_body = cm.group(2).strip()
                        if len(c_body) < 15:
                            continue
                        duty = self._get_code_duty_level(clean_code)

                        chunks.append(RegulatoryChunk(
                            standard=standard,
                            regulation_number=reg_number,
                            sub_clause=f"{reg_number} - Code {clean_code} Definition",
                            duty_holder=duty,
                            parent_title=parent_title,
                            raw_text=f"Code {clean_code}: {c_body}",
                            document_type=doc_type,
                            classification_code=clean_code,
                            metadata={
                                "bpg4_code": clean_code,
                                "section": sec_num,
                                "file_metadata": file_metadata or {}
                            }
                        ))
                else:
                    chunks.append(RegulatoryChunk(
                        standard=standard,
                        regulation_number=reg_number,
                        sub_clause=reg_number,
                        duty_holder=DutyHolderType.ADVISORY.value,
                        parent_title=parent_title,
                        raw_text=sec_body,
                        document_type=doc_type,
                        metadata={"section": sec_num, "file_metadata": file_metadata or {}}
                    ))
            else:
                # Subsections (e.g. 1.1, 1.2) or clean paragraphs
                paragraphs = [p.strip() for p in sec_body.split('\n\n') if len(p.strip()) > 35]
                for idx, p in enumerate(paragraphs):
                    chunks.append(RegulatoryChunk(
                        standard=standard,
                        regulation_number=reg_number,
                        sub_clause=f"{reg_number}.{idx+1}",
                        duty_holder=DutyHolderType.ADVISORY.value,
                        parent_title=parent_title,
                        raw_text=p,
                        document_type=doc_type,
                        metadata={
                            "section": sec_num,
                            "paragraph_index": idx + 1,
                            "file_metadata": file_metadata or {}
                        }
                    ))

        # 2. Parse Section 9: Specific Observation Classification Examples
        if s9_text:
            s9_chunks = self._parse_section_9_examples(
                s9_text=s9_text,
                standard=standard,
                doc_type=doc_type,
                file_metadata=file_metadata
            )
            chunks.extend(s9_chunks)

        logger.info(f"ESFBPG4Parser successfully extracted {len(chunks)} regulatory chunks for '{standard}'.")
        return chunks

    def _parse_section_9_examples(
        self,
        s9_text: str,
        standard: str,
        doc_type: str,
        file_metadata: Optional[Dict[str, Any]]
    ) -> List[RegulatoryChunk]:
        """
        Extracts each tabular observation row in Section 9 into an explicit, search-optimized RegulatoryChunk.
        """
        lines = s9_text.split('\n')
        current_cat = "General"
        current_code = None
        current_desc_lines: List[str] = []
        row_pattern = re.compile(r'^(.*?)\b(C[123]|FI)\b\s*(.*)$')

        s9_chunks: List[RegulatoryChunk] = []

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            if "EXAMPLES OF THE USE OF" in line_str or "CLASSIFICATION CODES" in line_str:
                continue
            if "The following examples are not exhaustive" in line_str or "competent person" in line_str:
                continue

            match = row_pattern.match(line_str)
            if match:
                # Finalize previous observation item
                if current_code and current_desc_lines:
                    desc = " ".join(current_desc_lines).strip()
                    duty = self._get_code_duty_level(current_code)
                    s9_chunks.append(RegulatoryChunk(
                        standard=standard,
                        regulation_number="Section 9",
                        sub_clause=f"BPG4 Item - Code {current_code} ({current_cat})",
                        duty_holder=duty,
                        parent_title=f"Section 9 - Classification Examples ({current_cat})",
                        raw_text=f"Observation [{current_code}] ({current_cat}): {desc}",
                        document_type=doc_type,
                        classification_code=current_code,
                        metadata={
                            "section": "9",
                            "category": current_cat,
                            "bpg4_code": current_code,
                            "file_metadata": file_metadata or {}
                        }
                    ))
                    current_desc_lines = []

                prefix = match.group(1).strip()
                current_code = match.group(2).strip()
                initial_desc = match.group(3).strip()

                if prefix:
                    current_cat = prefix
                if initial_desc:
                    current_desc_lines.append(initial_desc)
            else:
                if current_code:
                    # Clean multi-line wrapped category prefixes
                    if current_cat == "Access to" and line_str.startswith("Live Parts"):
                        current_cat = "Access to Live Parts"
                        line_str = line_str[len("Live Parts"):].strip()
                    elif line_str in ["Live Parts", "Parts"]:
                        current_cat = f"{current_cat} {line_str}".strip()
                        continue
                    if line_str:
                        current_desc_lines.append(line_str)

        # Append final observation
        if current_code and current_desc_lines:
            desc = " ".join(current_desc_lines).strip()
            duty = self._get_code_duty_level(current_code)
            s9_chunks.append(RegulatoryChunk(
                standard=standard,
                regulation_number="Section 9",
                sub_clause=f"BPG4 Item - Code {current_code} ({current_cat})",
                duty_holder=duty,
                parent_title=f"Section 9 - Classification Examples ({current_cat})",
                raw_text=f"Observation [{current_code}] ({current_cat}): {desc}",
                document_type=doc_type,
                classification_code=current_code,
                metadata={
                    "section": "9",
                    "category": current_cat,
                    "bpg4_code": current_code,
                    "file_metadata": file_metadata or {}
                }
            ))

        return s9_chunks

    @staticmethod
    def _get_code_duty_level(code: str) -> str:
        if code == "C1":
            return "Immediate Action (Danger Present - Code C1)"
        elif code == "C2":
            return "Urgent Action (Potentially Dangerous - Code C2)"
        elif code == "C3":
            return "Improvement Recommended (Code C3)"
        elif code == "FI":
            return "Further Investigation Required (Code FI)"
        return DutyHolderType.ADVISORY.value
