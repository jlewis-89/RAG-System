import React from 'react';
import { HealthStatus } from '../types';
import { ShieldCheck, Database, RefreshCw, Upload, History, Sparkles } from 'lucide-react';

interface Props {
  health: HealthStatus | null;
  loadingHealth: boolean;
  onRefreshHealth: () => void;
  onOpenIngest: () => void;
  onOpenAudit: () => void;
  onSeedData: () => void;
  isSeeding: boolean;
}

export const Header: React.FC<Props> = ({
  health,
  loadingHealth,
  onRefreshHealth,
  onOpenIngest,
  onOpenAudit,
  onSeedData,
  isSeeding,
}) => {
  const isHealthy = health?.status === 'healthy';

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        
        {/* Brand / Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center shadow-lg shadow-emerald-500/20 border border-emerald-400/30">
            <ShieldCheck className="w-6 h-6 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-white">
                Compliance<span className="text-emerald-400">RAG</span>
              </h1>
              <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono uppercase tracking-wider rounded bg-slate-800 text-slate-300 border border-slate-700">
                v1.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Engineering Regulatory Standard Verification
            </p>
          </div>
        </div>

        {/* System Diagnostics & Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* ChromaDB Vector Count Pill */}
          <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
            <Database className="w-3.5 h-3.5 text-teal-400" />
            <span>Chroma:</span>
            <span className="font-semibold text-emerald-400">
              {health?.chroma_items_count ?? 0} chunks
            </span>
          </div>

          {/* Backend Health Indicator */}
          <button
            onClick={onRefreshHealth}
            title="Click to re-check API & ChromaDB status"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs transition hover:bg-slate-850"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                loadingHealth
                  ? 'bg-amber-400 animate-ping'
                  : isHealthy
                  ? 'bg-emerald-400 shadow-sm shadow-emerald-400'
                  : 'bg-rose-500'
              }`}
            />
            <span className="text-slate-300 font-mono text-[11px] hidden sm:inline">
              {loadingHealth ? 'Checking...' : isHealthy ? 'API Active' : 'Offline'}
            </span>
            <RefreshCw className={`w-3 h-3 text-slate-400 ${loadingHealth ? 'animate-spin' : ''}`} />
          </button>

          {/* Seed Initial Standards Demo */}
          <button
            onClick={onSeedData}
            disabled={isSeeding}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-emerald-300 bg-emerald-950/40 hover:bg-emerald-900/50 border border-emerald-700/40 transition disabled:opacity-50"
            title="Seed ISO 9001, ASME Section VIII & IEC 61508 standards"
          >
            <Sparkles className={`w-3.5 h-3.5 ${isSeeding ? 'animate-spin' : 'text-emerald-400'}`} />
            <span className="hidden sm:inline">{isSeeding ? 'Seeding...' : 'Seed Standards'}</span>
          </button>

          {/* Ingest Document Modal Trigger */}
          <button
            onClick={onOpenIngest}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
          >
            <Upload className="w-3.5 h-3.5 text-slate-300" />
            <span className="hidden sm:inline">Ingest</span>
          </button>

          {/* Audit History Trigger */}
          <button
            onClick={onOpenAudit}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition"
          >
            <History className="w-3.5 h-3.5 text-slate-300" />
            <span className="hidden sm:inline">Audit Trail</span>
          </button>
        </div>

      </div>
    </header>
  );
};
