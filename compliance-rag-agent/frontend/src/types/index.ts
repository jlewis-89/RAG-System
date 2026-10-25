/**
 * TypeScript Interfaces for Engineering Compliance System.
 * Synchronized with backend Pydantic & DRF schemas.
 */

export type ComplianceStatus =
  | 'COMPLIANT'
  | 'POTENTIALLY_DANGEROUS' // Code C2
  | 'IMMEDIATE_DANGER' // Code C1
  | 'IMPROVEMENT_RECOMMENDED' // Code C3
  | 'INSUFFICIENT_DATA_FURTHER_INVESTIGATION'; // Code FI

export type InspectionContext =
  | 'Domestic'
  | 'Commercial'
  | 'Industrial'
  | 'Agricultural'
  | 'Special Installation'
  | 'General';

export type UserFeedback = 'pending' | 'approved' | 'flagged' | 'rejected';

export interface CitedClause {
  standard: string;
  clause_number: string;
  verbatim_quote: string;
}

export interface CitationItem {
  chunk_id?: string;
  standard_code?: string;
  clause?: string;
  source?: string;
  snippet?: string;
  relevance_score?: number;
  standard?: string;
  clause_number?: string;
  verbatim_quote?: string;
}


export interface ComplianceQueryRequest {
  query: string;
  inspection_context?: InspectionContext;
  standard_filter?: string;
  duty_filter?: string;
  top_k?: number;
  provider?: 'ollama' | 'groq' | 'anthropic' | 'deterministic' | 'auto';
  model?: string;
  stream?: boolean;
}

export interface ComplianceQueryResponse {
  query_id: number;
  audit_id: number;
  compliance_status: ComplianceStatus;
  summary_verdict: string;
  cited_clauses: CitedClause[];
  mandatory_requirements: string[];
  inspection_checks: string[];
  confidence_score: number;
  inspection_context: string;
  retrieved_chunks_count: number;
  latency_ms: number;
  model_used?: string;
  created_at: string;
}

export interface ComplianceStandardItem {
  code: string;
  name: string;
  authority: string;
  version?: string | null;
  clause_count: number;
  document_count: number;
  is_active: boolean;
  description?: string;
}

export interface ComplianceStandardsResponse {
  total_standards: number;
  standards: ComplianceStandardItem[];
}

export interface ComplianceAuditFeedbackPayload {
  feedback: UserFeedback;
  notes?: string;
}

export interface ComplianceAuditFeedbackResponse {
  status: string;
  message: string;
  audit_id: number;
  query_id: number;
  user_feedback: UserFeedback;
  feedback_notes: string;
  feedback_by: string;
  feedback_at: string | null;
}

export interface ComplianceAuditLogItem {
  id: number;
  query_id: number;
  query_text: string;
  inspection_context: string;
  full_input: Record<string, any>;
  retrieved_context_ids: string[];
  generated_response: Record<string, any>;
  response_time_ms: number;
  user_feedback: UserFeedback;
  feedback_notes: string;
  feedback_by_username?: string | null;
  feedback_at?: string | null;
  model_used?: string;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  chroma_status: string;
  chroma_collection: string;
  chroma_items_count: number;
  database_status: string;
  version: string;
}

export interface DocumentIngestPayload {
  title: string;
  standard_code: string;
  content: string;
  source_identifier?: string;
  metadata?: Record<string, any>;
}
