"""
Regulation Parsers Package.
"""
from apps.compliance_core.ingestion.parsers.base import AbstractBaseRegulationParser
from apps.compliance_core.ingestion.parsers.eawr import EAWRParser
from apps.compliance_core.ingestion.parsers.esf_bpg4 import ESFBPG4Parser
from apps.compliance_core.ingestion.parsers.registry import (
    RegulationParserRegistry,
    GenericRegulationParser,
    get_parser_registry
)

__all__ = [
    'AbstractBaseRegulationParser',
    'EAWRParser',
    'ESFBPG4Parser',
    'GenericRegulationParser',
    'RegulationParserRegistry',
    'get_parser_registry',
]
