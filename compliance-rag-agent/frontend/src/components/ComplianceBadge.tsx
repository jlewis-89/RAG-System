import React from 'react';
import { ComplianceStatus } from '../types';
import { CheckCircle2, AlertTriangle, AlertOctagon, HelpCircle } from 'lucide-react';

interface Props {
  verdict: ComplianceStatus | string;
  className?: string;
}

export const ComplianceBadge: React.FC<Props> = ({ verdict, className = '' }) => {
  const norm = String(verdict || '').toUpperCase();

  if (norm === 'IMMEDIATE_DANGER' || norm === 'NON_COMPLIANT' || norm === 'C1') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/40 shadow-sm shadow-rose-950 ${className}`}
      >
        <AlertOctagon className="w-3.5 h-3.5 text-rose-400" />
        CODE C1 — IMMEDIATE DANGER
      </span>
    );
  }

  if (norm === 'POTENTIALLY_DANGEROUS' || norm === 'PARTIALLY_COMPLIANT' || norm === 'C2') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/40 shadow-sm shadow-amber-950 ${className}`}
      >
        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
        CODE C2 — POTENTIALLY DANGEROUS
      </span>
    );
  }

  if (norm === 'IMPROVEMENT_RECOMMENDED' || norm === 'C3') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-yellow-500/15 text-yellow-400 border border-yellow-500/40 shadow-sm shadow-yellow-950 ${className}`}
      >
        <AlertTriangle className="w-3.5 h-3.5 text-yellow-400" />
        CODE C3 — IMPROVEMENT RECOMMENDED
      </span>
    );
  }

  if (norm === 'COMPLIANT') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/40 shadow-sm shadow-emerald-950 ${className}`}
      >
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        COMPLIANT — SATISFACTORY
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-sky-500/15 text-sky-400 border border-sky-500/40 shadow-sm shadow-sky-950 ${className}`}
    >
      <HelpCircle className="w-3.5 h-3.5 text-sky-400" />
      CODE FI — FURTHER INVESTIGATION
    </span>
  );
};

export default ComplianceBadge;
