import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Search,
  Cpu,
  Zap,
  Filter,
} from 'lucide-react';
import { Header } from './components/Header';
import { TrafficLightBanner } from './components/TrafficLightBanner';
import { EvidenceAccordions } from './components/EvidenceAccordions';
import { SurveyorActionPanel } from './components/SurveyorActionPanel';
import { QuickTagsBar } from './components/QuickTagsBar';
import { OfflineIndicator } from './components/OfflineIndicator';
import { DocumentIngestModal } from './components/DocumentIngestModal';
import { AuditTrailPanel } from './components/AuditTrailPanel';
import api from './services/api';
import {
  HealthStatus,
  ComplianceQueryResponse,
  ComplianceStandardItem,
  InspectionContext,
} from './types';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(false);
  const [standards, setStandards] = useState<ComplianceStandardItem[]>([]);
  const [selectedStandard, setSelectedStandard] = useState<string>('ALL');
  const [inspectionContext, setInspectionContext] = useState<InspectionContext>('Domestic');

  const [query, setQuery] = useState('');
  const [loadingQuery, setLoadingQuery] = useState(false);
  const [result, setResult] = useState<ComplianceQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [isIngestOpen, setIsIngestOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);

  // Fetch initial health and standards
  const fetchHealthAndStandards = async () => {
    try {
      setLoadingHealth(true);
      const healthData = await api.getHealth().catch(() => null);
      if (healthData) setHealth(healthData);

      const stdsData = await api.getStandards();
      setStandards(stdsData.standards || []);
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

  const handleExecuteQuery = async (customQuery?: string, customContext?: InspectionContext) => {
    const q = customQuery || query;
    const ctx = customContext || inspectionContext;
    if (!q || q.trim().length < 3) return;

    try {
      setLoadingQuery(true);
      setError(null);
      setResult(null);

      const res = await api.queryCompliance({
        query: q.trim(),
        inspection_context: ctx,
        standard_filter: selectedStandard === 'ALL' ? undefined : selectedStandard,
        top_k: 4,
        provider: 'auto',
      });
      setResult(res);
      api.getHealth().then(setHealth).catch(() => {});
    } catch (err: any) {
      console.error('Compliance Query Error:', err);
      const errDetail =
        err.response?.data?.message ||
        err.response?.data?.detail ||
        err.message ||
        'Failed to complete compliance audit.';
      setError(errDetail);
    } finally {
      setLoadingQuery(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 selection:bg-emerald-500/30 selection:text-emerald-300">
      {/* Offline Mode Alert & PWA Home Screen Banner */}
      <OfflineIndicator />

      {/* Top Mobile-First Navbar */}
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
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-5 sm:py-8 space-y-6">
        
        {/* Mobile Header Banner */}
        <section className="relative overflow-hidden rounded-2xl glass-panel p-5 sm:p-7 border border-slate-800">
          <div className="absolute top-0 right-0 -mt-12 -mr-12 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-1/3 -mb-12 w-64 h-64 bg-teal-500/10 rounded-full blur-2xl pointer-events-none" />

          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 mb-3">
              <Zap className="w-3.5 h-3.5 text-emerald-400" />
              <span>UK Electrical Standards Reasoner • Mobile Field Tool</span>
            </div>
            <h1 className="text-xl sm:text-2xl lg:text-3xl font-extrabold tracking-tight text-white leading-tight">
              Statutory Engineering Compliance Auditor
            </h1>
            <p className="mt-2 text-xs sm:text-sm text-slate-300 max-w-3xl leading-relaxed">
              Show the engineer why the answer was reached, not just the answer.
              Audits technical observations against EAWR 1989, HSE HSR25, and ESF BPG4 with zero hallucination.
            </p>
          </div>
        </section>

        {/* Query Input Section */}
        <section className="glass-panel rounded-2xl p-4 sm:p-6 border border-slate-800 space-y-4 shadow-xl">
          {/* Context Selector & Quick Tags */}
          <QuickTagsBar
            selectedContext={inspectionContext}
            onSelectContext={(ctx) => setInspectionContext(ctx)}
            onSelectTag={(tagQuery, defaultContext) => {
              setQuery(tagQuery);
              if (defaultContext) setInspectionContext(defaultContext);
              handleExecuteQuery(tagQuery, defaultContext);
            }}
          />

          {/* Search Box & Controls */}
          <div className="pt-2 border-t border-slate-800/80 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 font-mono">
                <Search className="w-4 h-4 text-emerald-400" />
                <span>Surveyor Query / Observation Input:</span>
              </label>

              {/* Standard Filter Dropdown */}
              <div className="flex items-center gap-2">
                <Filter className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-xs text-slate-400">Standard:</span>
                <select
                  value={selectedStandard}
                  onChange={(e) => setSelectedStandard(e.target.value)}
                  className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
                >
                  <option value="ALL">All Standards</option>
                  {standards && standards.length > 0 ? (
                    standards.map((s) => (
                      <option key={s.code} value={s.code}>
                        {s.code} ({s.clause_count} cls)
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="EAWR-1989">EAWR 1989</option>
                      <option value="ESF-BPG4">ESF BPG4</option>
                      <option value="HSE-HSR25">HSR25 Guidance</option>
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
                placeholder="Enter engineering defect, inspection condition, or regulation query (e.g., 'A circuit protective device is missing from a consumer unit with accessible live parts')..."
                className="w-full px-4 py-3 rounded-xl bg-slate-900/90 border border-slate-700 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-sans resize-none transition"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    handleExecuteQuery();
                  }
                }}
              />

              <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/80">
                <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
                  Tip: Press Ctrl+Enter to execute reasoning
                </span>

                <button
                  onClick={() => handleExecuteQuery()}
                  disabled={loadingQuery || !query.trim()}
                  className="ml-auto w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition shadow-lg shadow-emerald-500/20 disabled:opacity-50 active:scale-95"
                >
                  <Cpu className={`w-4 h-4 ${loadingQuery ? 'animate-spin' : ''}`} />
                  <span>{loadingQuery ? 'Reasoning Against Standards...' : 'Verify Statutory Compliance'}</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Error Alert */}
        {error && (
          <div className="rounded-xl p-4 border border-rose-500/40 bg-rose-950/20 text-rose-300 text-xs flex items-center gap-3 animate-fadeIn">
            <ShieldAlert className="w-5 h-5 text-rose-400 flex-shrink-0" />
            <div>
              <p className="font-semibold">Compliance Audit Error</p>
              <p className="text-slate-400 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Results View */}
        {result && (
          <section className="space-y-6 animate-fadeIn">
            {/* 1. Traffic-Light Verdict Banner */}
            <TrafficLightBanner
              status={result.compliance_status}
              summaryVerdict={result.summary_verdict}
              confidenceScore={result.confidence_score}
              inspectionContext={result.inspection_context}
              latencyMs={result.latency_ms}
              auditId={result.audit_id}
              modelUsed={result.model_used}
            />

            {/* 2. Surveyor Action & EICR Copy Panel */}
            <SurveyorActionPanel
              response={result}
              onFeedbackSubmitted={() => {
                // Refresh if needed
              }}
            />

            {/* 3. Evidence & Audit Accordions */}
            <EvidenceAccordions
              mandatoryRequirements={result.mandatory_requirements}
              inspectionChecks={result.inspection_checks}
              citedClauses={result.cited_clauses}
            />
          </section>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-4 glass-panel text-center text-xs text-slate-400 font-mono mt-auto">
        <p>UK Statutory Electrical Standards Compliance Engine • EAWR 1989 • ESF BPG4 • BS 7671</p>
      </footer>

      {/* Ingest Document Modal */}
      <DocumentIngestModal
        isOpen={isIngestOpen}
        onClose={() => setIsIngestOpen(false)}
        onSuccess={() => fetchHealthAndStandards()}
      />

      {/* Audit Trail Drawer */}
      <AuditTrailPanel
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
        onSelectAudit={(queryText, context) => {
          setQuery(queryText);
          if (context) setInspectionContext(context as InspectionContext);
          setIsAuditOpen(false);
          handleExecuteQuery(queryText, context as InspectionContext);
        }}
      />
    </div>
  );
};

export default App;
