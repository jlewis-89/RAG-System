"""
DRF Serializers for Engineering Compliance RAG System.
"""
from rest_framework import serializers
from apps.rag.models import ComplianceStandard, ComplianceDocument, ComplianceAuditLog


class ComplianceStandardSerializer(serializers.ModelSerializer):
    documents_count = serializers.IntegerField(source='documents.count', read_only=True)

    class Meta:
        model = ComplianceStandard
        fields = [
            'id',
            'code',
            'name',
            'authority',
            'version',
            'description',
            'is_active',
            'documents_count',
            'created_at',
            'updated_at',
        ]


class ComplianceDocumentSerializer(serializers.ModelSerializer):
    standard_code = serializers.CharField(source='standard.code', read_only=True)

    class Meta:
        model = ComplianceDocument
        fields = [
            'id',
            'standard',
            'standard_code',
            'title',
            'source_identifier',
            'status',
            'total_chunks',
            'document_metadata',
            'error_message',
            'uploaded_at',
            'updated_at',
        ]


class ComplianceAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceAuditLog
        fields = [
            'id',
            'query_text',
            'verdict',
            'confidence_score',
            'answer_text',
            'citations',
            'standard_filter',
            'latency_ms',
            'created_at',
        ]
