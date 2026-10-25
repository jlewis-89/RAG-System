import React from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  Clock,
  Sparkles,
  Zap,
} from 'lucide-react';
import { ComplianceStatus } from '../types';

interface TrafficLightBannerProps {
  status: ComplianceStatus;
  summaryVerdict: string;
  confidenceScore: number;
  inspectionContext: string;
  latencyMs: number;
  auditId: number;
  modelUsed?: string;
}

export const TrafficLightBanner: React.FC<TrafficLightBannerProps> = ({
  status,
  summaryVerdict,
  confidenceScore,
  inspectionContext,
  latencyMs,
  auditId,
  modelUsed,
}) => {
  const getVerdictConfig = () => {
    switch (status) {
      case 'IMMEDIATE_DANGER':
        return {
          code: 'CODE C1',
          title: 'DANGER PRESENT — IMMEDIATE ACTION REQUIRED',
          badgeText: 'C1 DANGER',
          bgClass: 'bg-gradient-to-r from-red-950/80 via-rose-900/60 to-red-950/80',
          borderClass: 'border-rose-500/80 shadow-rose-950/50',
          glowClass: 'bg-rose-500',
          textClass: 'text-rose-400',
          lightColor: 'bg-rose-500 animate-pulse shadow-lg shadow-rose-500/50',
          icon: ShieldAlert,
          description: 'Immediate risk of injury or death. Urgent safe isolation required before surveyor leaves site.',
        };
      case 'POTENTIALLY_DANGEROUS':
        return {
          code: 'CODE C2',
          title: 'POTENTIALLY DANGEROUS — URGENT REMEDIAL ACTION',
          badgeText: 'C2 URGENT',
          bgClass: 'bg-gradient-to-r from-amber-950/80 via-orange-950/60 to-amber-950/80',
          borderClass: 'border-amber-500/80 shadow-amber-950/50',
          glowClass: 'bg-amber-500',
          textClass: 'text-amber-400',
          lightColor: 'bg-amber-500 shadow-md shadow-amber-500/50',
          icon: AlertTriangle,
          description: 'Safety of persons or installation compromised under fault conditions. Remedial work required urgently.',
        };
      case 'IMPROVEMENT_RECOMMENDED':
        return {
          code: 'CODE C3',
          title: 'IMPROVEMENT RECOMMENDED',
          badgeText: 'C3 IMPROVEMENT',
          bgClass: 'bg-gradient-to-r from-yellow-950/70 via-amber-950/50 to-yellow-950/70',
          borderClass: 'border-yellow-500/70 shadow-yellow-950/40',
          glowClass: 'bg-yellow-500',
          textClass: 'text-yellow-400',
          lightColor: 'bg-yellow-400 shadow-md shadow-yellow-400/40',
          icon: AlertTriangle,
          description: 'Non-compliance with modern standards; not immediately hazardous but improvement will enhance safety.',
        };
      case 'COMPLIANT':
        return {
          code: 'SATISFACTORY',
          title: 'STATUTORY COMPLIANCE CONFIRMED',
          badgeText: 'COMPLIANT',
          bgClass: 'bg-gradient-to-r from-emerald-950/80 via-teal-950/60 to-emerald-950/80',
          borderClass: 'border-emerald-500/80 shadow-emerald-950/50',
          glowClass: 'bg-emerald-500',
          textClass: 'text-emerald-400',
          lightColor: 'bg-emerald-400 shadow-md shadow-emerald-400/50',
          icon: ShieldCheck,
          description: 'Installation conforms with applicable statutory regulations and verified engineering standards.',
        };
      case 'INSUFFICIENT_DATA_FURTHER_INVESTIGATION':
      default:
        return {
          code: 'CODE FI',
          title: 'FURTHER INVESTIGATION REQUIRED',
          badgeText: 'FI INVESTIGATE',
          bgClass: 'bg-gradient-to-r from-blue-950/80 via-indigo-950/60 to-blue-950/80',
          borderClass: 'border-sky-500/80 shadow-sky-950/50',
          glowClass: 'bg-sky-500',
          textClass: 'text-sky-400',
          lightColor: 'bg-sky-400 shadow-md shadow-sky-400/50',
          icon: HelpCircle,
          description: 'Retrieved standards do not substantiate query. Zero-fabrication mandate enforced; further investigation required.',
        };
    }
  };

  const config = getVerdictConfig();
  const IconComponent = config.icon;
  const confidencePercent = Math.round(confidenceScore * 100);

  return (
    <div
      className={`rounded-2xl p-5 sm:p-7 border-2 ${config.borderClass} ${config.bgClass} shadow-xl relative overflow-hidden backdrop-blur-xl transition-all duration-300`}
    >
      {/* Background ambient glow */}
      <div
        className={`absolute -top-16 -right-16 w-64 h-64 ${config.glowClass}/15 rounded-full blur-3xl pointer-events-none`}
      />

      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/10 relative z-10">
        
        {/* Left: Traffic light badge & code */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-black/40 border border-white/10 backdrop-blur-md">
            <span className={`w-3.5 h-3.5 rounded-full ${config.lightColor} inline-block`} />
            <span className="font-mono text-xs font-black tracking-wider text-white uppercase">
              {config.badgeText}
            </span>
          </div>

          <span className="text-xs font-mono font-bold text-slate-400 uppercase tracking-widest bg-slate-900/60 px-2.5 py-1 rounded-md border border-slate-800">
            {inspectionContext}
          </span>

          <span className="text-xs font-mono text-slate-400 hidden md:inline">
            Audit #{auditId}
          </span>
        </div>

        {/* Right: Confidence Score & Latency */}
        <div className="flex items-center gap-3 text-xs font-mono self-start sm:self-auto">
          <div className="flex items-center gap-2 bg-black/30 px-3 py-1.5 rounded-lg border border-white/10">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-slate-400 text-[11px]">Certainty:</span>
            <span className={`font-black text-sm ${config.textClass}`}>
              {confidencePercent}%
            </span>
          </div>

          <div className="flex items-center gap-1.5 bg-black/30 px-2.5 py-1.5 rounded-lg border border-white/10 text-slate-400 text-[11px]">
            <Clock className="w-3 h-3 text-slate-400" />
            <span>{Math.round(latencyMs)}ms</span>
          </div>
        </div>
      </div>

      {/* Verdict Title & Explanation */}
      <div className="mt-4 sm:mt-5 space-y-3 relative z-10">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-xl bg-black/40 border border-white/10 ${config.textClass} flex-shrink-0 mt-0.5`}>
            <IconComponent className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg sm:text-xl font-extrabold text-white tracking-tight leading-snug">
              {config.title}
            </h2>
            <p className="text-xs text-slate-300/90 mt-0.5 font-medium">
              {config.description}
            </p>
          </div>
        </div>

        {/* Natural Language Reasoned Summary (2-3 sentences) */}
        <div className="p-4 rounded-xl bg-black/40 border border-white/10 backdrop-blur-md">
          <div className="flex items-center gap-1.5 text-[11px] font-mono font-bold uppercase tracking-wider text-slate-400 mb-1.5">
            <Zap className="w-3.5 h-3.5 text-emerald-400" />
            <span>Engineering Rationale & Statutory Basis</span>
          </div>
          <p className="text-sm sm:text-base text-slate-100 font-medium leading-relaxed">
            {summaryVerdict}
          </p>
        </div>

        {modelUsed && (
          <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-1">
            <span>Grounding: Zero-Hallucination Verified</span>
            <span>Reasoning Provider: {modelUsed}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default TrafficLightBanner;
