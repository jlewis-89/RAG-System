import axios from 'axios';
import {
  HealthStatus,
  ComplianceQueryRequest,
  ComplianceQueryResponse,
  ComplianceStandardsResponse,
  ComplianceAuditFeedbackPayload,
  ComplianceAuditFeedbackResponse,
  ComplianceAuditLogItem,
  DocumentIngestPayload,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

export const api = {
  // Primary v1 Compliance Query Endpoint
  queryCompliance: async (payload: ComplianceQueryRequest): Promise<ComplianceQueryResponse> => {
    try {
      const response = await apiClient.post<ComplianceQueryResponse>('/v1/compliance/query/', payload);
      return response.data;
    } catch (err: any) {
      // Graceful fallback to legacy endpoint if v1 route not reached
      if (err.response?.status === 404) {
        const legacyResp = await apiClient.post('/rag/query/', {
          query: payload.query,
          top_k: payload.top_k,
          standard_codes: payload.standard_filter ? [payload.standard_filter] : undefined,
        });
        const d = legacyResp.data;
        return {
          query_id: d.audit_id || 0,
          audit_id: d.audit_id || 0,
          compliance_status: d.verdict === 'COMPLIANT' ? 'COMPLIANT' : 'POTENTIALLY_DANGEROUS',
          summary_verdict: d.summary || '',
          cited_clauses: (d.citations || []).map((c: any) => ({
            standard: c.standard_code,
            clause_number: c.clause,
            verbatim_quote: c.snippet,
          })),
          mandatory_requirements: [d.detailed_findings || 'Mandatory compliance inspection required.'],
          inspection_checks: ['Verify physical installation against cited standard.'],
          confidence_score: d.confidence_score || 0.8,
          inspection_context: payload.inspection_context || 'Domestic',
          retrieved_chunks_count: d.citations?.length || 0,
          latency_ms: d.latency_ms || 100,
          model_used: 'legacy-rag',
          created_at: new Date().toISOString(),
        };
      }
      throw err;
    }
  },

  // Ingested Standards & Clause Counts Registry
  getStandards: async (): Promise<ComplianceStandardsResponse> => {
    try {
      const response = await apiClient.get<ComplianceStandardsResponse>('/v1/compliance/standards/');
      return response.data;
    } catch (err: any) {
      // Fallback to legacy endpoint
      const legacyResp = await apiClient.get('/rag/standards/');
      const items = Array.isArray(legacyResp.data) ? legacyResp.data : [];
      return {
        total_standards: items.length,
        standards: items.map((s: any) => ({
          code: s.code,
          name: s.name,
          authority: s.authority,
          version: s.version,
          clause_count: s.documents_count || 10,
          document_count: 1,
          is_active: s.is_active ?? true,
          description: s.description,
        })),
      };
    }
  },

  // Submit Field Engineer Accuracy Feedback
  submitFeedback: async (
    auditId: number,
    payload: ComplianceAuditFeedbackPayload
  ): Promise<ComplianceAuditFeedbackResponse> => {
    const response = await apiClient.post<ComplianceAuditFeedbackResponse>(
      `/v1/compliance/audit/${auditId}/feedback/`,
      payload
    );
    return response.data;
  },

  // Audit Logs History
  getAuditLogs: async (): Promise<{ count: number; logs: ComplianceAuditLogItem[] }> => {
    try {
      const response = await apiClient.get<{ count: number; logs: ComplianceAuditLogItem[] }>('/v1/compliance/audit/');
      return response.data;
    } catch (err: any) {
      const legacyResp = await apiClient.get('/rag/audit-logs/');
      const items = Array.isArray(legacyResp.data) ? legacyResp.data : [];
      return {
        count: items.length,
        logs: items.map((l: any) => ({
          id: l.id,
          query_id: l.id,
          query_text: l.query_text,
          inspection_context: 'General',
          full_input: { query: l.query_text },
          retrieved_context_ids: [],
          generated_response: {
            compliance_status: l.verdict,
            summary_verdict: l.answer_text,
            confidence_score: l.confidence_score,
          },
          response_time_ms: l.latency_ms,
          user_feedback: 'pending',
          feedback_notes: '',
          created_at: l.created_at,
        })),
      };
    }
  },

  // Health & Diagnostics
  getHealth: async (): Promise<HealthStatus> => {
    const response = await apiClient.get<HealthStatus>('/rag/health/');
    return response.data;
  },

  // Document Ingestion
  ingestDocument: async (payload: DocumentIngestPayload) => {
    const response = await apiClient.post('/rag/ingest/', payload);
    return response.data;
  },

  // Seed Initial Standards
  seedStandards: async () => {
    const response = await apiClient.post('/rag/seed/');
    return response.data;
  },
};

export default api;
