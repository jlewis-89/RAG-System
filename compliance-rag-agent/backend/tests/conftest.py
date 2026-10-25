"""
Pytest configuration and shared fixtures for compliance RAG pipeline tests.
"""

import os
import sys
from pathlib import Path
import django
import pytest

# Ensure backend root and apps are on python path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
APPS_DIR = BACKEND_ROOT / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.compliance_core.services.compliance_engine import get_compliance_engine, ComplianceReasoningEngine
from apps.compliance_core.services.vector_store import get_vector_store, RegulationVectorStore


@pytest.fixture(scope="session")
def engine() -> ComplianceReasoningEngine:
    """Provides the singleton Compliance Reasoning Engine."""
    return get_compliance_engine()


@pytest.fixture(scope="session")
def vector_store() -> RegulationVectorStore:
    """Provides the singleton Regulation Vector Store."""
    return get_vector_store()
