"""
DRF API Views for Compliance Querying, Standards Inspection, and Audit Feedback.
Endpoints:
- POST /api/v1/compliance/query/
- GET  /api/v1/compliance/standards/
- POST /api/v1/compliance/audit/{id}/feedback/
- GET  /api/v1/compliance/audit/
- GET  /api/v1/compliance/audit/{id}/
- POST /api/v1/compliance/auth/token/
"""

import json
import logging
from django.utils import timezone
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import NotFound, ValidationError

from apps.compliance_api.models import (
    ComplianceQuery,
    ComplianceAuditLog,
    UserFeedback,
    InspectionContext,
)
from apps.compliance_api.serializers import (
    ComplianceQueryRequestSerializer,
    ComplianceQueryResponseSerializer,
    ComplianceFeedbackRequestSerializer,
    ComplianceAuditLogSerializer,
    ComplianceStandardListSerializer,
)
from apps.compliance_api.permissions import (
    IsFieldEngineerOrReadOnly,
    CanSubmitAuditFeedback,
    get_user_permission_tier,
)
from apps.compliance_core.services.compliance_engine import get_compliance_engine
from apps.rag.models import ComplianceStandard, ComplianceDocument

logger = logging.getLogger(__name__)


class ComplianceQueryView(APIView):
    """
    POST /api/v1/compliance/query/
    Accepts surveyor query + operational inspection context (Domestic, Commercial, Industrial).
    Executes grounded statutory compliance evaluation and logs complete audit trail.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsFieldEngineerOrReadOnly]

    def post(self, request):
        serializer = ComplianceQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        query_text = data['query']
        inspection_context = data.get('inspection_context', InspectionContext.DOMESTIC)
        standard_filter = data.get('standard_filter') or None
        duty_filter = data.get('duty_filter') or None
        top_k = data.get('top_k', 5)
        provider = data.get('provider', 'auto')
        model = data.get('model') or None
        is_stream = data.get('stream', False)

        # 1. Persist surveyor query record
        user = request.user if request.user and request.user.is_authenticated else None
        compliance_query = ComplianceQuery.objects.create(
            user=user,
            query_text=query_text,
            inspection_context=inspection_context,
            standard_filter=standard_filter or '',
            duty_filter=duty_filter or ''
        )

        engine = get_compliance_engine()
        # Operational context-enhanced query for statutory evaluation
        audit_query = f"[{inspection_context} Installation Audit]: {query_text}"

        # 2. Handle real-time streaming response
        if is_stream:
            def event_stream():
                stream_generator = engine.stream_reason(
                    query=audit_query,
                    standard_filter=standard_filter,
                    duty_filter=duty_filter,
                    top_k=top_k,
                    provider=provider,
                    model=model
                )
                final_response = None
                for event in stream_generator:
                    if event.event == "token":
                        yield f"data: {json.dumps({'event': 'token', 'token': event.token})}\n\n"
                    elif event.event == "partial":
                        yield f"data: {json.dumps({'event': 'partial', 'partial_data': event.partial_data})}\n\n"
                    elif event.event == "validated_response":
                        final_response = event.validated_response
                        # Create audit log on stream completion
                        if final_response:
                            context_ids = [c.clause_number for c in final_response.cited_clauses]
                            audit_log = ComplianceAuditLog.objects.create(
                                query=compliance_query,
                                full_input=data,
                                retrieved_context_ids=context_ids,
                                generated_response=final_response.model_dump(),
                                response_time_ms=final_response.latency_ms or 0.0,
                                user_feedback=UserFeedback.PENDING,
                                model_used=final_response.model_used or provider
                            )
                            payload = final_response.model_dump()
                            payload['query_id'] = compliance_query.id
                            payload['audit_id'] = audit_log.id
                            payload['inspection_context'] = inspection_context
                            payload['created_at'] = compliance_query.created_at.isoformat()
                            yield f"data: {json.dumps({'event': 'validated_response', 'response': payload})}\n\n"
                    elif event.event == "error":
                        yield f"data: {json.dumps({'event': 'error', 'error': event.error})}\n\n"

                yield "data: [DONE]\n\n"

            response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        # 3. Synchronous compliance evaluation
        compliance_response = engine.reason(
            query=audit_query,
            standard_filter=standard_filter,
            duty_filter=duty_filter,
            top_k=top_k,
            provider=provider,
            model=model
        )

        # 4. Extract retrieved chunk citation identifiers
        retrieved_ids = [f"{c.standard}::{c.clause_number}" for c in compliance_response.cited_clauses]

        # 5. Persist comprehensive ComplianceAuditLog
        audit_log = ComplianceAuditLog.objects.create(
            query=compliance_query,
            full_input=data,
            retrieved_context_ids=retrieved_ids,
            generated_response=compliance_response.model_dump(),
            response_time_ms=compliance_response.latency_ms or 0.0,
            user_feedback=UserFeedback.PENDING,
            model_used=compliance_response.model_used or provider
        )

        # 6. Format structured JSON payload
        output_data = {
            'query_id': compliance_query.id,
            'audit_id': audit_log.id,
            'compliance_status': compliance_response.compliance_status,
            'summary_verdict': compliance_response.summary_verdict,
            'cited_clauses': [c.model_dump() for c in compliance_response.cited_clauses],
            'mandatory_requirements': compliance_response.mandatory_requirements,
            'inspection_checks': compliance_response.inspection_checks,
            'confidence_score': compliance_response.confidence_score,
            'inspection_context': compliance_query.inspection_context,
            'retrieved_chunks_count': compliance_response.retrieved_chunks_count or 0,
            'latency_ms': compliance_response.latency_ms or 0.0,
            'model_used': compliance_response.model_used or provider,
            'created_at': compliance_query.created_at,
        }

        resp_serializer = ComplianceQueryResponseSerializer(output_data)
        return Response(resp_serializer.data, status=status.HTTP_200_OK)


class ComplianceStandardsListView(APIView):
    """
    GET /api/v1/compliance/standards/
    Lists all ingested engineering and statutory standards, total indexed clauses, and versions.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsFieldEngineerOrReadOnly]

    def get(self, request):
        standards = ComplianceStandard.objects.all().prefetch_related('documents')
        standards_list = []

        for std in standards:
            docs = std.documents.all()
            total_clauses = sum(d.total_chunks for d in docs)
            standards_list.append({
                'code': std.code,
                'name': std.name,
                'authority': std.authority,
                'version': std.version or "Current Statutory Issue",
                'clause_count': total_clauses,
                'document_count': docs.count(),
                'is_active': std.is_active,
                'description': std.description or f"Official regulatory specification for {std.name}",
            })

        # If DB has no standards, query vector store collection to ensure real-time status
        if not standards_list:
            try:
                engine = get_compliance_engine()
                total_in_chroma = engine.vector_store.count()
                standards_list.append({
                    'code': 'EAWR-1989',
                    'name': 'Electricity at Work Regulations 1989',
                    'authority': 'HSE / UK Statutory',
                    'version': 'S.I. 1989 No. 635',
                    'clause_count': total_in_chroma,
                    'document_count': 1,
                    'is_active': True,
                    'description': 'Primary UK statutory instrument governing electrical safety at work.',
                })
            except Exception as e:
                logger.warning(f"Chroma fallback lookup warning: {e}")

        serializer = ComplianceStandardListSerializer(standards_list, many=True)
        return Response({
            'total_standards': len(standards_list),
            'standards': serializer.data
        }, status=status.HTTP_200_OK)


class ComplianceAuditFeedbackView(APIView):
    """
    POST /api/v1/compliance/audit/{id}/feedback/
    Allows field engineers and surveyors to submit accuracy feedback (approved / flagged / rejected).
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [CanSubmitAuditFeedback]

    def post(self, request, id):
        try:
            audit_log = ComplianceAuditLog.objects.select_related('query').get(id=id)
        except ComplianceAuditLog.DoesNotExist:
            raise NotFound(detail=f"ComplianceAuditLog with ID {id} does not exist.")

        serializer = ComplianceFeedbackRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback_val = serializer.validated_data['feedback']
        notes = serializer.validated_data.get('notes', '')

        # Update audit log with field engineer review
        audit_log.user_feedback = feedback_val
        audit_log.feedback_notes = notes
        if request.user and request.user.is_authenticated:
            audit_log.feedback_by = request.user
        audit_log.feedback_at = timezone.now()
        audit_log.save()

        return Response({
            'status': 'success',
            'message': f"Accuracy feedback successfully recorded as '{feedback_val}'.",
            'audit_id': audit_log.id,
            'query_id': audit_log.query_id,
            'user_feedback': audit_log.user_feedback,
            'feedback_notes': audit_log.feedback_notes,
            'feedback_by': audit_log.feedback_by.username if audit_log.feedback_by else 'Anonymous Field Engineer',
            'feedback_at': audit_log.feedback_at.isoformat() if audit_log.feedback_at else None,
        }, status=status.HTTP_200_OK)


class ComplianceAuditLogsListView(APIView):
    """
    GET /api/v1/compliance/audit/
    Retrieves historical compliance verification audits and engineer feedback logs.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsFieldEngineerOrReadOnly]

    def get(self, request):
        logs = ComplianceAuditLog.objects.select_related('query', 'feedback_by').all().order_by('-created_at')[:50]
        serializer = ComplianceAuditLogSerializer(logs, many=True)
        return Response({
            'count': len(serializer.data),
            'logs': serializer.data
        }, status=status.HTTP_200_OK)


class ComplianceAuditLogDetailView(APIView):
    """
    GET /api/v1/compliance/audit/{id}/
    Retrieve specific audit trail by ID.
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsFieldEngineerOrReadOnly]

    def get(self, request, id):
        try:
            audit_log = ComplianceAuditLog.objects.select_related('query', 'feedback_by').get(id=id)
        except ComplianceAuditLog.DoesNotExist:
            raise NotFound(detail=f"ComplianceAuditLog with ID {id} does not exist.")

        serializer = ComplianceAuditLogSerializer(audit_log)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ObtainComplianceTokenView(ObtainAuthToken):
    """
    POST /api/v1/compliance/auth/token/
    Obtains DRF API token for mobile surveyor apps and field engineer CLI tools.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)
        tier = get_user_permission_tier(user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'permission_tier': tier
        }, status=status.HTTP_200_OK)
