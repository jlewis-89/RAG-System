import React, { useState } from 'react';
import {
  ChevronDown,
  Scale,
  ClipboardCheck,
  BookOpen,
  Copy,
  Check,
  ShieldCheck,
  AlertCircle,
} from 'lucide-react';
import { CitedClause } from '../types';

interface EvidenceAccordionsProps {
  mandatoryRequirements: string[];
  inspectionChecks: string[];
  citedClauses: CitedClause[];
}

export const EvidenceAccordions: React.FC<EvidenceAccordionsProps> = ({
  mandatoryRequirements,
  inspectionChecks,
  citedClauses,
}) => {
  // Accordion open/close state
  const [openPanels, setOpenPanels] = useState<{
    duties: boolean;
    checks: boolean;
    citations: boolean;
  }>({
    duties: true,
    checks: true,
    citations: true,
  });

  // Interactive on-site check verification state (surveyor ticking off on mobile)
  const [verifiedChecks, setVerifiedChecks] = useState<Record<number, boolean>>({});
  const [copiedClauseIndex, setCopiedClauseIndex] = useState<number | null>(null);

  const togglePanel = (panel: 'duties' | 'checks' | 'citations') => {
    setOpenPanels((prev) => ({ ...prev, [panel]: !prev[panel] }));
  };

  const toggleCheck = (idx: number) => {
    setVerifiedChecks((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  const handleCopyQuote = (quote: string, idx: number) => {
    navigator.clipboard.writeText(quote);
    setCopiedClauseIndex(idx);
    setTimeout(() => setCopiedClauseIndex(null), 2000);
  };

  const totalChecks = inspectionChecks.length;
  const completedChecksCount = Object.values(verifiedChecks).filter(Boolean).length;

  return (
    <div className="space-y-4">
      {/* 1. Statutory Duty-Holder Requirements Accordion */}
      <div className="glass-panel rounded-2xl border border-slate-800/80 overflow-hidden transition-all duration-200">
        <button
          onClick={() => togglePanel('duties')}
          className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-slate-900/50 transition"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide">
                Statutory Duty-Holder Requirements
              </h3>
              <p className="text-xs text-slate-400">
                Absolute duties & statutory obligations under UK legislation ({mandatoryRequirements.length} rules)
              </p>
            </div>
          </div>
          <ChevronDown
            className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${
              openPanels.duties ? 'rotate-180' : ''
            }`}
          />
        </button>

        {openPanels.duties && (
          <div className="px-5 pb-5 pt-1 space-y-2.5 border-t border-slate-800/50">
            {mandatoryRequirements.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No explicit statutory duty obligations cited in retrieved context.
              </p>
            ) : (
              mandatoryRequirements.map((req, idx) => {
                const isAbsolute = req.toLowerCase().includes('absolute') || req.toLowerCase().includes('shall');
                return (
                  <div
                    key={idx}
                    className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 flex items-start gap-3 hover:border-slate-700 transition"
                  >
                    <span
                      className={`text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded-md mt-0.5 flex-shrink-0 ${
                        isAbsolute
                          ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                          : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                      }`}
                    >
                      {isAbsolute ? 'Absolute Duty' : 'Statutory Mandate'}
                    </span>
                    <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-sans">
                      {req}
                    </p>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* 2. Physical On-Site Checks Required Accordion */}
      <div className="glass-panel rounded-2xl border border-slate-800/80 overflow-hidden transition-all duration-200">
        <button
          onClick={() => togglePanel('checks')}
          className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-slate-900/50 transition"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <ClipboardCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white tracking-wide">
                  Physical On-Site Checks Required
                </h3>
                {totalChecks > 0 && (
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-emerald-400 font-semibold border border-slate-700">
                    {completedChecksCount}/{totalChecks} Verified
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                Actionable inspection steps the surveyor must physically verify on site
              </p>
            </div>
          </div>
          <ChevronDown
            className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${
              openPanels.checks ? 'rotate-180' : ''
            }`}
          />
        </button>

        {openPanels.checks && (
          <div className="px-5 pb-5 pt-1 space-y-2 border-t border-slate-800/50">
            {inspectionChecks.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No specific physical checks extracted for this scenario.
              </p>
            ) : (
              inspectionChecks.map((check, idx) => {
                const isChecked = !!verifiedChecks[idx];
                return (
                  <div
                    key={idx}
                    onClick={() => toggleCheck(idx)}
                    className={`p-3.5 rounded-xl border transition cursor-pointer select-none flex items-start gap-3 ${
                      isChecked
                        ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-200'
                        : 'bg-slate-900/70 border-slate-800 text-slate-200 hover:border-slate-700'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5 transition ${
                        isChecked
                          ? 'bg-emerald-500 text-slate-950'
                          : 'border border-slate-600 bg-slate-800/80 hover:border-emerald-400'
                      }`}
                    >
                      {isChecked && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>
                    <span
                      className={`text-xs sm:text-sm leading-relaxed ${
                        isChecked ? 'line-through text-slate-400' : 'text-slate-200'
                      }`}
                    >
                      {check}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* 3. Verbatim Cited Regulations Accordion */}
      <div className="glass-panel rounded-2xl border border-slate-800/80 overflow-hidden transition-all duration-200">
        <button
          onClick={() => togglePanel('citations')}
          className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-slate-900/50 transition"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-wide">
                Verbatim Cited Regulations & Standards
              </h3>
              <p className="text-xs text-slate-400">
                Unsevered statutory quotes grounded strictly in retrieved chunks ({citedClauses.length} citations)
              </p>
            </div>
          </div>
          <ChevronDown
            className={`w-5 h-5 text-slate-400 transition-transform duration-200 ${
              openPanels.citations ? 'rotate-180' : ''
            }`}
          />
        </button>

        {openPanels.citations && (
          <div className="px-5 pb-5 pt-1 space-y-3 border-t border-slate-800/50">
            {citedClauses.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 text-center">
                <AlertCircle className="w-5 h-5 text-sky-400 mx-auto mb-1.5" />
                No statutory standards cited. Under the zero-fabrication mandate, citations are only emitted when directly present in indexed context.
              </div>
            ) : (
              citedClauses.map((clause, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2 hover:border-slate-700 transition"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-sky-400 bg-sky-950/40 px-2.5 py-1 rounded-md border border-sky-500/30">
                        {clause.standard}
                      </span>
                      <span className="text-xs font-mono font-bold text-white bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                        {clause.clause_number}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
                        <ShieldCheck className="w-3 h-3" />
                        Verbatim Grounded
                      </span>

                      <button
                        onClick={() => handleCopyQuote(clause.verbatim_quote, idx)}
                        className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition flex items-center gap-1 text-xs font-mono"
                        title="Copy verbatim quote"
                      >
                        {copiedClauseIndex === idx ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                        <span className="text-[11px] hidden sm:inline">
                          {copiedClauseIndex === idx ? 'Copied' : 'Copy'}
                        </span>
                      </button>
                    </div>
                  </div>

                  {/* Verbatim Quote Block */}
                  <div className="relative pl-3.5 py-1 border-l-2 border-sky-500/60 bg-sky-950/10 rounded-r-lg">
                    <blockquote className="text-xs sm:text-sm text-slate-200 italic font-serif leading-relaxed">
                      "{clause.verbatim_quote}"
                    </blockquote>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default EvidenceAccordions;
