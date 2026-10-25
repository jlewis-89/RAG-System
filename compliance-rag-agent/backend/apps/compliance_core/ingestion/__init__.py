"""
Compliance Core Ingestion Module.
Exports parsing and extraction services for UK statutory and engineering standards.
"""
from apps.compliance_core.schemas import RegulatoryChunk, IngestionReport, DutyHolderType, DocumentType
from apps.compliance_core.ingestion.extractors import extract_text_from_file, DocumentExtractionError
from apps.compliance_core.ingestion.service import DocumentIngestionService
from apps.compliance_core.ingestion.parsers import (
    AbstractBaseRegulationParser,
    EAWRParser,
    ESFBPG4Parser,
    get_parser_registry,
)

__all__ = [
    'RegulatoryChunk',
    'IngestionReport',
    'DutyHolderType',
    'DocumentType',
    'extract_text_from_file',
    'DocumentExtractionError',
    'DocumentIngestionService',
    'AbstractBaseRegulationParser',
    'EAWRParser',
    'ESFBPG4Parser',
    'get_parser_registry',
]
