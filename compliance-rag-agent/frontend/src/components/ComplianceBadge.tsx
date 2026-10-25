import React from 'react';
import { ComplianceVerdict } from '../types';
import { CheckCircle2, XCircle, AlertTriangle, HelpCircle } from 'lucide-react';

interface Props {
  verdict: ComplianceVerdict;
  className?: string;
}

export const ComplianceBadge: React.FC<Props> = ({ verdict, className = '' }) => {
  switch (verdict) {
    case 'COMPLIANT':
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 ${className}`}>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          COMPLIANT
        </span>
      );
    case 'NON_COMPLIANT':
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 ${className}`}>
          <XCircle className="w-3.5 h-3.5 text-rose-400" />
          NON-COMPLIANT
        </span>
      );
    case 'PARTIALLY_COMPLIANT':
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 ${className}`}>
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          PARTIALLY COMPLIANT
        </span>
      );
    case 'NEEDS_REVIEW':
    default:
      return (
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30 ${className}`}>
          <HelpCircle className="w-3.5 h-3.5 text-blue-400" />
          NEEDS REVIEW
        </span>
      );
  }
};
