"""
Hierarchical Parser for the UK Electricity at Work Regulations 1989 (EAWR / SI 1989/635)
and HSE Memorandum of Guidance (HSR25).
Preserves exact legal clauses, parent titles, sub-clauses, duty holder classifications,
and statutory defense availability under Regulation 29.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from apps.compliance_core.schemas import RegulatoryChunk, DutyHolderType, DocumentType
from apps.compliance_core.ingestion.parsers.base import AbstractBaseRegulationParser

logger = logging.getLogger(__name__)

# Known Statutory Titles for EAWR 1989 (ensures 100% accuracy across both SI 1989/635 & HSR25)
EAWR_KNOWN_TITLES: Dict[int, str] = {
    1: "Citation and commencement",
    2: "Interpretation",
    3: "Persons on whom duties are imposed by these Regulations",
    4: "Systems, work activities and protective equipment",
    5: "Strength and capability of electrical equipment",
    6: "Adverse or hazardous environments",
    7: "Insulation, protection and placing of conductors",
    8: "Earthing or other suitable precautions",
    9: "Integrity of referenced conductors",
    10: "Connections",
    11: "Means for protecting from excess of current",
    12: "Means for cutting off the supply and for isolation",
    13: "Precautions for work on equipment made dead",
    14: "Work on or near live conductors",
    15: "Working space, access and lighting",
    16: "Persons to be competent to prevent danger and injury",
    17: "Defence (Historical / Revoked)",
    18: "Mines: Exemption certificate",
    29: "Defence",
    30: "Exemption certificates",
    31: "Extension outside Great Britain",
    32: "Disapplication of duties",
    33: "Revocations and modifications",
}

# EAWR Statutory Duty Classification Mapping per HSE HSR25 & Case Law
EAWR_STATUTORY_DUTIES: Dict[str, str] = {
    "4(1)": DutyHolderType.REASONABLY_PRACTICABLE.value,
    "4(2)": DutyHolderType.REASONABLY_PRACTICABLE.value,
    "4(3)": DutyHolderType.REASONABLY_PRACTICABLE.value,
    "4(4)": DutyHolderType.ABSOLUTE.value,
    "5": DutyHolderType.ABSOLUTE.value,
    "6": DutyHolderType.ABSOLUTE.value,
    "7": DutyHolderType.ABSOLUTE.value,
    "8": DutyHolderType.ABSOLUTE.value,
    "8(1)": DutyHolderType.ABSOLUTE.value,
    "8(2)": DutyHolderType.ABSOLUTE.value,
    "9": DutyHolderType.ABSOLUTE.value,
    "10": DutyHolderType.ABSOLUTE.value,
    "11": DutyHolderType.ABSOLUTE.value,
    "12": DutyHolderType.ABSOLUTE.value,
    "12(1)": DutyHolderType.ABSOLUTE.value,
    "12(2)": DutyHolderType.ABSOLUTE.value,
    "12(3)": DutyHolderType.ABSOLUTE.value,
    "13": DutyHolderType.ABSOLUTE.value,
    "14": DutyHolderType.ABSOLUTE.value,
    "15": DutyHolderType.ABSOLUTE.value,
    "16": DutyHolderType.ABSOLUTE.value,
    "29": DutyHolderType.ABSOLUTE.value,
}

# Statutory defense under Regulation 29 applies to offences under these provisions:
REG_29_DEFENSE_REGS = {
    "4(4)", "5", "8", "8(1)", "8(2)", "9", "10", "11",
    "12", "12(1)", "12(2)", "12(3)", "13", "14", "15", "16"
}


class EAWRParser(AbstractBaseRegulationParser):
    """
    Parser for UK Statutory Instrument: The Electricity at Work Regulations 1989
    and HSE Guidance Publication HSR25.
    """

    @property
    def parser_name(self) -> str:
        return "Electricity at Work Regulations 1989 Parser (EAWR / HSR25)"

    def can_parse(self, text: str, file_name: Optional[str] = None) -> bool:
        """Checks whether the document is EAWR 1989 or HSE HSR25."""
        if file_name:
            fn_lower = file_name.lower()
            # Explicit negative exclusion for other standards
            if any(term in fn_lower for term in ["best_practice", "best-practice", "bpg", "puwer", "hasawa", "nist", "approved_document"]):
                return False
            if any(term in fn_lower for term in ["eawr", "hsr25", "eaw act", "electricity_at_work"]):
                return True

        lower_head = text[:2500].lower()
        if "best practice guide" in lower_head or "classification codes" in lower_head:
            return False
        if "provision and use of work equipment" in lower_head:
            return False
        if "health and safety at work etc. act" in lower_head and "regulations 1989" not in lower_head:
            return False

        lower_text = text.lower()
        if "electricity at work regulations" in lower_text or "hsr25" in lower_text:
            return True
        if "regulation 4" in lower_text and ("systems, work activities" in lower_text or "so far as is reasonably practicable" in lower_text):
            return True

        return False

    def parse(
        self,
        text: str,
        standard_name: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RegulatoryChunk]:
        standard = standard_name or "Electricity at Work Regulations 1989"
        is_hsr25 = "hsr25" in text.lower() or (file_metadata and "hsr25" in str(file_metadata).lower())
        doc_type = DocumentType.HSE_MEMORANDUM.value if is_hsr25 else DocumentType.STATUTORY_INSTRUMENT.value

        clean_text = text.replace('\r\n', '\n').strip()

        if is_hsr25:
            chunks = self._parse_hsr25(clean_text, standard, doc_type, file_metadata)
        else:
            chunks = self._parse_legislation(clean_text, standard, doc_type, file_metadata)

        if not chunks:
            logger.warning("Primary EAWR extraction yielded no chunks, falling back to broad clause parser.")
            chunks = self._parse_broad_eawr_clauses(clean_text, standard, doc_type, file_metadata)

        logger.info(f"EAWRParser successfully extracted {len(chunks)} regulatory chunks for '{standard}'.")
        return chunks

    def _parse_legislation(
        self,
        text: str,
        standard: str,
        doc_type: str,
        file_metadata: Optional[Dict[str, Any]]
    ) -> List[RegulatoryChunk]:
        """
        Parses statutory legislation format (e.g. SI 1989/635 / EAW ACT Full.pdf).
        Skips Table of Contents / Arrangement of Regulations, removes page footnotes,
        cuts off before Schedules, and extracts clauses 1 to 33.
        """
        idx_part1 = text.find('PART I')
        if idx_part1 == -1:
            idx_part1 = text.find('Citation and commencement')
        substantive = text[idx_part1:] if idx_part1 != -1 else text

        # Cut off before schedules (which have their own numbering starting at 1)
        sched_idx = substantive.find('\nSCHEDULE')
        if sched_idx != -1:
            substantive = substantive[:sched_idx]

        # Clean running headers, footers, and statutory footnotes
        substantive = re.sub(r'Document Generated:[^\n]*', '', substantive)
        substantive = re.sub(r'Changes to legislation:[^\n]*', '', substantive)
        substantive = re.sub(r'Commencement Information[^\n]*\nI\d+[^\n]*', '', substantive)
        substantive = re.sub(r'\n\s*\(\d+\)\s+\d{4}\s+c\.\s+\d+.*', '', substantive)

        pattern = re.compile(
            r'(?:^|\n)(?:([A-Z][^\n]+)\n)?\s*(\d{1,2})[\.·\u2014\-]+(?:\s*\(([0-9a-zA-Z]+)\))?\s*(.*?)(?=(?:\n(?:[^\n]+\n)?\s*\d{1,2}[\.·\u2014\-]+)|$)',
            re.DOTALL
        )

        chunks: List[RegulatoryChunk] = []
        for m in pattern.finditer(substantive):
            title = (m.group(1) or "").strip()
            reg_num = int(m.group(2))
            initial_sub = m.group(3)
            body = m.group(4).strip()

            parent_title = EAWR_KNOWN_TITLES.get(reg_num, title or f"Regulation {reg_num}")
            reg_label = f"Regulation {reg_num}"

            if initial_sub:
                full_sub_text = f"({initial_sub}) {body}"
                sub_pattern = re.compile(r'(?:^|\n)\s*\((\d+)\)\s*(.*?)(?=(?:\n\s*\(\d+\))|$)', re.DOTALL)
                sub_matches = list(sub_pattern.finditer(full_sub_text))
                seen_subs = set()
                if sub_matches:
                    for sm in sub_matches:
                        s_num = sm.group(1).strip()
                        if s_num in seen_subs:
                            continue
                        s_text = sm.group(2).strip()
                        # Skip footnote remnants that look like statute citations
                        if len(s_text) < 20 and re.match(r'^\d{4}\s+c\.\s+\d+', s_text):
                            continue
                        seen_subs.add(s_num)

                        s_label = f"{reg_label}({s_num})"
                        key = f"{reg_num}({s_num})"
                        duty = EAWR_STATUTORY_DUTIES.get(
                            key,
                            DutyHolderType.ABSOLUTE.value if "shall" in s_text.lower() else DutyHolderType.NOT_APPLICABLE.value
                        )
                        has_defense = key in REG_29_DEFENSE_REGS or str(reg_num) in REG_29_DEFENSE_REGS
                        chunks.append(RegulatoryChunk(
                            standard=standard,
                            regulation_number=reg_label,
                            sub_clause=s_label,
                            duty_holder=duty,
                            defense_available=has_defense,
                            parent_title=parent_title,
                            raw_text=f"({s_num}) {s_text}",
                            document_type=doc_type,
                            metadata={"eawr_regulation": reg_num, "sub_clause_number": int(s_num), "file_metadata": file_metadata or {}}
                        ))
                else:
                    chunks.append(RegulatoryChunk(
                        standard=standard,
                        regulation_number=reg_label,
                        sub_clause=f"{reg_label}({initial_sub})",
                        duty_holder=DutyHolderType.ABSOLUTE.value,
                        defense_available=str(reg_num) in REG_29_DEFENSE_REGS,
                        parent_title=parent_title,
                        raw_text=body,
                        document_type=doc_type,
                        metadata={"eawr_regulation": reg_num, "file_metadata": file_metadata or {}}
                    ))
            else:
                key = str(reg_num)
                duty = EAWR_STATUTORY_DUTIES.get(key, DutyHolderType.ABSOLUTE.value)
                has_defense = key in REG_29_DEFENSE_REGS
                chunks.append(RegulatoryChunk(
                    standard=standard,
                    regulation_number=reg_label,
                    sub_clause=reg_label,
                    duty_holder=duty,
                    defense_available=has_defense,
                    parent_title=parent_title,
                    raw_text=body,
                    document_type=doc_type,
                    metadata={"eawr_regulation": reg_num, "file_metadata": file_metadata or {}}
                ))

        return chunks

    def _parse_hsr25(
        self,
        text: str,
        standard: str,
        doc_type: str,
        file_metadata: Optional[Dict[str, Any]]
    ) -> List[RegulatoryChunk]:
        """
        Parses HSE Memorandum of Guidance HSR25.
        Extracts statutory regulation clauses and binds corresponding HSE guidance notes.
        """
        sub_start = text.find('Regulation 1 Citation and commencement', 5000)
        if sub_start == -1:
            sub_start = text.find('Regulation 3 Persons on whom', 5000)
        substantive = text[sub_start:] if sub_start != -1 else text

        reg_header_pattern = re.compile(
            r'(?:^|\n)\s*Regulation\s+(\d{1,2})\b\s*([^\n\(\d]+?)(?=\n|$)',
            re.MULTILINE
        )

        matches = list(reg_header_pattern.finditer(substantive))
        valid_sections = []
        last_reg_num = 0
        for m in matches:
            reg_num = int(m.group(1))
            title = m.group(2).strip()
            if reg_num in EAWR_KNOWN_TITLES and reg_num >= last_reg_num:
                valid_sections.append((reg_num, title, m.start()))
                last_reg_num = reg_num

        chunks: List[RegulatoryChunk] = []
        for i, (reg_num, raw_title, start_idx) in enumerate(valid_sections):
            end_idx = valid_sections[i+1][2] if i + 1 < len(valid_sections) else len(substantive)
            block = substantive[start_idx:end_idx].strip()

            parent_title = EAWR_KNOWN_TITLES.get(reg_num, raw_title or f"Regulation {reg_num}")
            reg_label = f"Regulation {reg_num}"

            # Split Statutory text and Guidance notes
            guidance_split = re.split(rf'\n\s*Guidance\s+{reg_num}\b', block, maxsplit=1, flags=re.IGNORECASE)
            statutory_text = guidance_split[0].strip()
            guidance_text = guidance_split[1].strip() if len(guidance_split) > 1 else None

            lines = statutory_text.split('\n', 1)
            statutory_body = lines[1].strip() if len(lines) > 1 else lines[0].strip()

            # Handle 'Regulation X (1)' on initial line
            statutory_body = re.sub(rf'^Regulation\s+{reg_num}\s*', '', statutory_body).strip()
            if not statutory_body.startswith('('):
                statutory_body = re.sub(r'^(?:[^\n\(]+)\s*\((\d+)\)', r'(\1)', statutory_body)

            sub_pattern = re.compile(r'(?:^|\n)\s*\((\d+)\)\s*(.*?)(?=(?:\n\s*\(\d+\))|$)', re.DOTALL)
            sub_matches = list(sub_pattern.finditer(statutory_body))

            if sub_matches:
                for sm in sub_matches:
                    s_num = sm.group(1).strip()
                    s_text = sm.group(2).strip()
                    s_label = f"{reg_label}({s_num})"
                    key = f"{reg_num}({s_num})"
                    duty = EAWR_STATUTORY_DUTIES.get(key, DutyHolderType.ABSOLUTE.value)
                    has_defense = key in REG_29_DEFENSE_REGS or str(reg_num) in REG_29_DEFENSE_REGS

                    # Link specific guidance for sub-clause if available
                    sub_guidance = None
                    if guidance_text:
                        sub_g_match = re.search(
                            rf'Regulation\s+{reg_num}\({s_num}\)(.*?)(?=(?:Regulation\s+{reg_num}\(\d+\)|$))',
                            guidance_text,
                            re.DOTALL
                        )
                        if sub_g_match:
                            sub_guidance = sub_g_match.group(1).strip()
                        else:
                            sub_guidance = guidance_text[:1200]

                    chunks.append(RegulatoryChunk(
                        standard=standard,
                        regulation_number=reg_label,
                        sub_clause=s_label,
                        duty_holder=duty,
                        defense_available=has_defense,
                        parent_title=parent_title,
                        raw_text=f"({s_num}) {s_text}",
                        guidance_notes=sub_guidance,
                        document_type=doc_type,
                        metadata={
                            "eawr_regulation": reg_num,
                            "sub_clause_number": int(s_num),
                            "file_metadata": file_metadata or {}
                        }
                    ))
            else:
                key = str(reg_num)
                duty = EAWR_STATUTORY_DUTIES.get(key, DutyHolderType.ABSOLUTE.value)
                has_defense = key in REG_29_DEFENSE_REGS
                chunks.append(RegulatoryChunk(
                    standard=standard,
                    regulation_number=reg_label,
                    sub_clause=reg_label,
                    duty_holder=duty,
                    defense_available=has_defense,
                    parent_title=parent_title,
                    raw_text=statutory_body,
                    guidance_notes=guidance_text,
                    document_type=doc_type,
                    metadata={"eawr_regulation": reg_num, "file_metadata": file_metadata or {}}
                ))

        return chunks

    def _parse_broad_eawr_clauses(
        self,
        text: str,
        standard: str,
        doc_type: str,
        file_metadata: Optional[Dict[str, Any]]
    ) -> List[RegulatoryChunk]:
        """
        Fallback parser if documents have custom markdown formatting or non-standard headers.
        """
        chunks: List[RegulatoryChunk] = []
        paragraphs = text.split("\n\n")

        current_reg = "Regulation 4"
        current_title = "Systems, work activities and protective equipment"

        for p in paragraphs:
            p = p.strip()
            if not p or len(p) < 20:
                continue

            reg_match = re.search(r'\b(?:Regulation|Reg)\s*(\d{1,2})\b', p, re.IGNORECASE)
            if reg_match:
                reg_num = int(reg_match.group(1))
                current_reg = f"Regulation {reg_num}"
                current_title = EAWR_KNOWN_TITLES.get(reg_num, f"Regulation {reg_num} Provisions")

            sub_match = re.search(r'\((\d+)\)', p)
            sub_clause = f"{current_reg}({sub_match.group(1)})" if sub_match else current_reg

            duty = self.infer_statutory_duty_holder(p, current_reg)
            reg_num_val = int(current_reg.split()[-1]) if current_reg.split()[-1].isdigit() else 4
            has_defense = str(reg_num_val) in REG_29_DEFENSE_REGS

            chunks.append(RegulatoryChunk(
                standard=standard,
                regulation_number=current_reg,
                sub_clause=sub_clause,
                duty_holder=duty,
                defense_available=has_defense,
                parent_title=current_title,
                raw_text=p,
                document_type=doc_type,
                metadata={"file_metadata": file_metadata or {}}
            ))

        return chunks
