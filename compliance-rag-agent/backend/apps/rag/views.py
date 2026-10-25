"""
DRF Views for Engineering Compliance RAG System.
Handles Querying, Ingestion, Standards Management, and Health Checks.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from pydantic import ValidationError

from apps.rag.models import ComplianceStandard, ComplianceDocument, ComplianceAuditLog
from apps.rag.serializers import (
    ComplianceStandardSerializer,
    ComplianceDocumentSerializer,
    ComplianceAuditLogSerializer
)
from apps.rag.schemas import (
    RAGQueryRequest,
    DocumentIngestRequest,
    HealthCheckResponse
)
from apps.rag.services.chroma import get_chroma_service
from apps.rag.services.rag_engine import ComplianceRAGEngine
from apps.rag.services.ingestion import ComplianceIngestionService

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    GET /api/rag/health/
    Health verification for DRF backend, SQLite/PostgreSQL, and ChromaDB persistent storage.
    """
    def get(self, request):
        try:
            chroma = get_chroma_service()
            stats = chroma.get_stats()
            chroma_status = "healthy"
            items_count = stats["total_items"]
            collection_name = stats["collection_name"]
        except Exception as e:
            logger.error(f"Chroma health check failed: {e}")
            chroma_status = f"unhealthy: {str(e)}"
            items_count = 0
            collection_name = "unavailable"

        # Check DB
        try:
            ComplianceStandard.objects.count()
            db_status = "healthy"
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

        payload = HealthCheckResponse(
            status="healthy" if chroma_status == "healthy" and db_status == "healthy" else "degraded",
            chroma_status=chroma_status,
            chroma_collection=collection_name,
            chroma_items_count=items_count,
            database_status=db_status,
            version="1.0.0-rc1"
        )
        return Response(payload.model_dump(), status=status.HTTP_200_OK)


class QueryComplianceView(APIView):
    """
    POST /api/rag/query/
    Audit a technical specification or engineering query against indexed regulatory standards.
    """
    def post(self, request):
        try:
            rag_req = RAGQueryRequest(**request.data)
        except ValidationError as e:
            return Response({"errors": e.errors()}, status=status.HTTP_400_BAD_REQUEST)

        try:
            engine = ComplianceRAGEngine()
            result = engine.query(rag_req)
            return Response(result.model_dump(), status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error executing RAG query: {e}", exc_info=True)
            return Response(
                {"error": "Failed to process compliance audit query", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IngestDocumentView(APIView):
    """
    POST /api/rag/ingest/
    Ingest a new engineering standard specification into ChromaDB persistent storage.
    """
    def post(self, request):
        try:
            ingest_req = DocumentIngestRequest(**request.data)
        except ValidationError as e:
            return Response({"errors": e.errors()}, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = ComplianceIngestionService()
            doc = service.ingest_document(
                title=ingest_req.title,
                standard_code=ingest_req.standard_code,
                content=ingest_req.content,
                source_identifier=ingest_req.source_identifier,
                custom_metadata=ingest_req.metadata
            )
            return Response({
                "document_id": doc.id,
                "title": doc.title,
                "standard_code": doc.standard.code if doc.standard else ingest_req.standard_code,
                "total_chunks": doc.total_chunks,
                "status": doc.status,
                "message": f"Successfully ingested and indexed {doc.total_chunks} chunks into ChromaDB."
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error ingesting document: {e}", exc_info=True)
            return Response(
                {"error": "Failed to ingest document", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SeedInitialStandardsView(APIView):
    """
    POST /api/rag/seed/
    Seed default sample engineering standards (ISO 9001, ASME Section VIII, IEC 61508)
    into ChromaDB and Django DB for instant demonstration.
    """
    def post(self, request):
        try:
            service = ComplianceIngestionService()
            indexed = service.seed_initial_standards()
            return Response({
                "status": "success",
                "message": f"Seeded {len(indexed)} initial engineering standard documents into ChromaDB.",
                "documents": [ComplianceDocumentSerializer(d).data for d in indexed]
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error seeding initial standards: {e}", exc_info=True)
            return Response(
                {"error": "Failed to seed standards", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ComplianceStandardsListView(APIView):
    """
    GET, POST /api/rag/standards/
    List all registered compliance standards or add a new standard authority.
    """
    def get(self, request):
        standards = ComplianceStandard.objects.all()
        serializer = ComplianceStandardSerializer(standards, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ComplianceStandardSerializer(data=request.data)
        if serializer.is_valid():
            standard = serializer.save()
            return Response(ComplianceStandardSerializer(standard).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ComplianceAuditLogsListView(APIView):
    """
    GET /api/rag/audit-logs/
    Retrieve historical compliance verification audits for regulatory accountability.
    """
    def get(self, request):
        logs = ComplianceAuditLog.objects.all().order_by('-created_at')[:50]
        serializer = ComplianceAuditLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
