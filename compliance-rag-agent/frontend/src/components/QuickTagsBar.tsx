import React from 'react';
import { Tag, Building, Home, Factory, Sprout, Zap, Wrench } from 'lucide-react';
import { InspectionContext } from '../types';

interface QuickTagsBarProps {
  onSelectTag: (tagQuery: string, defaultContext?: InspectionContext) => void;
  selectedContext: InspectionContext;
  onSelectContext: (context: InspectionContext) => void;
}

export const QuickTagsBar: React.FC<QuickTagsBarProps> = ({
  onSelectTag,
  selectedContext,
  onSelectContext,
}) => {
  const quickTags = [
    {
      label: 'Socket-outlet without RCD',
      query: 'Socket-outlet installed without 30mA RCD protection',
      context: 'Domestic' as InspectionContext,
      hint: 'Reg 411.3.3 / BS 7671',
    },
    {
      label: 'Work on live conductors',
      query: 'Working on or near exposed live electrical conductors without justification',
      context: 'Commercial' as InspectionContext,
      hint: 'EAWR 1989 Reg 14',
    },
    {
      label: 'Earthing conductor disconnection',
      query: 'Absence or disconnection of main earthing conductor to installation',
      context: 'Domestic' as InspectionContext,
      hint: 'EAWR Reg 8 & BPG4 C2',
    },
    {
      label: 'Missing blanking piece on consumer unit',
      query: 'Circuit protective device missing from consumer unit with accessible live parts',
      context: 'Domestic' as InspectionContext,
      hint: 'BPG4 Code C1',
    },
    {
      label: 'Reg 4(2) System maintenance',
      query: 'What does Regulation 4(2) require regarding the maintenance of electrical systems to prevent danger?',
      context: 'Industrial' as InspectionContext,
      hint: 'EAWR Reg 4(2)',
    },
    {
      label: 'Reg 16 Competent persons',
      query: 'Persons to be competent to prevent danger and injury under Regulation 16',
      context: 'Industrial' as InspectionContext,
      hint: 'EAWR Reg 16',
    },
  ];

  const contexts: { id: InspectionContext; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
    { id: 'Domestic', label: 'Domestic', icon: Home },
    { id: 'Commercial', label: 'Commercial', icon: Building },
    { id: 'Industrial', label: 'Industrial', icon: Factory },
    { id: 'Agricultural', label: 'Agricultural', icon: Sprout },
    { id: 'Special Installation', label: 'Special (EV/PV)', icon: Zap },
  ];

  return (
    <div className="space-y-3">
      {/* 1. Operational Inspection Context Chips */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <Wrench className="w-3.5 h-3.5 text-emerald-400" />
          Operational Environment Context:
        </span>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          {contexts.map((ctx) => {
            const Icon = ctx.icon;
            const isSelected = selectedContext === ctx.id;
            return (
              <button
                key={ctx.id}
                type="button"
                onClick={() => onSelectContext(ctx.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium font-sans whitespace-nowrap transition ${
                  isSelected
                    ? 'bg-emerald-500 text-slate-950 font-bold shadow-md shadow-emerald-500/20'
                    : 'bg-slate-900/80 hover:bg-slate-800 text-slate-300 border border-slate-800'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-slate-950' : 'text-slate-400'}`} />
                <span>{ctx.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. Quick-Tap Scenario Tags */}
      <div>
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-400 mb-1.5">
          <Tag className="w-3 h-3 text-emerald-400" />
          <span>Quick Scenario Tags for Field Surveyors:</span>
        </div>

        <div className="flex flex-wrap gap-1.5">
          {quickTags.map((tag, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectTag(tag.query, tag.context)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 hover:border-emerald-500/40 text-xs text-slate-300 hover:text-white transition group shadow-sm"
            >
              <span className="font-medium">{tag.label}</span>
              <span className="text-[10px] font-mono text-slate-400 group-hover:text-emerald-400 bg-slate-950/80 px-1.5 py-0.5 rounded border border-slate-800">
                {tag.hint}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default QuickTagsBar;
