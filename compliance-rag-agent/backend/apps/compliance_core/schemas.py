"""
Pydantic v2 Metadata Schemas for Statutory & Engineering Regulatory Chunks.
Specialized for UK Electrical Standards (EAWR 1989, HSR25, ESF BPG4).
"""

import re
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class DutyHolderType(str, Enum):
    ABSOLUTE = "Absolute"
    REASONABLY_PRACTICABLE = "Reasonably Practicable"
    QUALIFIED = "Qualified"
    ADVISORY = "Advisory / Guidance"
    NOT_APPLICABLE = "Not Applicable"


class DocumentType(str, Enum):
    STATUTORY_INSTRUMENT = "Statutory Instrument"
    HSE_MEMORANDUM = "HSE Guidance (HSR25)"
    INDUSTRY_BEST_PRACTICE = "Industry Best Practice (ESF)"
    APPROVED_CODE_OF_PRACTICE = "Approved Code of Practice (ACOP)"
    TECHNICAL_SPECIFICATION = "Technical Specification"


class RegulatoryChunk(BaseModel):
    """
    Structured atomic regulatory clause or guidance chunk.
    Preserves exact legal hierarchy and duty holder qualifications without arbitrary character cuts.
    """
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=False,
        populate_by_name=True,
        str_strip_whitespace=True
    )

    # Core required fields specified in requirements
    standard: str = Field(
        ...,
        description="Statutory regulation or engineering standard name (e.g. 'Electricity at Work Regulations 1989')"
    )
    regulation_number: str = Field(
        ...,
        description="Formal regulation or section designation (e.g. 'Regulation 4', 'Regulation 16', 'Section 4')"
    )
    sub_clause: str = Field(
        ...,
        description="Precise sub-clause or item designation (e.g. 'Regulation 4(1)', 'Regulation 4(2)', 'Section 4.1')"
    )
    duty_holder: str = Field(
        ...,
        description="Statutory nature of duty: 'Absolute' vs 'Reasonably Practicable' or 'Advisory / Guidance'"
    )
    parent_title: str = Field(
        ...,
        description="Parent regulation heading or chapter title (e.g. 'Systems, work activities and protective equipment')"
    )
    raw_text: str = Field(
        ...,
        min_length=5,
        description="Complete, unsevered verbatim statutory text of the clause"
    )

    # Enriched legal & retrieval fields
    chunk_id: Optional[str] = Field(
        default=None,
        description="Deterministic unique chunk identifier"
    )
    document_type: Optional[str] = Field(
        default=DocumentType.STATUTORY_INSTRUMENT.value,
        description="Classification of source document"
    )
    guidance_notes: Optional[str] = Field(
        default=None,
        description="Associated explanatory guidance notes (e.g. from HSE HSR25 memorandum)"
    )
    defense_available: bool = Field(
        default=False,
        description="Whether the Regulation 29 statutory due diligence defense is available for this regulation"
    )
    classification_code: Optional[str] = Field(
        default=None,
        description="Observation classification code if applicable (e.g. C1, C2, C3, FI from ESF BPG4)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary additional legal metadata, citations, and source coordinates"
    )

    @field_validator('standard', 'regulation_number', 'sub_clause', 'parent_title', mode='before')
    @classmethod
    def clean_text_headers(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Field cannot be empty or solely whitespace.")
        # Normalize consecutive spaces and carriage returns
        return re.sub(r'\s+', ' ', str(v)).strip()

    @field_validator('raw_text', mode='before')
    @classmethod
    def clean_raw_text(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("raw_text cannot be empty.")
        clean = v.replace('\r\n', '\n').strip()
        # Remove hyphenated line-breaks created by PDF columns (e.g. 'rea-\nsonably' -> 'reasonably')
        clean = re.sub(r'(\b[a-zA-Z]+)-\n\s*([a-zA-Z]+\b)', r'\1\2', clean)
        return clean

    @model_validator(mode='after')
    def validate_and_enrich(self) -> 'RegulatoryChunk':
        # Automatically generate deterministic chunk_id if not supplied
        if not self.chunk_id:
            std_slug = re.sub(r'[^a-zA-Z0-9]+', '_', self.standard.lower()).strip('_')
            reg_slug = re.sub(r'[^a-zA-Z0-9()]+', '_', self.regulation_number.lower()).strip('_')
            sub_slug = re.sub(r'[^a-zA-Z0-9()]+', '_', self.sub_clause.lower()).strip('_')
            self.chunk_id = f"{std_slug}::{reg_slug}::{sub_slug}"

        # Standardize EAWR Regulation 29 defense availability
        # EAWR Reg 29 specifies defense for offences under regulations:
        # 4(4), 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, or 25
        reg_match = re.search(r'\b(?:Regulation|Reg)\s*(\d+)', self.regulation_number, re.IGNORECASE)
        if reg_match:
            reg_num = int(reg_match.group(1))
            if "electricity at work" in self.standard.lower() or "eawr" in self.standard.lower():
                if reg_num in [5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 25]:
                    self.defense_available = True
                elif reg_num == 4 and "4(4)" in self.sub_clause:
                    self.defense_available = True

        # Sanity check duty_holder consistency:
        # If the clause explicitly states "so far as is reasonably practicable", it must be Reasonably Practicable
        lower_text = self.raw_text.lower()
        if "so far as is reasonably practicable" in lower_text or "reasonably practicable" in lower_text:
            if self.duty_holder == DutyHolderType.ABSOLUTE.value:
                # Correct it to Reasonably Practicable
                self.duty_holder = DutyHolderType.REASONABLY_PRACTICABLE.value

        return self


class IngestionReport(BaseModel):
    """
    Summary outcome of an ingestion job for CLI reporting and API responses.
    """
    source_file: str
    standard_name: str
    document_type: str
    total_chunks: int
    regulations_found: List[str]
    duty_breakdown: Dict[str, int]
    chroma_upserted: bool = False
    database_saved: bool = False
    duration_seconds: float
    chunks: List[RegulatoryChunk] = Field(default_factory=list)


# ==============================================================================
# Compliance Reasoning Engine Response Schemas
# ==============================================================================

class ComplianceStatus(str, Enum):
    """
    Statutory & Engineering Compliance Verdict Taxonomy.
    Directly aligns with UK Electrical Safety First BPG4 observation codes
    and statutory EAWR 1989 legal determinations.
    """
    COMPLIANT = "COMPLIANT"
    POTENTIALLY_DANGEROUS = "POTENTIALLY_DANGEROUS"  # C2 equivalent: Urgent remedial action required
    IMMEDIATE_DANGER = "IMMEDIATE_DANGER"  # C1 equivalent: Immediate risk of injury/death
    IMPROVEMENT_RECOMMENDED = "IMPROVEMENT_RECOMMENDED"  # C3 equivalent: Improvement recommended
    INSUFFICIENT_DATA_FURTHER_INVESTIGATION = "INSUFFICIENT_DATA_FURTHER_INVESTIGATION"  # FI equivalent: Further investigation required


class CitedClause(BaseModel):
    """
    Individual regulatory citation referencing statutory instrument or standard.
    Strictly preserves unsevered verbatim quotes to prevent fabrication.
    """
    model_config = ConfigDict(
        use_enum_values=True,
        str_strip_whitespace=True,
        populate_by_name=True
    )

    standard: str = Field(
        ...,
        description="Formal regulation or engineering standard name (e.g. 'Electricity at Work Regulations 1989')"
    )
    clause_number: str = Field(
        ...,
        description="Regulation number, section, or sub-clause designation (e.g. 'Regulation 4(4)', 'Regulation 14')"
    )
    verbatim_quote: str = Field(
        ...,
        min_length=1,
        description="Exact verbatim excerpt from retrieved statutory or standard text without modification"
    )

    @field_validator('standard', 'clause_number', mode='before')
    @classmethod
    def clean_citation_text(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Citation standard and clause_number cannot be empty.")
        return re.sub(r'\s+', ' ', str(v)).strip()

    @field_validator('verbatim_quote', mode='before')
    @classmethod
    def clean_quote_text(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("verbatim_quote cannot be empty.")
        return str(v).strip()


class ComplianceResponse(BaseModel):
    """
    Pydantic v2 Compliance Reasoning Schema.
    Philosophy: 'Show the engineer why the answer was reached, not just the answer. Never fabricate compliance decisions.'
    """
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        populate_by_name=True
    )

    compliance_status: ComplianceStatus = Field(
        ...,
        description="Definitive statutory/standard compliance verdict"
    )
    summary_verdict: str = Field(
        ...,
        min_length=10,
        description="High-level natural language explanation (2-3 sentences explaining the engineering rationale)"
    )
    cited_clauses: List[CitedClause] = Field(
        default_factory=list,
        description="Explicit list of standard clauses and verbatim quotes substantiating the decision"
    )
    mandatory_requirements: List[str] = Field(
        default_factory=list,
        description="Statutory duty-holder obligations ('shall' / absolute duties from applicable legislation)"
    )
    inspection_checks: List[str] = Field(
        default_factory=list,
        description="Bulleted list of physical checks and tests the surveyor must verify on site"
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Float between 0.0 and 1.0 reflecting context relevance, coverage, and statutory certainty"
    )

    # Operational & Audit Trail Metadata
    model_used: Optional[str] = Field(
        default=None,
        description="Identifier of LLM provider or model that produced the reasoning output"
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="Reasoning evaluation latency in milliseconds"
    )
    retrieved_chunks_count: Optional[int] = Field(
        default=0,
        description="Number of candidate regulatory chunks evaluated"
    )

    @field_validator('confidence_score', mode='before')
    @classmethod
    def round_and_clamp_score(cls, v: Any) -> float:
        try:
            val = float(v)
            return max(0.0, min(1.0, round(val, 3)))
        except (ValueError, TypeError):
            return 0.0

    @field_validator('summary_verdict', mode='before')
    @classmethod
    def clean_verdict(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("summary_verdict cannot be empty.")
        return re.sub(r'\s+', ' ', str(v)).strip()


class StreamingChunk(BaseModel):
    """
    Streaming event emitted during incremental LLM generation and JSON validation.
    """
    event: str = Field(..., description="Event type: 'token', 'partial', 'validated_response', or 'error'")
    token: Optional[str] = Field(default=None, description="Incremental raw text or token delta")
    partial_data: Optional[Dict[str, Any]] = Field(default=None, description="Partially parsed JSON state")
    validated_response: Optional[ComplianceResponse] = Field(default=None, description="Final fully validated response")
    error: Optional[str] = Field(default=None, description="Error message if validation or generation failed")

