"""
URL configuration for compliance-rag-agent project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Compliance API v1 Endpoints (Surveyor Query, Standards, Audit Feedback)
    path('api/v1/compliance/', include('apps.compliance_api.urls', namespace='compliance_api')),
    # Legacy RAG Endpoints
    path('api/rag/', include('apps.rag.urls', namespace='rag')),
]

