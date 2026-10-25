import axios from 'axios';
import {
  HealthStatus,
  RAGQueryRequest,
  RAGQueryResponse,
  ComplianceStandard,
  ComplianceAuditLog,
  DocumentIngestPayload
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 45000,
});

export const api = {
  // Health & Diagnostics
  getHealth: async (): Promise<HealthStatus> => {
    const response = await apiClient.get<HealthStatus>('/rag/health/');
    return response.data;
  },

  // RAG Query
  queryCompliance: async (payload: RAGQueryRequest): Promise<RAGQueryResponse> => {
    const response = await apiClient.post<RAGQueryResponse>('/rag/query/', payload);
    return response.data;
  },

  // Document Ingestion
  ingestDocument: async (payload: DocumentIngestPayload) => {
    const response = await apiClient.post('/rag/ingest/', payload);
    return response.data;
  },

  // Seed sample standards
  seedStandards: async () => {
    const response = await apiClient.post('/rag/seed/');
    return response.data;
  },

  // Standards Registry
  getStandards: async (): Promise<ComplianceStandard[]> => {
    const response = await apiClient.get<ComplianceStandard[]>('/rag/standards/');
    return response.data;
  },

  // Regulatory Audit Logs
  getAuditLogs: async (): Promise<ComplianceAuditLog[]> => {
    const response = await apiClient.get<ComplianceAuditLog[]>('/rag/audit-logs/');
    return response.data;
  },
};

export default api;
