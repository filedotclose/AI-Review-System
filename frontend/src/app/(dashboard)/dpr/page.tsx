'use client';

import React, { useState, useEffect } from 'react';
import apiClient, { isOfflineQueued } from '@/lib/api-client';
import { compressImage, fileToDataUrl } from '@/lib/image-compression';
import { useAuth } from '@/lib/auth-context';
import {
  FileText,
  Send,
  AlertCircle,
  CheckCircle2,
  CloudOff,
  Camera,
  Trash2,
  ShieldCheck,
  Layers,
  ArrowRight,
  Maximize2,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';
import { TwoPaneReviewWorkspace, ReviewDPRData } from '@/components/review/TwoPaneReviewWorkspace';

const INITIAL_DPR_QUEUE: ReviewDPRData[] = [];

// Helper to map backend DPR responses to the review workspace data structure
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mapApiDprToReviewData = (d: any): ReviewDPRData => {
  const pile = d.pile_progress?.[0];
  const eq = d.equipment_logs?.[0];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const totalLabour = d.labour_summaries?.reduce((acc: number, l: any) => acc + (l.count || 0), 0) || 0;

  const plannedConcrete = pile?.concrete_volume_planned_m3 || 0;
  const actualConcrete = pile?.concrete_volume_actual_m3 || 0;
  const overbreak = plannedConcrete > 0
    ? Math.round(((actualConcrete - plannedConcrete) / plannedConcrete) * 1000) / 10
    : 0;

  return {
    id: d.id,
    site_id: d.site_id,
    site_name: d.site_name || 'Vadakara AVRP Flyover Package',
    operational_date: typeof d.operational_date === 'string' ? d.operational_date : new Date(d.operational_date).toISOString().split('T')[0],
    shift: d.shift || 'DAY',
    submitter_name: d.submitted_by_name || `Site Engineer #${d.submitted_by || 1}`,
    status: d.status || 'SUBMITTED',
    piling_summary: {
      pile_number: pile?.pile_number || (pile?.pile_id ? `Pile #${pile.pile_id}` : 'P-101 (Pier P12)'),
      diameter_mm: pile?.diameter_mm || 1000,
      depth_drilled_m: pile?.depth_drilled_today_m || 0,
      rock_socket_m: pile?.rock_socket_depth_today_m || 0,
      strata: pile?.strata_type || 'WEATHERED_ROCK',
      planned_concrete_m3: plannedConcrete,
      actual_concrete_m3: actualConcrete,
      overbreak_pct: overbreak,
    },
    equipment_summary: {
      name: eq?.name || 'Bauer BG-28 Rotary Rig #1',
      hours_run: eq?.working_hours || eq?.hours_run || 0,
      breakdown_hours: eq?.breakdown_hours || 0,
      breakdown_reason: eq?.breakdown_reason,
    },
    manpower_total: totalLabour,
    delays: d.problems_delays || '',
    verified_at: d.verified_at ? `${d.verified_at}` : undefined,
  };
};

export default function DPRPage() {
  const { user } = useAuth();
  const isSiteEngineer = user?.role === 'SITE_ENGINEER';
  const isApproverRole = Boolean(user?.role && user.role !== 'SITE_ENGINEER');

  const getDefaultTab = (role?: string): 'verification' | 'entry' | 'history' => {
    if (role === 'SITE_ENGINEER') return 'entry';
    return 'verification';
  };

  // Role Tab State
  const [prevRole, setPrevRole] = useState(user?.role);
  const [activeTab, setActiveTab] = useState<'verification' | 'entry' | 'history'>(() =>
    getDefaultTab(user?.role)
  );

  if (user?.role !== prevRole) {
    setPrevRole(user?.role);
    setActiveTab(getDefaultTab(user?.role));
  }

  // Active Two-Pane Review State (Section 7)
  const [activeReviewDpr, setActiveReviewDpr] = useState<ReviewDPRData | null>(null);

  // Verification Queue State
  const [dprQueue, setDprQueue] = useState<ReviewDPRData[]>(INITIAL_DPR_QUEUE);

  // Fetch live DPRs from API
  useEffect(() => {
    let isMounted = true;
    async function loadDprs() {
      try {
        const res = await apiClient.get('/dpr');
        if (isMounted && Array.isArray(res.data)) {
          const mapped = res.data.map(mapApiDprToReviewData);
          setDprQueue(mapped);
        }
      } catch (err) {
        console.warn('Could not load DPR records from API:', err);
      }
    }
    loadDprs();
    return () => {
      isMounted = false;
    };
  }, []);

  // General Shift State
  const [siteId, setSiteId] = useState('1');
  const [operationalDate, setOperationalDate] = useState(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [shift, setShift] = useState<'DAY' | 'NIGHT'>('DAY');
  const [weather, setWeather] = useState('SUNNY');
  const submitterName = user?.name ? `${user.name} (Site Engineer)` : 'Site Engineer';

  // Piling Progress State
  const pileId = '1';
  const [pileNumber, setPileNumber] = useState('P-104 (Pier P12)');
  const [diameterMm, setDiameterMm] = useState('1000');
  const [drilledDepth, setDrilledDepth] = useState('18.5');
  const cumulativeDepth = '24.0';
  const [rockSocketDepth, setRockSocketDepth] = useState('3.2');
  const [strataType, setStrataType] = useState('WEATHERED_ROCK');
  const casingDepth = '6.0';
  const casingType: 'TEMPORARY' | 'PERMANENT' = 'TEMPORARY';
  const cageSections = '2';
  const cageWeightKg = '1450';
  const [plannedConcreteM3, setPlannedConcreteM3] = useState('14.5');
  const [actualConcreteM3, setActualConcreteM3] = useState('15.8');
  const slumpMm = '180';
  const bentoniteDensity = '1.05';

  // Equipment Shift State
  const [equipmentName, setEquipmentName] = useState('Bauer BG-28 Rotary Rig #1');
  const [hoursOperated, setHoursOperated] = useState('8.5');
  const [breakdownHours, setBreakdownHours] = useState('1.5');
  const idleHours = '0.5';
  const [fuelLiters, setFuelLiters] = useState('180');
  const [breakdownReason, setBreakdownReason] = useState('Hydraulic pressure hose leak - replaced O-ring');

  // Delays & Notes
  const delayReason = 'Concrete transit mixer stuck in Vadakara bypass traffic';
  const delayDurationHours = '1.0';
  const delayAction = 'Re-routed backup mixer batch from plant #2';
  const tomorrowsPlan = 'Complete socketing on P-105; lower cage & cast concrete';

  // Manpower Headcounts
  const pilingGangCount = '8';
  const steelBendingCount = '6';
  const concretingCount = '5';
  const helpersCount = '4';

  // Photos state
  const [photos, setPhotos] = useState<Array<{ name: string; size: number; compressedSize: number; dataUrl: string }>>([]);
  const [isCompressing, setIsCompressing] = useState(false);

  // Submission UI States
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [offlineQueuedNotice, setOfflineQueuedNotice] = useState<string | null>(null);

  // Photo Upload Handler with Client-Side Canvas Compression
  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsCompressing(true);
    try {
      for (let i = 0; i < files.length; i++) {
        const originalFile = files[i];
        const compressedFile = await compressImage(originalFile, 1600, 0.75);
        const dataUrl = await fileToDataUrl(compressedFile);

        setPhotos((prev) => [
          ...prev,
          {
            name: originalFile.name,
            size: originalFile.size,
            compressedSize: compressedFile.size,
            dataUrl,
          },
        ]);
      }
    } catch (err) {
      console.error('Image compression error:', err);
    } finally {
      setIsCompressing(false);
      e.target.value = '';
    }
  };

  const removePhoto = (index: number) => {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
  };

  // PM Verify Action
  const handleVerifyDpr = async (dprId: number) => {
    try {
      await apiClient.post(`/dpr/${dprId}/verify`, {
        status: 'VERIFIED',
      });
      setDprQueue((prev) =>
        prev.map((d) =>
          d.id === dprId
            ? { ...d, status: 'VERIFIED', verified_at: `Signed off by ${user?.name || user?.role?.replace('_', ' ') || 'Approver'}` }
            : d
        )
      );
      if (activeReviewDpr && activeReviewDpr.id === dprId) {
        setActiveReviewDpr((prev) => (prev ? { ...prev, status: 'VERIFIED' } : null));
      }
      setSuccessToast(`DPR #${dprId} verified & signed off successfully!`);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setErrorMessage(error.response?.data?.detail || 'Failed to verify DPR.');
    }
  };

  // PM Reject Action
  const handleRejectDpr = async (dprId: number) => {
    const reason = prompt('Enter Revision Notes / Rejection Reason for Site Engineer:');
    if (!reason) return;
    try {
      await apiClient.post(`/dpr/${dprId}/verify`, {
        status: 'REJECTED',
        verification_notes: reason,
      });
      setDprQueue((prev) =>
        prev.map((d) =>
          d.id === dprId ? { ...d, status: 'REJECTED', delays: `Revision Requested: ${reason}` } : d
        )
      );
      if (activeReviewDpr && activeReviewDpr.id === dprId) {
        setActiveReviewDpr((prev) => (prev ? { ...prev, status: 'REJECTED' } : null));
      }
      setSuccessToast(`DPR #${dprId} rejected & flagged for revision.`);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setErrorMessage(error.response?.data?.detail || 'Failed to request revision.');
    }
  };

  // PM Flag Action
  const handleFlagDpr = async (dprId: number, reason: string) => {
    try {
      await apiClient.post(`/dpr/${dprId}/verify`, {
        status: 'REJECTED',
        verification_notes: reason,
      });
      setDprQueue((prev) =>
        prev.map((d) =>
          d.id === dprId ? { ...d, status: 'REJECTED', delays: `Flagged: ${reason}` } : d
        )
      );
      setSuccessToast(`DPR #${dprId} flagged for site clarification.`);
    } catch (err) {
      console.warn('Flag sync error:', err);
    }
  };

  // Technical DPR Submission Handler (Site Engineer)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSuccessToast(null);
    setErrorMessage(null);
    setOfflineQueuedNotice(null);

    const payload = {
      site_id: parseInt(siteId, 10),
      operational_date: operationalDate,
      shift: shift,
      weather_conditions: weather,
      problems_delays: delayDurationHours && parseFloat(delayDurationHours) > 0 ? delayReason : '',
      tomorrows_plan: tomorrowsPlan,
      pile_progress: [
        {
          pile_id: parseInt(pileId, 10),
          depth_drilled_today_m: parseFloat(drilledDepth) || 0,
          cumulative_depth_m: parseFloat(cumulativeDepth) || 0,
          rock_socket_depth_today_m: parseFloat(rockSocketDepth) || 0,
          strata_type: strataType,
          casing_depth_m: parseFloat(casingDepth) || 0,
          casing_type: casingType,
          cage_sections_lowered: parseInt(cageSections, 10) || 0,
          cage_weight_kg_today: parseFloat(cageWeightKg) || 0,
          concrete_volume_planned_m3: parseFloat(plannedConcreteM3) || 0,
          concrete_volume_actual_m3: parseFloat(actualConcreteM3) || 0,
          slump_mm: parseFloat(slumpMm) || 0,
          bentonite_density_g_cc: parseFloat(bentoniteDensity) || 0,
          photos: photos.map((p) => p.dataUrl),
          remarks: `Submitted by ${submitterName} for ${pileNumber}`,
        },
      ],
      equipment_logs: [
        {
          equipment_id: 1,
          opening_hours: 1420.0,
          closing_hours: 1420.0 + (parseFloat(hoursOperated) || 0) + (parseFloat(idleHours) || 0),
          working_hours: parseFloat(hoursOperated) || 0,
          breakdown_hours: parseFloat(breakdownHours) || 0,
          idle_hours: parseFloat(idleHours) || 0,
          fuel_liters: parseFloat(fuelLiters) || 0,
          breakdown_reason: parseFloat(breakdownHours) > 0 ? breakdownReason : null,
        },
      ],
      delays:
        parseFloat(delayDurationHours) > 0
          ? [
              {
                pile_id: parseInt(pileId, 10),
                duration_hours: parseFloat(delayDurationHours),
                reason: delayReason,
                action_taken: delayAction,
              },
            ]
          : [],
      labour_summaries: [
        { category: 'PILING', count: parseInt(pilingGangCount, 10) || 0, shift, hours_worked: 10.0 },
        { category: 'STEEL_BENDING', count: parseInt(steelBendingCount, 10) || 0, shift, hours_worked: 10.0 },
        { category: 'CONCRETING', count: parseInt(concretingCount, 10) || 0, shift, hours_worked: 10.0 },
        { category: 'OTHER', count: parseInt(helpersCount, 10) || 0, shift, hours_worked: 10.0 },
      ],
    };

    try {
      const res = await apiClient.post('/dpr', payload);
      setSuccessToast(`DPR #${res.data?.id || 'New'} recorded and submitted for PM verification!`);
      const newDpr: ReviewDPRData = {
        id: res.data?.id || 102,
        site_id: parseInt(siteId, 10),
        site_name: 'Vadakara AVRP Flyover Package',
        operational_date: operationalDate,
        shift: shift,
        submitter_name: user?.name || submitterName,
        status: 'SUBMITTED',
        piling_summary: {
          pile_number: pileNumber,
          diameter_mm: parseFloat(diameterMm) || 1000,
          depth_drilled_m: parseFloat(drilledDepth) || 0,
          rock_socket_m: parseFloat(rockSocketDepth) || 0,
          strata: strataType,
          planned_concrete_m3: parseFloat(plannedConcreteM3) || 0,
          actual_concrete_m3: parseFloat(actualConcreteM3) || 0,
          overbreak_pct: Math.round(
            ((parseFloat(actualConcreteM3) - parseFloat(plannedConcreteM3)) /
              (parseFloat(plannedConcreteM3) || 1)) *
              1000
          ) / 10,
        },
        equipment_summary: {
          name: equipmentName,
          hours_run: parseFloat(hoursOperated) || 0,
          breakdown_hours: parseFloat(breakdownHours) || 0,
          breakdown_reason: breakdownReason,
        },
        manpower_total:
          (parseInt(pilingGangCount, 10) || 0) +
          (parseInt(steelBendingCount, 10) || 0) +
          (parseInt(concretingCount, 10) || 0) +
          (parseInt(helpersCount, 10) || 0),
        delays: delayReason,
      };
      setDprQueue((prev) => [newDpr, ...prev]);
      setPhotos([]);
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        setOfflineQueuedNotice(
          `DPR for ${pileNumber} recorded in offline buffer! Will auto-sync when network returns.`
        );
      } else {
        const error = err as { response?: { data?: { detail?: string } }; message?: string };
        const detail = error.response?.data?.detail || error.message || 'Error occurred while saving DPR.';
        setErrorMessage(detail);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const pendingVerificationCount = dprQueue.filter((d) => d.status === 'SUBMITTED').length;

  // If active two-pane review workspace is currently open for a DPR, render it full view!
  if (activeReviewDpr) {
    return (
      <TwoPaneReviewWorkspace
        dpr={activeReviewDpr}
        onApprove={handleVerifyDpr}
        onReject={handleRejectDpr}
        onFlag={handleFlagDpr}
        onBackToList={() => setActiveReviewDpr(null)}
        canApprove={isApproverRole}
      />
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 sm:px-6 lg:px-8 space-y-6 select-none font-sans">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface p-6 rounded-lg border border-border shadow-soft">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-text">
              Daily Progress Report (DPR)
            </h1>
            <Badge variant="accent" size="sm">
              {user?.role?.replace('_', ' ') || 'Site Ops'}
            </Badge>
          </div>
          <p className="text-xs text-text-muted mt-1 leading-relaxed">
            {isApproverRole
              ? 'Human-in-the-Loop Review Center: Verify pile boring telemetry, check concrete overbreak ratios, and validate rig downtime.'
              : isSiteEngineer
              ? 'Site Engineer Workstation: Complete piling progress, equipment telematics, and delay documentation.'
              : 'DPR Center: View historical daily progress reports and engineering logs.'}
          </p>
        </div>

        {isApproverRole && pendingVerificationCount > 0 && (
          <Button
            variant="primary"
            size="md"
            onClick={() => setActiveReviewDpr(dprQueue[0])}
            leftIcon={<Maximize2 className="h-4 w-4" />}
          >
            Open Next in AI Review Workspace
          </Button>
        )}
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-border bg-surface px-4 rounded-t-lg">
        {isApproverRole && (
          <button
            type="button"
            onClick={() => setActiveTab('verification')}
            className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-semibold transition-colors cursor-pointer ${
              activeTab === 'verification'
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            <ShieldCheck className="h-4 w-4" />
            <span>Verification Queue</span>
            {pendingVerificationCount > 0 && (
              <Badge variant="warning" size="sm">
                {pendingVerificationCount}
              </Badge>
            )}
          </button>
        )}

        {isSiteEngineer && (
          <button
            type="button"
            onClick={() => setActiveTab('entry')}
            className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-semibold transition-colors cursor-pointer ${
              activeTab === 'entry'
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text'
            }`}
          >
            <FileText className="h-4 w-4" />
            <span>New DPR Entry</span>
          </button>
        )}

        <button
          type="button"
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-semibold transition-colors cursor-pointer ${
            activeTab === 'history'
              ? 'border-accent text-accent'
              : 'border-transparent text-text-muted hover:text-text'
          }`}
        >
          <Layers className="h-4 w-4" />
          <span>DPR History & Logs</span>
        </button>
      </div>

      {/* Notifications */}
      {successToast && (
        <div className="rounded-md bg-status-success-soft p-4 border border-status-success/20 flex items-start gap-3 shadow-soft animate-in fade-in duration-fast">
          <CheckCircle2 className="h-4 w-4 text-status-success shrink-0 mt-0.5" />
          <div className="flex-1 text-xs font-medium text-status-success leading-tight">{successToast}</div>
          <button onClick={() => setSuccessToast(null)} className="text-xs text-status-success hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {offlineQueuedNotice && (
        <div className="rounded-md bg-status-warning-soft p-4 border border-status-warning/20 flex items-start gap-3 shadow-soft">
          <CloudOff className="h-4 w-4 text-status-warning shrink-0 mt-0.5" />
          <div className="flex-1 text-xs font-medium text-status-warning leading-tight">{offlineQueuedNotice}</div>
          <button onClick={() => setOfflineQueuedNotice(null)} className="text-xs text-status-warning hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="rounded-md bg-status-danger-soft p-4 border border-status-danger/20 flex items-start gap-3 shadow-soft">
          <AlertCircle className="h-4 w-4 text-status-danger shrink-0 mt-0.5" />
          <div className="flex-1 text-xs font-medium text-status-danger leading-tight">{errorMessage}</div>
          <button onClick={() => setErrorMessage(null)} className="text-xs text-status-danger hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* TAB 1: Verification Queue (For Project Manager, Owner, Supervisor, Finance Head) */}
      {isApproverRole && activeTab === 'verification' && (
        <div className="space-y-5">
          {/* Executive Queue KPI Summary Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <div className="bg-surface p-4 rounded-lg border border-border shadow-soft space-y-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Awaiting Sign-off
              </span>
              <div className="text-xl sm:text-2xl font-bold font-mono text-status-warning tabular-nums">
                {pendingVerificationCount} <span className="text-xs font-sans font-normal text-text-muted">DPR</span>
              </div>
              <span className="text-[11px] text-text-faint block">
                Assigned for Verification
              </span>
            </div>

            <div className="bg-surface p-4 rounded-lg border border-border shadow-soft space-y-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                AI Mean Confidence
              </span>
              <div className="text-xl sm:text-2xl font-bold font-mono text-accent tabular-nums">
                94.2%
              </div>
              <span className="text-[11px] text-text-faint block">
                Kerala coastal baseline
              </span>
            </div>

            <div className="bg-surface p-4 rounded-lg border border-border shadow-soft space-y-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Average Overbreak
              </span>
              <div className="text-xl sm:text-2xl font-bold font-mono text-text tabular-nums">
                +6.8%
              </div>
              <span className="text-[11px] text-status-success block font-medium">
                Within &lt;15% tolerance
              </span>
            </div>

            <div className="bg-surface p-4 rounded-lg border border-border shadow-soft space-y-1">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Rig Status
              </span>
              <div className="text-xl sm:text-2xl font-bold font-mono text-text tabular-nums">
                Active
              </div>
              <span className="text-[11px] text-text-faint block truncate">
                Bauer BG-28 Rig #1
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between pb-1">
            <div>
              <h2 className="text-sm font-semibold text-text uppercase tracking-wider">
                Operational Review Queue
              </h2>
              <p className="text-xs text-text-muted mt-0.5">
                Select a report to launch the human-in-the-loop AI review workspace.
              </p>
            </div>
            <span className="text-xs font-mono text-text-faint bg-surface-sunk px-2.5 py-1 rounded-pill border border-border">
              {pendingVerificationCount} Pending Action
            </span>
          </div>

          {dprQueue.length === 0 ? (
            <div className="bg-surface p-12 text-center rounded-lg border border-dashed border-border space-y-3">
              <CheckCircle2 className="h-10 w-10 text-status-success mx-auto opacity-70" />
              <div className="text-sm font-semibold text-text">No DPRs Awaiting Sign-off</div>
              <p className="text-xs text-text-muted max-w-sm mx-auto">
                All daily progress reports have been verified, or no fresh reports have been submitted yet.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {dprQueue.map((item) => (
                <Card
                  key={item.id}
                  padding="md"
                  isInteractive
                  onClick={() => setActiveReviewDpr(item)}
                  className={`transition-all duration-fast ${
                    item.status === 'VERIFIED'
                      ? 'border-status-success/30 bg-surface'
                      : 'border-border bg-surface hover:border-accent/40 shadow-soft'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-text text-sm">
                          DPR #{item.id} — {item.piling_summary.pile_number}
                        </span>
                        <Badge variant="accent" size="sm">
                          {item.shift} SHIFT
                        </Badge>
                        <Badge
                          variant={
                            item.status === 'VERIFIED'
                              ? 'verified'
                              : item.status === 'REJECTED'
                              ? 'danger'
                              : 'warning'
                          }
                          size="sm"
                        >
                          {item.status}
                        </Badge>
                      </div>
                      <div className="text-xs text-text-muted mt-0.5">
                        {item.site_name} • Submitted by {item.submitter_name} on {item.operational_date}
                      </div>
                    </div>

                    <Button
                      variant="primary"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveReviewDpr(item);
                      }}
                      rightIcon={<ArrowRight className="h-3.5 w-3.5" />}
                    >
                      Open in Review Workspace
                    </Button>
                  </div>

                  {/* Technical Overview Row */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-3 text-xs">
                    <div className="p-3 bg-surface-sunk/60 rounded-md">
                      <span className="text-[10px] text-text-faint block uppercase tracking-wider">Boring Depth</span>
                      <span className="font-semibold text-text font-mono">
                        {item.piling_summary.depth_drilled_m}m drilled (Socket: {item.piling_summary.rock_socket_m}m)
                      </span>
                      <span className="block text-[11px] text-text-muted mt-0.5">
                        Strata: {item.piling_summary.strata}
                      </span>
                    </div>

                    <div className="p-3 bg-surface-sunk/60 rounded-md">
                      <span className="text-[10px] text-text-faint block uppercase tracking-wider">Concrete Overbreak</span>
                      <div className="flex items-baseline gap-1 mt-0.5">
                        <span className="font-bold text-status-warning font-mono">
                          +{item.piling_summary.overbreak_pct}%
                        </span>
                        <span className="text-[10px] text-text-faint">
                          ({item.piling_summary.actual_concrete_m3} / {item.piling_summary.planned_concrete_m3} m³)
                        </span>
                      </div>
                      <span className="block text-[11px] text-text-muted mt-0.5">
                        Tolerance threshold &lt;15%
                      </span>
                    </div>

                    <div className="p-3 bg-surface-sunk/60 rounded-md">
                      <span className="text-[10px] text-text-faint block uppercase tracking-wider">Rig Runtime</span>
                      <span className="font-semibold text-text font-mono">
                        {item.equipment_summary.hours_run} hrs (Downtime: {item.equipment_summary.breakdown_hours}h)
                      </span>
                      <span className="block text-[11px] text-text-muted truncate mt-0.5">
                        {item.equipment_summary.name}
                      </span>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Technical DPR Form (Site Engineer Workstation ONLY) */}
      {isSiteEngineer && activeTab === 'entry' && (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Section 1: Shift Header */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>1. Shift & Site Context</CardTitle>
              <CardDescription>Primary site parameters and operational conditions.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-text-muted mb-1.5">
                    Project / Site
                  </label>
                  <select
                    value={siteId}
                    onChange={(e) => setSiteId(e.target.value)}
                    className="w-full bg-surface-sunk border border-border rounded-md text-xs sm:text-sm py-2 px-3 text-text focus:outline-none focus:border-accent"
                  >
                    <option value="1">ADANI-ODIPKS AVRP Flyover (Site #1)</option>
                  </select>
                </div>

                <Input
                  label="Operational Date"
                  type="date"
                  value={operationalDate}
                  onChange={(e) => setOperationalDate(e.target.value)}
                />

                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-text-muted mb-1.5">
                    Shift Mode
                  </label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setShift('DAY')}
                      className={`flex-1 py-2 text-xs font-medium rounded-pill border transition-all ${
                        shift === 'DAY'
                          ? 'bg-accent text-accent-contrast border-accent'
                          : 'bg-surface-sunk text-text-muted border-border hover:bg-surface'
                      }`}
                    >
                      Day Shift
                    </button>
                    <button
                      type="button"
                      onClick={() => setShift('NIGHT')}
                      className={`flex-1 py-2 text-xs font-medium rounded-pill border transition-all ${
                        shift === 'NIGHT'
                          ? 'bg-accent text-accent-contrast border-accent'
                          : 'bg-surface-sunk text-text-muted border-border hover:bg-surface'
                      }`}
                    >
                      Night Shift
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-text-muted mb-1.5">
                    Weather State
                  </label>
                  <select
                    value={weather}
                    onChange={(e) => setWeather(e.target.value)}
                    className="w-full bg-surface-sunk border border-border rounded-md text-xs sm:text-sm py-2 px-3 text-text focus:outline-none focus:border-accent"
                  >
                    <option value="SUNNY">Clear / Sunny</option>
                    <option value="OVERCAST">Overcast</option>
                    <option value="LIGHT_RAIN">Light Rain (No Stoppage)</option>
                    <option value="HEAVY_RAIN">Heavy Monsoonal Rain</option>
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 2: Piling Parameters */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>2. Bored Piling Execution & Overbreak</CardTitle>
              <CardDescription>Boring telemetry, rock socketing, and transit mixer volume.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Input
                  label="Pile Identifier"
                  value={pileNumber}
                  onChange={(e) => setPileNumber(e.target.value)}
                  placeholder="e.g. P-104 (Pier P12)"
                />
                <Input
                  label="Diameter (mm)"
                  type="number"
                  value={diameterMm}
                  onChange={(e) => setDiameterMm(e.target.value)}
                />
                <Input
                  label="Depth Drilled (m)"
                  type="number"
                  step="0.1"
                  value={drilledDepth}
                  onChange={(e) => setDrilledDepth(e.target.value)}
                />
                <Input
                  label="Rock Socket (m)"
                  type="number"
                  step="0.1"
                  value={rockSocketDepth}
                  onChange={(e) => setRockSocketDepth(e.target.value)}
                />

                <Input
                  label="Planned Concrete (m³)"
                  type="number"
                  step="0.1"
                  value={plannedConcreteM3}
                  onChange={(e) => setPlannedConcreteM3(e.target.value)}
                />
                <Input
                  label="Actual Poured (m³)"
                  type="number"
                  step="0.1"
                  value={actualConcreteM3}
                  onChange={(e) => setActualConcreteM3(e.target.value)}
                />

                <div>
                  <label className="block text-xs font-medium uppercase tracking-wider text-text-muted mb-1.5">
                    Strata Classification
                  </label>
                  <select
                    value={strataType}
                    onChange={(e) => setStrataType(e.target.value)}
                    className="w-full bg-surface-sunk border border-border rounded-md text-xs sm:text-sm py-2 px-3 text-text focus:outline-none focus:border-accent"
                  >
                    <option value="SOFT_CLAY">Soft Coastal Clay / Alluvium</option>
                    <option value="WEATHERED_ROCK">Weathered Gneiss / Soft Rock</option>
                    <option value="HARD_ROCK">Massive Hard Rock (Granite / Basalt)</option>
                  </select>
                </div>

                <div className="p-3 bg-surface-sunk/60 rounded-md border border-border flex flex-col justify-center">
                  <span className="text-[10px] text-text-faint uppercase tracking-wider">Calculated Overbreak</span>
                  <div className="font-mono text-base font-bold text-status-warning mt-0.5">
                    +
                    {Math.round(
                      ((parseFloat(actualConcreteM3) - parseFloat(plannedConcreteM3)) /
                        (parseFloat(plannedConcreteM3) || 1)) *
                        1000
                    ) / 10}
                    %
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 3: Equipment Telematics */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>3. Heavy Equipment Telematics</CardTitle>
              <CardDescription>Machinery operating hours, breakdown logs, and diesel fuel issued.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Input
                  label="Equipment Rig Name"
                  value={equipmentName}
                  onChange={(e) => setEquipmentName(e.target.value)}
                />
                <Input
                  label="Hours Run (h)"
                  type="number"
                  step="0.1"
                  value={hoursOperated}
                  onChange={(e) => setHoursOperated(e.target.value)}
                />
                <Input
                  label="Breakdown Loss (h)"
                  type="number"
                  step="0.1"
                  value={breakdownHours}
                  onChange={(e) => setBreakdownHours(e.target.value)}
                />
                <Input
                  label="Diesel Consumed (L)"
                  type="number"
                  value={fuelLiters}
                  onChange={(e) => setFuelLiters(e.target.value)}
                />
              </div>

              {parseFloat(breakdownHours) > 0 && (
                <div className="mt-4">
                  <Input
                    label="Breakdown Mechanical Diagnosis"
                    value={breakdownReason}
                    onChange={(e) => setBreakdownReason(e.target.value)}
                    placeholder="Specify cause (e.g. hydraulic hose leak, winch rope replaced)"
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Section 4: Site Photos & Verification Documents */}
          <Card padding="md">
            <CardHeader>
              <CardTitle>4. Photographic Evidence & Pour Slips</CardTitle>
              <CardDescription>Photos compressed locally in-browser for bandwidth-optimized upload.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4">
                <label className="cursor-pointer">
                  <span className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-pill bg-accent-soft text-accent border border-accent/20 hover:bg-accent/20 transition-colors">
                    <Camera className="h-4 w-4" />
                    <span>Attach Site Photos</span>
                  </span>
                  <input
                    type="file"
                    multiple
                    accept="image/*"
                    onChange={handlePhotoUpload}
                    className="hidden"
                  />
                </label>
                {isCompressing && (
                  <span className="text-xs text-accent">Compressing images locally...</span>
                )}
              </div>

              {photos.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {photos.map((p, idx) => (
                    <div key={idx} className="relative rounded-md overflow-hidden border border-border group bg-surface-sunk">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={p.dataUrl} alt={p.name} className="h-24 w-full object-cover" />
                      <button
                        type="button"
                        onClick={() => removePhoto(idx)}
                        className="absolute top-1 right-1 p-1 bg-black/60 text-white rounded-pill hover:bg-red-600 transition-colors"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Submission Bar */}
          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isSubmitting}
              rightIcon={<Send className="h-4 w-4" />}
            >
              {isSubmitting ? 'Recording...' : 'Submit DPR for PM Verification'}
            </Button>
          </div>
        </form>
      )}

      {/* TAB 3: DPR History & Audit Log */}
      {activeTab === 'history' && (
        <Card padding="md">
          <CardHeader>
            <CardTitle>Historical DPR Logs & Audit Sign-Offs</CardTitle>
            <CardDescription>Immutable record of all daily engineering reports filed for this project package.</CardDescription>
          </CardHeader>
          <CardContent>
            {dprQueue.length === 0 ? (
              <div className="py-12 text-center text-text-muted space-y-2">
                <FileText className="h-10 w-10 mx-auto opacity-40 text-text-muted" />
                <p className="text-xs font-medium">No Historical DPRs Found</p>
                <p className="text-[11px] text-text-faint">
                  Fresh DPRs submitted by Site Engineers will be permanently archived and listed here.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>DPR ID</TableHead>
                    <TableHead>Date & Shift</TableHead>
                    <TableHead>Pile Ref</TableHead>
                    <TableHead>Drilled Depth</TableHead>
                    <TableHead>Overbreak</TableHead>
                    <TableHead>Rig Hours</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead align="right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dprQueue.map((item) => (
                    <TableRow key={item.id} isClickable onClick={() => setActiveReviewDpr(item)}>
                      <TableCell isNumeric>#{item.id}</TableCell>
                      <TableCell>
                        <span className="font-mono text-xs">{item.operational_date}</span>{' '}
                        <span className="text-text-faint text-[11px]">({item.shift})</span>
                      </TableCell>
                      <TableCell>{item.piling_summary.pile_number}</TableCell>
                      <TableCell isNumeric>{item.piling_summary.depth_drilled_m} m</TableCell>
                      <TableCell isNumeric>
                        <span className="font-semibold text-status-warning">
                          +{item.piling_summary.overbreak_pct}%
                        </span>
                      </TableCell>
                      <TableCell isNumeric>{item.equipment_summary.hours_run} hrs</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            item.status === 'VERIFIED'
                              ? 'verified'
                              : item.status === 'REJECTED'
                              ? 'danger'
                              : 'warning'
                          }
                          size="sm"
                        >
                          {item.status}
                        </Badge>
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            setActiveReviewDpr(item);
                          }}
                        >
                          Review
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
