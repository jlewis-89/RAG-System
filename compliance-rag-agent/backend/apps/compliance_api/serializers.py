"""
DRF Serializers for Compliance API.
Implements strict request validation, structured compliance response formatting,
and field engineer accuracy feedback processing.
"""

from rest_framework import serializers
from apps.compliance_api.models import (
    ComplianceQuery,
    ComplianceAuditLog,
    InspectionContext,
    UserFeedback,
)


class CitedClauseSerializer(serializers.Serializer):
    """
    Sub-object representing a specific cited statutory clause with verbatim text.
    """
    standard = serializers.CharField(max_length=255)
    clause_number = serializers.CharField(max_length=128)
    verbatim_quote = serializers.CharField()


class ComplianceQueryRequestSerializer(serializers.Serializer):
    """
    Strict request serializer for POST /api/v1/compliance/query/.
    """
    query = serializers.CharField(
        required=True,
        min_length=3,
        max_length=4000,
        trim_whitespace=True,
        error_messages={
            'required': 'Query text is mandatory for compliance reasoning.',
            'blank': 'Query text cannot be blank or solely whitespace.',
            'min_length': 'Query text must contain at least 3 characters.'
        }
    )
    inspection_context = serializers.ChoiceField(
        choices=InspectionContext.choices,
        default=InspectionContext.DOMESTIC,
        error_messages={
            'invalid_choice': "Invalid inspection context. Must be one of: Domestic, Commercial, Industrial, Agricultural, Special Installation, General."
        }
    )
    standard_filter = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=255
    )
    duty_filter = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=64
    )
    top_k = serializers.IntegerField(
        required=False,
        default=5,
        min_value=1,
        max_value=25,
        error_messages={
            'min_value': 'top_k must be at least 1.',
            'max_value': 'top_k cannot exceed 25.'
        }
    )
    provider = serializers.ChoiceField(
        choices=['ollama', 'groq', 'anthropic', 'deterministic', 'auto'],
        required=False,
        default='auto',
        error_messages={
            'invalid_choice': "Provider must be 'ollama', 'groq', 'anthropic', 'deterministic', or 'auto'."
        }
    )
    model = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=128
    )
    stream = serializers.BooleanField(
        required=False,
        default=False
    )

    def validate_query(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Query text cannot be empty or solely whitespace.")
        return cleaned


class ComplianceQueryResponseSerializer(serializers.Serializer):
    """
    Structured response serializer for POST /api/v1/compliance/query/.
    Strictly follows the Pydantic compliance schema + operational database audit IDs.
    """
    query_id = serializers.IntegerField()
    audit_id = serializers.IntegerField()
    compliance_status = serializers.CharField()
    summary_verdict = serializers.CharField()
    cited_clauses = CitedClauseSerializer(many=True)
    mandatory_requirements = serializers.ListField(child=serializers.CharField())
    inspection_checks = serializers.ListField(child=serializers.CharField())
    confidence_score = serializers.FloatField()
    inspection_context = serializers.CharField()
    retrieved_chunks_count = serializers.IntegerField()
    latency_ms = serializers.FloatField()
    model_used = serializers.CharField(allow_blank=True, allow_null=True)
    created_at = serializers.DateTimeField()


class ComplianceFeedbackRequestSerializer(serializers.Serializer):
    """
    Strict request serializer for POST /api/v1/compliance/audit/{id}/feedback/.
    """
    feedback = serializers.ChoiceField(
        choices=UserFeedback.choices,
        required=True,
        error_messages={
            'required': "Feedback status is required (e.g. 'approved', 'flagged', 'rejected', 'pending').",
            'invalid_choice': "Invalid feedback value. Must be 'approved', 'flagged', 'rejected', or 'pending'."
        }
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=5000,
        trim_whitespace=True
    )


class ComplianceAuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for ComplianceAuditLog inspection records.
    """
    query_text = serializers.CharField(source='query.query_text', read_only=True)
    inspection_context = serializers.CharField(source='query.inspection_context', read_only=True)
    feedback_by_username = serializers.CharField(source='feedback_by.username', read_only=True, default=None)

    class Meta:
        model = ComplianceAuditLog
        fields = [
            'id',
            'query_id',
            'query_text',
            'inspection_context',
            'full_input',
            'retrieved_context_ids',
            'generated_response',
            'response_time_ms',
            'user_feedback',
            'feedback_notes',
            'feedback_by_username',
            'feedback_at',
            'model_used',
            'created_at',
        ]
        read_only_fields = fields


class ComplianceStandardListSerializer(serializers.Serializer):
    """
    Serializer for GET /api/v1/compliance/standards/.
    Lists ingested standards, total indexed clauses, versions, and authority.
    """
    code = serializers.CharField()
    name = serializers.CharField()
    authority = serializers.CharField()
    version = serializers.CharField(allow_null=True, allow_blank=True)
    clause_count = serializers.IntegerField()
    document_count = serializers.IntegerField()
    is_active = serializers.BooleanField()
    description = serializers.CharField(allow_blank=True)
