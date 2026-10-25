import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Search,
  BookOpen,
  Cpu,
  Zap,
  ArrowRight
} from 'lucide-react';
import { Header } from './components/Header';
import { ComplianceBadge } from './components/ComplianceBadge';
import { CitationCard } from './components/CitationCard';
import { DocumentIngestModal } from './components/DocumentIngestModal';
import { AuditTrailPanel } from './components/AuditTrailPanel';
import api from './services/api';
import { HealthStatus, RAGQueryResponse, ComplianceStandard } from './types';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(false);
  const [standards, setStandards] = useState<ComplianceStandard[]>([]);
  const [selectedStandard, setSelectedStandard] = useState<string>('ALL');

  const [query, setQuery] = useState('');
  const [loadingQuery, setLoadingQuery] = useState(false);
  const [result, setResult] = useState<RAGQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [isIngestOpen, setIsIngestOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);

  // Fetch initial health and standards
  const fetchHealthAndStandards = async () => {
    try {
      setLoadingHealth(true);
      const healthData = await api.getHealth();
      setHealth(healthData);

      const stds = await api.getStandards();
      setStandards(stds);
    } catch (err: any) {
      console.warn('Backend not responding yet:', err.message);
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    fetchHealthAndStandards();
  }, []);

  const handleSeedData = async () => {
    try {
      setIsSeeding(true);
      await api.seedStandards();
      await fetchHealthAndStandards();
    } catch (err: any) {
      setError(err.response?.data?.error || err.message || 'Failed to seed standards.');
    } finally {
      setIsSeeding(false);
    }
  };

  const handleExecuteQuery = async (customQuery?: string) => {
    const q = customQuery || query;
    if (!q || q.trim().length < 3) return;

    try {
      setLoadingQuery(true);
      setError(null);
      setResult(null);

      const standardCodes = selectedStandard === 'ALL' ? undefined : [selectedStandard];
      const res = await api.queryCompliance({
        query: q.trim(),
        standard_codes: standardCodes,
        top_k: 4,
        strict_mode: true,
      });
      setResult(res);
      // Refresh health to update chunk counts if needed
      api.getHealth().then(setHealth).catch(() => {});
    } catch (err: any) {
      console.error('Compliance Query Error:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to complete compliance audit.');
    } finally {
      setLoadingQuery(false);
    }
  };

  const sampleQueries = [
    {
      title: "EAWR Reg 4(2) System Maintenance",
      prompt: "What does Regulation 4(2) require regarding the maintenance of electrical systems?",
      standard: "EAWR-1989",
    },
    {
      title: "BPG4 Consumer Unit Classification",
      prompt: "What classification code is assigned to a missing blanking piece on a consumer unit?",
      standard: "ESF-BPG4",
    },
    {
      title: "EAWR Reg 16 Competence & Supervision",
      prompt: "What are the requirements for persons undertaking electrical work under Regulation 16?",
      standard: "EAWR-1989",
    },
    {
      title: "PUWER Reg 4 Suitability of Equipment",
      prompt: "What duty is imposed on employers concerning the suitability of work equipment under Regulation 4?",
      standard: "PUWER-1998",
    }
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Top Navbar */}
      <Header
        health={health}
        loadingHealth={loadingHealth}
        onRefreshHealth={fetchHealthAndStandards}
        onOpenIngest={() => setIsIngestOpen(true)}
        onOpenAudit={() => setIsAuditOpen(true)}
        onSeedData={handleSeedData}
        isSeeding={isSeeding}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">
        
        {/* Banner / Introduction */}
        <section className="relative overflow-hidden rounded-2xl glass-panel p-6 sm:p-8 border border-slate-800">
          <div className="absolute top-0 right-0 -mt-12 -mr-12 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/3 -mb-12 w-64 h-64 bg-teal-500/10 rounded-full blur-2xl pointer-events-none" />

          <div className="relative z-10 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-4">
              <Zap className="w-3.5 h-3.5" />
              ChromaDB Vector Retrieval • Pydantic v2 • LangChain Orchestration
            </div>
            <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
              Autonomous Engineering Compliance Verification
            </h2>
            <p className="mt-2 text-sm sm:text-base text-slate-300 leading-relaxed">
              Query statutory UK electrical and safety regulations (EAWR 1989, HSE HSR25, ESF BPG4, PUWER 1998, HASAWA 1974).
              Retrieve exact clause citations with definitive compliance verdicts, duty holder classifications, and audit trails.
            </p>
          </div>
        </section>

        {/* Query Input Box */}
        <section className="glass-panel rounded-2xl p-4 sm:p-6 border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5 font-mono">
              <Search className="w-4 h-4 text-emerald-400" />
              Compliance Specification Audit Query
            </label>

            {/* Standard Selector Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400 font-medium">Standard Filter:</span>
              <select
                value={selectedStandard}
                onChange={(e) => setSelectedStandard(e.target.value)}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
              >
                <option value="ALL">ALL Indexed Standards</option>
                {standards && standards.length > 0 ? (
                  standards.map((s) => (
                    <option key={s.id} value={s.code}>
                      {s.name} ({s.code})
                    </option>
                  ))
                ) : (
                  <>
                    <option value="EAWR-1989">EAWR 1989 (Electricity at Work)</option>
                    <option value="HSE-HSR25">HSE HSR25 Guidance</option>
                    <option value="ESF-BPG4">Electrical Safety First BPG4</option>
                    <option value="PUWER-1998">PUWER 1998</option>
                    <option value="HASAWA-1974">HASAWA 1974</option>
                  </>
                )}
              </select>
            </div>
          </div>

          <div className="relative">
            <textarea
              rows={3}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter engineering parameter, design clause, or safety requirement to audit (e.g., 'Verify relief valve testing intervals per ASME Section VIII')..."
              className="w-full px-4 py-3 rounded-xl bg-slate-900/90 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-sans resize-none transition"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                  handleExecuteQuery();
                }
              }}
            />
            
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/80">
              <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
                Press Ctrl+Enter or Cmd+Enter to execute audit
              </span>
              <button
                onClick={() => handleExecuteQuery()}
                disabled={loadingQuery || !query.trim()}
                className="ml-auto flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition shadow-lg shadow-emerald-500/20 disabled:opacity-50"
              >
                <Cpu className={`w-4 h-4 ${loadingQuery ? 'animate-spin' : ''}`} />
                <span>{loadingQuery ? 'Auditing Standard Clauses...' : 'Verify Compliance'}</span>
              </button>
            </div>
          </div>

          {/* Preset Sample Prompts */}
          <div className="pt-2">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2 font-mono">
              Quick Audit Scenarios
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
              {sampleQueries.map((item, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setQuery(item.prompt);
                    setSelectedStandard(item.standard);
                    handleExecuteQuery(item.prompt);
                  }}
                  className="text-left p-2.5 rounded-xl bg-slate-900/70 hover:bg-slate-800/90 border border-slate-800 hover:border-emerald-500/40 transition group"
                >
                  <div className="flex items-center justify-between text-[11px] font-mono text-emerald-400 mb-1 font-semibold">
                    <span>{item.standard}</span>
                    <ArrowRight className="w-3 h-3 text-slate-500 group-hover:text-emerald-400 transition transform group-hover:translate-x-0.5" />
                  </div>
                  <p className="text-xs text-slate-300 font-medium line-clamp-2">
                    {item.title}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Error Alert */}
        {error && (
          <div className="glass-card rounded-xl p-4 border border-rose-500/40 bg-rose-950/20 text-rose-300 text-xs flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-rose-400 flex-shrink-0" />
            <div>
              <p className="font-semibold">Audit Execution Issue</p>
              <p className="text-slate-400 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Audit Results View */}
        {result && (
          <section className="space-y-6 animate-fadeIn">
            {/* Verdict Header Card */}
            <div className="glass-panel rounded-2xl p-6 border border-slate-800">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div className="space-y-1">
                  <div className="flex items-center gap-3">
                    <ComplianceBadge verdict={result.verdict} className="text-sm px-4 py-1.5" />
                    <span className="text-xs font-mono text-slate-400">
                      Audit #{result.audit_id || 'LOCAL'}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white mt-1">
                    Compliance Audit Findings
                  </h3>
                </div>

                <div className="flex items-center gap-4 text-xs font-mono">
                  <div className="text-right">
                    <span className="text-slate-400 block text-[10px]">CONFIDENCE</span>
                    <span className="text-emerald-400 font-bold text-sm">
                      {Math.round(result.confidence_score * 100)}%
                    </span>
                  </div>
                  <div className="h-8 w-px bg-slate-800" />
                  <div className="text-right">
                    <span className="text-slate-400 block text-[10px]">LATENCY</span>
                    <span className="text-slate-200 font-semibold text-sm">
                      {result.latency_ms} ms
                    </span>
                  </div>
                </div>
              </div>

              {/* Summary and Findings */}
              <div className="mt-4 space-y-3">
                <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800">
                  <p className="text-xs font-semibold text-emerald-400 font-mono uppercase mb-1">
                    Executive Determination
                  </p>
                  <p className="text-sm text-slate-200 font-medium">
                    {result.summary}
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800/60">
                  <p className="text-xs font-semibold text-slate-400 font-mono uppercase mb-1">
                    Regulatory Analysis & Parameters
                  </p>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">
                    {result.detailed_findings}
                  </p>
                </div>
              </div>
            </div>

            {/* Citations Grid */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-emerald-400" />
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-mono">
                    Retrieved Standard Clauses ({result.citations.length})
                  </h4>
                </div>
                <span className="text-[11px] text-slate-400 font-mono">
                  Source: ChromaDB Persistent Storage
                </span>
              </div>

              {result.citations.length === 0 ? (
                <div className="glass-card rounded-xl p-6 text-center text-xs text-slate-500">
                  No explicit clauses found with sufficient similarity in ChromaDB.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {result.citations.map((citation, index) => (
                    <CitationCard key={citation.chunk_id} citation={citation} index={index} />
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-4 glass-panel text-center text-xs text-slate-400 font-mono">
        <p>Engineering Compliance RAG System • Django 5.x REST Framework • ChromaDB Volume</p>
      </footer>

      {/* Ingest Document Modal */}
      <DocumentIngestModal
        isOpen={isIngestOpen}
        onClose={() => setIsIngestOpen(false)}
        onSuccess={() => {
          fetchHealthAndStandards();
        }}
      />

      {/* Audit Trail Drawer */}
      <AuditTrailPanel
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
        onSelectAudit={(log) => {
          setQuery(log.query_text);
          setIsAuditOpen(false);
          handleExecuteQuery(log.query_text);
        }}
      />
    </div>
  );
};

export default App;
