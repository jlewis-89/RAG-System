import React from 'react';
import { CitationItem } from '../types';
import { BookOpen, ShieldCheck, Tag } from 'lucide-react';

interface Props {
  citation: CitationItem;
  index: number;
}

export const CitationCard: React.FC<Props> = ({ citation, index }) => {
  const scorePercent = Math.round(citation.relevance_score * 100);

  return (
    <div className="glass-card rounded-xl p-4 transition-all duration-200 hover:border-emerald-500/40 hover:bg-slate-800/60">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="flex items-center justify-center w-6 h-6 rounded-md bg-emerald-500/20 text-emerald-400 text-xs font-mono font-bold">
            #{index + 1}
          </span>
          <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-slate-800 text-emerald-300 border border-slate-700">
            {citation.standard_code}
          </span>
          <span className="text-xs text-slate-300 font-medium truncate max-w-[150px] sm:max-w-[240px]">
            {citation.clause}
          </span>
        </div>
        <div className="flex items-center gap-1 text-xs font-mono font-semibold text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
          <ShieldCheck className="w-3.5 h-3.5" />
          {scorePercent}% match
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-xs text-slate-400 mb-2">
        <BookOpen className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
        <span className="truncate">{citation.source}</span>
      </div>

      <div className="bg-slate-950/70 rounded-lg p-3 border border-slate-800/80">
        <p className="text-xs text-slate-300 font-mono leading-relaxed line-clamp-4">
          "{citation.snippet}"
        </p>
      </div>

      <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-400">
        <span className="font-mono text-slate-400 truncate max-w-[180px]">
          ID: {citation.chunk_id}
        </span>
        <span className="inline-flex items-center gap-1 text-emerald-400/80">
          <Tag className="w-3 h-3" />
          Regulatory Clause
        </span>
      </div>
    </div>
  );
};
