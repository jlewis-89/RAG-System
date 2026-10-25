"""
Base Abstract Class for Hierarchical Regulation & Standard Parsers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from apps.compliance_core.schemas import RegulatoryChunk, DutyHolderType


class AbstractBaseRegulationParser(ABC):
    """
    Abstract interface for parsing legal, statutory, and engineering guidance documents
    into hierarchical, unsevered RegulatoryChunks.
    """

    @property
    @abstractmethod
    def parser_name(self) -> str:
        """Name or identifier of the parser."""
        pass

    @abstractmethod
    def can_parse(self, text: str, file_name: Optional[str] = None) -> bool:
        """Determines if this parser is suitable for the given text or filename."""
        pass

    @abstractmethod
    def parse(
        self,
        text: str,
        standard_name: Optional[str] = None,
        file_metadata: Optional[Dict[str, Any]] = None
    ) -> List[RegulatoryChunk]:
        """
        Parses full document text into structured, validated RegulatoryChunk instances.
        """
        pass

    @staticmethod
    def infer_statutory_duty_holder(clause_text: str, reg_number: Optional[str] = None) -> str:
        """
        Infers whether a UK health and safety statutory duty is Absolute or qualified
        by the 'reasonably practicable' test (SFARP).
        """
        lower = clause_text.lower()

        # 1. Check for statutory qualification phrases
        if (
            "so far as is reasonably practicable" in lower
            or "so far as reasonably practicable" in lower
            or "reasonably practicable" in lower
        ):
            return DutyHolderType.REASONABLY_PRACTICABLE.value

        # 2. Check for other qualified terms
        if "as may be necessary" in lower or "where necessary" in lower or "adequate precautions" in lower:
            # Still often treated as qualified, but if mandatory 'shall' without SFARP, can be absolute
            if "shall" in lower or "must" in lower:
                return DutyHolderType.ABSOLUTE.value
            return DutyHolderType.QUALIFIED.value

        # 3. Direct mandatory duties without qualification are Absolute in UK statutory law
        if "shall" in lower or "must" in lower or "no person shall" in lower or "shall not" in lower:
            return DutyHolderType.ABSOLUTE.value

        # 4. Purely guidance/advisory
        if "should" in lower or "recommended" in lower or "guidance" in lower:
            return DutyHolderType.ADVISORY.value

        return DutyHolderType.NOT_APPLICABLE.value
