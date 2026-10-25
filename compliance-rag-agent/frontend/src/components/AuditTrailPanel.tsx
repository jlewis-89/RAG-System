import React, { useEffect, useState } from 'react';
import { X, History, Clock, FileCode, RefreshCw } from 'lucide-react';
import { ComplianceAuditLog } from '../types';
import { ComplianceBadge } from './ComplianceBadge';
import api from '../services/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSelectAudit?: (log: ComplianceAuditLog) => void;
}

export const AuditTrailPanel: React.FC<Props> = ({ isOpen, onClose, onSelectAudit }) => {
  const [logs, setLogs] = useState<ComplianceAuditLog[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditLogs();
      setLogs(data);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchLogs();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/70 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-xl h-full glass-panel border-l border-slate-800 shadow-2xl flex flex-col">
        
        {/* Header */}
        <div className="p-4 sm:p-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Compliance Audit Trail</h2>
              <p className="text-xs text-slate-400">Chronological verification logs & citations</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchLogs}
              title="Refresh logs"
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {loading && logs.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              Loading audit logs...
            </div>
          ) : logs.length === 0 ? (
            <div className="py-16 text-center text-slate-400">
              <FileCode className="w-8 h-8 mx-auto text-slate-600 mb-2" />
              <p className="text-sm font-medium">No audit entries yet</p>
              <p className="text-xs text-slate-500 mt-1">
                Run an engineering compliance query to generate audit trails.
              </p>
            </div>
          ) : (
            logs.map((log) => (
              <div
                key={log.id}
                onClick={() => onSelectAudit && onSelectAudit(log)}
                className="glass-card rounded-xl p-4 transition hover:border-emerald-500/30 hover:bg-slate-800/50 cursor-pointer"
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <ComplianceBadge verdict={log.verdict} />
                  <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {log.latency_ms}ms
                    </span>
                    <span>•</span>
                    <span className="text-emerald-400 font-semibold">
                      {Math.round(log.confidence_score * 100)}% conf
                    </span>
                  </div>
                </div>

                <p className="text-xs font-semibold text-slate-200 line-clamp-2 mb-2 font-mono">
                  "{log.query_text}"
                </p>

                <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                  {log.answer_text}
                </p>

                <div className="flex items-center justify-between text-[11px] text-slate-500 border-t border-slate-800/80 pt-2 font-mono">
                  <span>Standard: {log.standard_filter || 'ALL'}</span>
                  <span>{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </div>
            ))
          )}
        </div>

      </div>
    </div>
  );
};
