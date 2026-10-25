export type ComplianceVerdict = 'COMPLIANT' | 'NON_COMPLIANT' | 'PARTIALLY_COMPLIANT' | 'NEEDS_REVIEW';

export interface CitationItem {
  chunk_id: string;
  standard_code: string;
  clause: string;
  source: string;
  snippet: string;
  relevance_score: number;
}

export interface RAGQueryRequest {
  query: string;
  standard_codes?: string[];
  top_k?: number;
  strict_mode?: boolean;
}

export interface RAGQueryResponse {
  query: string;
  verdict: ComplianceVerdict;
  confidence_score: number;
  summary: string;
  detailed_findings: string;
  citations: CitationItem[];
  audit_id?: number;
  latency_ms: number;
  timestamp: string;
}

export interface ComplianceStandard {
  id: number;
  code: string;
  name: string;
  authority: string;
  version?: string;
  description?: string;
  is_active: boolean;
  documents_count: number;
  created_at: string;
}

export interface ComplianceAuditLog {
  id: number;
  query_text: string;
  verdict: ComplianceVerdict;
  confidence_score: number;
  answer_text: string;
  citations: CitationItem[];
  standard_filter?: string;
  latency_ms: number;
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
