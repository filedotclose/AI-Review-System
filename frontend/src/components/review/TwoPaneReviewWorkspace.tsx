'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  Clock,
  HardHat,
  ChevronDown,
  ChevronUp,
  Flag,
  Ban,
  Check,
  RefreshCw,
  FileText,
  Activity,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export interface ReviewFinding {
  id: string;
  sourceKey: 'concrete' | 'equipment' | 'strata' | 'delays';
  title: string;
  description: string;
  severity: 'WARNING' | 'INFO' | 'CRITICAL';
  confidence: number;
  isFlagged?: boolean;
}

export interface ReviewDPRData {
  id: number;
  site_id: number;
  site_name: string;
  operational_date: string;
  shift: string;
  submitter_name: string;
  status: 'SUBMITTED' | 'VERIFIED' | 'REJECTED';
  piling_summary: {
    pile_number: string;
    diameter_mm: number;
    depth_drilled_m: number;
    rock_socket_m: number;
    strata: string;
    planned_concrete_m3: number;
    actual_concrete_m3: number;
    overbreak_pct: number;
  };
  equipment_summary: {
    name: string;
    hours_run: number;
    breakdown_hours: number;
    breakdown_reason?: string;
  };
  manpower_total: number;
  delays?: string;
  verified_at?: string;
}

interface TwoPaneReviewWorkspaceProps {
  dpr: ReviewDPRData;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
  onFlag: (id: number, reason: string) => void;
  onBackToList?: () => void;
}

export const TwoPaneReviewWorkspace: React.FC<TwoPaneReviewWorkspaceProps> = ({
  dpr,
  onApprove,
  onReject,
  onFlag,
  onBackToList,
}) => {
  const [activeHighlight, setActiveHighlight] = useState<string | null>(null);
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false);
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [findings, setFindings] = useState<ReviewFinding[]>([
    {
      id: 'finding-1',
      sourceKey: 'concrete',
      title: 'Concrete Overbreak Variance (+8.9%)',
      description:
        'Actual pour of 15.8 m³ exceeds theoretical cylinder (14.5 m³). Overbreak is within standard Kerala coastal rock tolerance (<15%).',
      severity: 'INFO',
      confidence: 0.94,
    },
    {
      id: 'finding-2',
      sourceKey: 'equipment',
      title: 'Rotary Rig Downtime (1.5h Unscheduled)',
      description:
        'Bauer BG-28 hydraulic hose leak during day shift boring. Mechanic log indicates O-ring replaced and pressure certified at 280 bar.',
      severity: 'WARNING',
      confidence: 0.91,
    },
    {
      id: 'finding-3',
      sourceKey: 'delays',
      title: 'Transit Mixer Bypass Congestion (1.0h)',
      description:
        'Delayed batch #3 arrival caused cold-joint prevention standby. Secondary mixer re-routed successfully from plant #2.',
      severity: 'WARNING',
      confidence: 0.88,
    },
  ]);

  // Refs for scrolling to passages
  const concreteRef = useRef<HTMLDivElement>(null);
  const equipmentRef = useRef<HTMLDivElement>(null);
  const delaysRef = useRef<HTMLDivElement>(null);
  const strataRef = useRef<HTMLDivElement>(null);

  const getSourceRef = (key: string) => {
    switch (key) {
      case 'concrete':
        return concreteRef;
      case 'equipment':
        return equipmentRef;
      case 'delays':
        return delaysRef;
      case 'strata':
        return strataRef;
      default:
        return null;
    }
  };

  // Keyboard Navigation: A (Approve), R (Reject), F (Flag), E (Reasoning)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input or textarea
      if (
        document.activeElement?.tagName === 'INPUT' ||
        document.activeElement?.tagName === 'TEXTAREA'
      ) {
        return;
      }

      if (e.key === 'a' || e.key === 'A') {
        e.preventDefault();
        onApprove(dpr.id);
      } else if (e.key === 'r' || e.key === 'R') {
        e.preventDefault();
        onReject(dpr.id);
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        const reason = prompt('Enter Revision Notes / Observation:');
        if (reason) onFlag(dpr.id, reason);
      } else if (e.key === 'e' || e.key === 'E') {
        e.preventDefault();
        setIsReasoningExpanded((prev) => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dpr.id, onApprove, onReject, onFlag]);

  const handleSelectFinding = (finding: ReviewFinding) => {
    setActiveHighlight(finding.sourceKey);
    const targetRef = getSourceRef(finding.sourceKey);
    if (targetRef?.current) {
      targetRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const handleSelectSource = (key: 'concrete' | 'equipment' | 'strata' | 'delays') => {
    setActiveHighlight(key);
  };

  const triggerAiReanalysis = () => {
    setIsAiProcessing(true);
    setTimeout(() => {
      setIsAiProcessing(false);
    }, 1200);
  };

  const toggleFlagFinding = (id: string) => {
    setFindings((prev) =>
      prev.map((f) => (f.id === id ? { ...f, isFlagged: !f.isFlagged } : f))
    );
  };

  return (
    <div className="flex flex-col h-full bg-bg font-sans select-none">
      {/* Top Review Bar */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-border glass-surface shrink-0">
        <div className="flex items-center gap-3">
          {onBackToList && (
            <button
              type="button"
              onClick={onBackToList}
              className="text-xs text-text-muted hover:text-text px-2 py-1 rounded hover:bg-surface-sunk transition-colors"
            >
              ← Back to Queue
            </button>
          )}
          <div className="h-4 w-px bg-border hidden sm:block" />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-text">
                Review Workspace: DPR #{dpr.id}
              </h2>
              <Badge variant="accent" size="sm">
                {dpr.shift} SHIFT
              </Badge>
              {dpr.status === 'VERIFIED' ? (
                <Badge variant="verified" size="sm">
                  Verified
                </Badge>
              ) : (
                <Badge variant="ai" size="sm">
                  AI Inspected
                </Badge>
              )}
            </div>
            <p className="text-[11px] text-text-muted">
              {dpr.site_name} • Operational Date: {dpr.operational_date}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={triggerAiReanalysis}
            disabled={isAiProcessing}
            leftIcon={<RefreshCw className={`h-3.5 w-3.5 ${isAiProcessing ? 'animate-spin text-accent' : ''}`} />}
          >
            {isAiProcessing ? 'Evaluating...' : 'Re-run AI Analysis'}
          </Button>
        </div>
      </div>

      {/* Calm AI Pulse Progress Bar during active analysis */}
      {isAiProcessing && (
        <div className="h-0.5 w-full bg-surface-sunk ai-pulse-bar" />
      )}

      {/* Main Two-Pane Split Screen (Section 7) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden">
        {/* LEFT PANE: SOURCE MATERIAL (7 Cols) */}
        <div className="lg:col-span-7 border-r border-border overflow-y-auto p-6 space-y-5 bg-bg/50">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-text-muted" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                Source Submission & Telemetry
              </h3>
            </div>
            <span className="text-[11px] text-text-faint">
              Submitted by {dpr.submitter_name}
            </span>
          </div>

          {/* Section A: Boring & Pile Cavity */}
          <div
            ref={strataRef}
            onClick={() => handleSelectSource('strata')}
            className={`p-5 rounded-lg border transition-all duration-fast cursor-pointer ${
              activeHighlight === 'strata'
                ? 'bg-surface border-accent shadow-soft ring-1 ring-accent/20'
                : 'bg-surface border-border hover:border-border-strong'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-text flex items-center gap-2">
                <HardHat className="h-3.5 w-3.5 text-accent" />
                Piling Geometry & Socketing: {dpr.piling_summary.pile_number}
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-pill bg-surface-sunk text-text-muted border border-border">
                Passage #1
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-2.5 rounded bg-surface-sunk/60">
                <span className="text-text-faint block text-[10px]">Diameter</span>
                <span className="font-semibold text-text font-mono">
                  {dpr.piling_summary.diameter_mm} mm
                </span>
              </div>
              <div className="p-2.5 rounded bg-surface-sunk/60">
                <span className="text-text-faint block text-[10px]">Depth Drilled</span>
                <span className="font-semibold text-text font-mono">
                  {dpr.piling_summary.depth_drilled_m} m
                </span>
              </div>
              <div className="p-2.5 rounded bg-surface-sunk/60">
                <span className="text-text-faint block text-[10px]">Rock Socket</span>
                <span className="font-semibold text-text font-mono">
                  {dpr.piling_summary.rock_socket_m} m
                </span>
              </div>
              <div className="p-2.5 rounded bg-surface-sunk/60">
                <span className="text-text-faint block text-[10px]">Strata Classified</span>
                <span className="font-semibold text-text">
                  {dpr.piling_summary.strata}
                </span>
              </div>
            </div>
          </div>

          {/* Section B: Concrete Overbreak (Linked with Finding 1) */}
          <div
            ref={concreteRef}
            onClick={() => handleSelectSource('concrete')}
            className={`p-5 rounded-lg border transition-all duration-fast cursor-pointer ${
              activeHighlight === 'concrete'
                ? 'bg-surface border-accent shadow-soft ring-1 ring-accent/20'
                : 'bg-surface border-border hover:border-border-strong'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-text flex items-center gap-2">
                <Activity className="h-3.5 w-3.5 text-status-warning" />
                Concrete Displacement & Volumetric Overbreak
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-pill bg-accent-soft text-accent border border-accent/20">
                Linked Passage ◄► Finding 1
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded bg-surface-sunk/60">
                <span className="text-text-faint block text-[10px]">Theoretical Cylindrical Volume</span>
                <span className="text-sm font-semibold text-text font-mono">
                  {dpr.piling_summary.planned_concrete_m3} m³
                </span>
              </div>
              <div className="p-3 rounded bg-surface-sunk/60">
                <span className="text-text-faint block text-[10px]">Actual Poured (Transit Mixer)</span>
                <span className="text-sm font-semibold text-text font-mono">
                  {dpr.piling_summary.actual_concrete_m3} m³
                </span>
              </div>
              <div className="p-3 rounded bg-surface-sunk/60 border border-status-warning/20">
                <span className="text-text-faint block text-[10px]">Overbreak Variance</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="text-sm font-bold text-status-warning font-mono">
                    +{dpr.piling_summary.overbreak_pct}%
                  </span>
                  <span className="text-[10px] text-text-faint">(Benchmark &lt;15%)</span>
                </div>
              </div>
            </div>
            <p className="text-[11px] text-text-muted mt-2.5">
              Casing lowered: 6.0m temporary casing. Slump tested at 180mm. Bentonite density 1.05 g/cc.
            </p>
          </div>

          {/* Section C: Equipment Runtime & Hose Breakdown (Linked with Finding 2) */}
          <div
            ref={equipmentRef}
            onClick={() => handleSelectSource('equipment')}
            className={`p-5 rounded-lg border transition-all duration-fast cursor-pointer ${
              activeHighlight === 'equipment'
                ? 'bg-surface border-accent shadow-soft ring-1 ring-accent/20'
                : 'bg-surface border-border hover:border-border-strong'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-text flex items-center gap-2">
                <Clock className="h-3.5 w-3.5 text-accent" />
                Equipment Telematics & Maintenance Log
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-pill bg-accent-soft text-accent border border-accent/20">
                Linked Passage ◄► Finding 2
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-2.5 rounded bg-surface-sunk/60">
                <span className="text-text-faint block text-[10px]">Machine</span>
                <span className="font-semibold text-text truncate block">
                  {dpr.equipment_summary.name}
                </span>
              </div>
              <div className="p-2.5 rounded bg-surface-sunk/60">
                <span className="text-text-faint block text-[10px]">Operating Hours</span>
                <span className="font-semibold text-text font-mono">
                  {dpr.equipment_summary.hours_run} hrs
                </span>
              </div>
              <div className="p-2.5 rounded bg-surface-sunk/60">
                <span className="text-text-faint block text-[10px]">Breakdown Loss</span>
                <span className="font-semibold text-status-warning font-mono">
                  {dpr.equipment_summary.breakdown_hours} hrs
                </span>
              </div>
            </div>

            {dpr.equipment_summary.breakdown_reason && (
              <div className="mt-3 p-2.5 rounded bg-status-warning-soft/40 border border-status-warning/20 text-xs">
                <span className="font-medium text-status-warning block mb-0.5">
                  Reported Issue:
                </span>
                <span className="text-text-muted">
                  {dpr.equipment_summary.breakdown_reason}
                </span>
              </div>
            )}
          </div>

          {/* Section D: Delays & Obstructions (Linked with Finding 3) */}
          <div
            ref={delaysRef}
            onClick={() => handleSelectSource('delays')}
            className={`p-5 rounded-lg border transition-all duration-fast cursor-pointer ${
              activeHighlight === 'delays'
                ? 'bg-surface border-accent shadow-soft ring-1 ring-accent/20'
                : 'bg-surface border-border hover:border-border-strong'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-text flex items-center gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-status-warning" />
                Problems & Logged Operational Delays
              </span>
              <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-pill bg-accent-soft text-accent border border-accent/20">
                Linked Passage ◄► Finding 3
              </span>
            </div>
            <p className="text-xs text-text-muted leading-relaxed">
              {dpr.delays || 'No critical delay incidents logged for this shift.'}
            </p>
          </div>
        </div>

        {/* RIGHT PANE: AI ANALYSIS (5 Cols) */}
        <div className="lg:col-span-5 flex flex-col h-full bg-surface overflow-y-auto p-6 space-y-5">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                AI Synthesis & Anomaly Detection
              </h3>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-pill bg-surface-sunk text-text-muted border border-border">
              Gemini Pro Civil Engine
            </span>
          </div>

          {/* AI Summary Card with Visual Confidence Gauge */}
          <div className="p-4 rounded-lg bg-surface-sunk/60 border border-border space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h4 className="text-xs font-semibold text-text">
                  Executive Assessment: Moderate Risk / Ready for Sign-Off
                </h4>
                <p className="text-xs text-text-muted mt-1 leading-relaxed">
                  Boring parameters adhere to structural engineering tolerances. Concrete overbreak (+8.9%) is acceptable for weathered rock socketing. Rig downtime was resolved with valid inspection.
                </p>
              </div>
            </div>

            {/* Visual Confidence Meter (Section 7) */}
            <div className="pt-2 border-t border-border space-y-1">
              <div className="flex justify-between text-[11px]">
                <span className="text-text-muted font-medium">Model Confidence</span>
                <span className="font-mono text-text font-semibold">94.2%</span>
              </div>
              <div className="h-1.5 w-full bg-border rounded-pill overflow-hidden">
                <div
                  className="h-full bg-accent rounded-pill transition-all duration-base"
                  style={{ width: '94.2%' }}
                />
              </div>
            </div>
          </div>

          {/* Interactive Findings List (Section 7) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-text-muted font-semibold uppercase tracking-wider">
              <span>Detected Findings ({findings.length})</span>
              <span className="text-[10px] text-text-faint font-normal normal-case">
                Click finding to locate source
              </span>
            </div>

            {findings.map((f) => {
              const isSelected = activeHighlight === f.sourceKey;
              return (
                <div
                  key={f.id}
                  onClick={() => handleSelectFinding(f)}
                  className={`p-3.5 rounded-md border text-xs transition-all duration-fast cursor-pointer ${
                    isSelected
                      ? 'bg-accent-soft/30 border-accent shadow-soft'
                      : 'bg-surface-sunk/40 border-border hover:border-border-strong hover:bg-surface-sunk'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-semibold text-text flex items-center gap-1.5">
                      <span
                        className={`h-2 w-2 rounded-pill shrink-0 ${
                          f.severity === 'CRITICAL'
                            ? 'bg-status-danger'
                            : f.severity === 'WARNING'
                            ? 'bg-status-warning'
                            : 'bg-status-success'
                        }`}
                      />
                      <span>{f.title}</span>
                    </div>

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFlagFinding(f.id);
                      }}
                      title="Flag finding for revision"
                      className={`p-1 rounded transition-colors ${
                        f.isFlagged
                          ? 'text-status-warning bg-status-warning-soft'
                          : 'text-text-faint hover:text-text'
                      }`}
                    >
                      <Flag className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  <p className="text-[11px] text-text-muted mt-1.5 leading-relaxed">
                    {f.description}
                  </p>

                  <div className="mt-2 pt-2 border-t border-border flex items-center justify-between text-[10px] text-text-faint">
                    <span className="font-mono">
                      Confidence: {Math.round(f.confidence * 100)}%
                    </span>
                    <span className="text-accent hover:underline">
                      {isSelected ? '● Highlighting Source' : 'View in Source →'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Collapsible Reasoning Block (Section 7) */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setIsReasoningExpanded(!isReasoningExpanded)}
              className="w-full flex items-center justify-between p-3 rounded-md bg-surface-sunk/60 border border-border text-xs text-text-muted hover:text-text transition-colors"
            >
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-accent" />
                <span className="font-semibold">AI Technical Reasoning & Chain</span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-text-faint">
                <kbd className="hidden sm:inline font-mono text-[10px] px-1 bg-surface border border-border rounded">
                  E
                </kbd>
                {isReasoningExpanded ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </div>
            </button>

            {isReasoningExpanded && (
              <div className="p-4 mt-2 rounded-md bg-surface-sunk/40 border border-border text-xs text-text-muted font-mono leading-relaxed space-y-2 animate-in fade-in duration-fast">
                <div>
                  [RULE-101] Checked theoretical bore cavity: V = π * (1.0m / 2)² * 18.5m = 14.53 m³.
                </div>
                <div>
                  [RULE-102] Checked pour ticket 15.8 m³: Overbreak ratio = (15.8 - 14.53) / 14.53 = +8.74% (logged at 8.9%).
                </div>
                <div>
                  [RULE-103] Cross-verified equipment breakdown: 1.5 hrs match pump stroke frequency drop recorded at 14:15 IST.
                </div>
                <div>
                  [RECOMMENDATION] No concrete honeycombing risk identified; approve pile casting.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* STICKY BOTTOM ACTION BAR (Section 7) */}
      <div className="glass-surface sticky bottom-0 z-30 border-t border-border px-6 py-3.5 flex items-center justify-between gap-4 shrink-0 shadow-soft">
        <div className="flex items-center gap-3">
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onReject(dpr.id)}
            leftIcon={<Ban className="h-3.5 w-3.5" />}
          >
            <span>Reject DPR</span>
            <kbd className="ml-1 text-[10px] font-mono opacity-80">R</kbd>
          </Button>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              const reason = prompt('Enter Revision Notes / Observation:');
              if (reason) onFlag(dpr.id, reason);
            }}
            leftIcon={<Flag className="h-3.5 w-3.5" />}
          >
            <span>Flag for Revision</span>
            <kbd className="ml-1 text-[10px] font-mono text-text-faint">F</kbd>
          </Button>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden sm:block text-right">
            <span className="text-[11px] text-text-faint block">
              Human In The Loop Sign-off
            </span>
          </div>

          <Button
            variant="primary"
            size="md"
            onClick={() => onApprove(dpr.id)}
            leftIcon={<Check className="h-4 w-4" />}
          >
            <span>Approve & Verify DPR</span>
            <kbd className="ml-1.5 text-[10px] font-mono opacity-80">A</kbd>
          </Button>
        </div>
      </div>
    </div>
  );
};

export default TwoPaneReviewWorkspace;
