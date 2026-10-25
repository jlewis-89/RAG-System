"""
URL routing for Compliance RAG API endpoints.
"""
from django.urls import path
from apps.rag.views import (
    HealthCheckView,
    QueryComplianceView,
    IngestDocumentView,
    SeedInitialStandardsView,
    ComplianceStandardsListView,
    ComplianceAuditLogsListView,
)

app_name = 'rag'

urlpatterns = [
    # System & Vector Store Health
    path('health/', HealthCheckView.as_view(), name='health'),
    
    # Core RAG Operations
    path('query/', QueryComplianceView.as_view(), name='query'),
    path('ingest/', IngestDocumentView.as_view(), name='ingest'),
    path('seed/', SeedInitialStandardsView.as_view(), name='seed'),
    
    # Metadata & Auditing
    path('standards/', ComplianceStandardsListView.as_view(), name='standards'),
    path('audit-logs/', ComplianceAuditLogsListView.as_view(), name='audit_logs'),
]
