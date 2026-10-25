"""
URL configuration for compliance-rag-agent project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # RAG Engine & Compliance Endpoints
    path('api/rag/', include('apps.rag.urls', namespace='rag')),
]
