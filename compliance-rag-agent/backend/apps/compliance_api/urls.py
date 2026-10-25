"""
URL Routing for Compliance API v1.
Endpoints:
- POST /api/v1/compliance/query/
- GET  /api/v1/compliance/standards/
- POST /api/v1/compliance/audit/<id>/feedback/
- GET  /api/v1/compliance/audit/
- GET  /api/v1/compliance/audit/<id>/
- POST /api/v1/compliance/auth/token/
"""

from django.urls import path
from apps.compliance_api.views import (
    ComplianceQueryView,
    ComplianceStandardsListView,
    ComplianceAuditFeedbackView,
    ComplianceAuditLogsListView,
    ComplianceAuditLogDetailView,
    ObtainComplianceTokenView,
)

app_name = 'compliance_api'

urlpatterns = [
    # Core Compliance Query Endpoint
    path('query/', ComplianceQueryView.as_view(), name='compliance_query'),

    # Regulatory Standards & Ingested Version Registry
    path('standards/', ComplianceStandardsListView.as_view(), name='compliance_standards'),

    # Field Engineer Accuracy Feedback & Auditing
    path('audit/<int:id>/feedback/', ComplianceAuditFeedbackView.as_view(), name='audit_feedback'),
    path('audit/', ComplianceAuditLogsListView.as_view(), name='audit_logs_list'),
    path('audit/<int:id>/', ComplianceAuditLogDetailView.as_view(), name='audit_log_detail'),

    # Session & Token Authentication
    path('auth/token/', ObtainComplianceTokenView.as_view(), name='api_token_auth'),
]
