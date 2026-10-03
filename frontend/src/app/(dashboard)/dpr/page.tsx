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
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Check,
  Ban,
  Clock,
  AlertTriangle,
  HardHat,
  Layers,
} from 'lucide-react';

interface PendingDPR {
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

const INITIAL_DPR_QUEUE: PendingDPR[] = [
  {
    id: 101,
    site_id: 1,
    site_name: 'Vadakara AVRP Flyover Package',
    operational_date: new Date().toISOString().split('T')[0],
    shift: 'DAY',
    submitter_name: 'Rajesh Sharma (Site Engineer)',
    status: 'SUBMITTED',
    piling_summary: {
      pile_number: 'P-104 (Pier P12)',
      diameter_mm: 1000,
      depth_drilled_m: 18.5,
      rock_socket_m: 3.2,
      strata: 'WEATHERED_ROCK',
      planned_concrete_m3: 14.5,
      actual_concrete_m3: 15.8,
      overbreak_pct: 8.9,
    },
    equipment_summary: {
      name: 'Bauer BG-28 Rotary Rig #1',
      hours_run: 8.5,
      breakdown_hours: 1.5,
      breakdown_reason: 'Hydraulic pressure hose leak - replaced O-ring',
    },
    manpower_total: 23,
    delays: 'Concrete transit mixer stuck in Vadakara bypass traffic (1.0h)',
  },
  {
    id: 100,
    site_id: 1,
    site_name: 'Vadakara AVRP Flyover Package',
    operational_date: new Date(Date.now() - 86400000).toISOString().split('T')[0],
    shift: 'NIGHT',
    submitter_name: 'Amit Patel (Site Engineer)',
    status: 'VERIFIED',
    piling_summary: {
      pile_number: 'P-103 (Pier P11)',
      diameter_mm: 1000,
      depth_drilled_m: 22.0,
      rock_socket_m: 4.1,
      strata: 'HARD_ROCK',
      planned_concrete_m3: 17.2,
      actual_concrete_m3: 18.0,
      overbreak_pct: 4.6,
    },
    equipment_summary: {
      name: 'Bauer BG-28 Rotary Rig #1',
      hours_run: 10.0,
      breakdown_hours: 0,
    },
    manpower_total: 19,
    verified_at: '2026-09-22 09:30 AM by Vikram Mehta (PM)',
  },
];

export default function DPRPage() {
  const { user } = useAuth();
  const isPMOrOwner = user?.role === 'PROJECT_MANAGER' || user?.role === 'OWNER';

  // Role Tab State
  const [activeTab, setActiveTab] = useState<'verification' | 'entry' | 'history'>(
    user?.role === 'PROJECT_MANAGER' ? 'verification' : 'entry'
  );

  useEffect(() => {
    if (user?.role === 'PROJECT_MANAGER') {
      setActiveTab('verification');
    } else if (user?.role === 'SITE_ENGINEER') {
      setActiveTab('entry');
    }
  }, [user?.role]);

  // Verification Queue State
  const [dprQueue, setDprQueue] = useState<PendingDPR[]>(INITIAL_DPR_QUEUE);

  // General Shift State
  const [siteId, setSiteId] = useState('1');
  const [operationalDate, setOperationalDate] = useState(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [shift, setShift] = useState<'DAY' | 'NIGHT'>('DAY');
  const [weather, setWeather] = useState('SUNNY');
  const submitterName = 'Rajesh Sharma (Site Engineer)';

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

  // Section collapse states
  const [expandPiling, setExpandPiling] = useState(true);
  const [expandEquipment, setExpandEquipment] = useState(true);

  // Handle Photo Upload with Client-Side Canvas Compression
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
            ? { ...d, status: 'VERIFIED', verified_at: `Signed off by ${user?.name || 'Project Manager'}` }
            : d
        )
      );
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
      setSuccessToast(`DPR #${dprId} flagged for revision.`);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } }; message?: string };
      setErrorMessage(error.response?.data?.detail || 'Failed to request revision.');
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
      setSuccessToast(`DPR #${res.data?.id || 'New'} submitted successfully and queued for PM Verification!`);
      // Add to local queue view
      const newDpr: PendingDPR = {
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
          `DPR for ${pileNumber} recorded offline on this device! Stored in IndexedDB and will auto-sync upon reconnection.`
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

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-gray-200 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
              <HardHat className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Daily Progress Report (DPR)</h1>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-gray-100 text-gray-700 border">
                  {user?.role?.replace('_', ' ') || 'Field Operations'}
                </span>
              </div>
              <p className="text-xs sm:text-sm text-gray-500">
                {isPMOrOwner
                  ? 'Project Manager Verification Center: Audit concrete overbreak, rig downtime, and verify reports'
                  : 'Site Engineer Workstation: Complete daily piling, equipment runtime, and delay logs'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Role Navigation Tabs */}
      <div className="flex border-b border-gray-200 bg-white px-4 rounded-t-xl">
        {isPMOrOwner && (
          <button
            onClick={() => setActiveTab('verification')}
            className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-bold transition-colors cursor-pointer ${
              activeTab === 'verification'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            <ShieldCheck className="h-4 w-4" />
            <span>PM Verification Queue</span>
            {pendingVerificationCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-100 text-amber-800 font-bold">
                {pendingVerificationCount}
              </span>
            )}
          </button>
        )}

        <button
          onClick={() => setActiveTab('entry')}
          className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-bold transition-colors cursor-pointer ${
            activeTab === 'entry'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileText className="h-4 w-4" />
          <span>{isPMOrOwner ? 'Technical Form Preview' : 'New DPR Entry'}</span>
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`flex items-center gap-2 py-3 px-4 border-b-2 text-xs font-bold transition-colors cursor-pointer ${
            activeTab === 'history'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Layers className="h-4 w-4" />
          <span>DPR History & Sign-Offs</span>
        </button>
      </div>

      {/* Notifications */}
      {successToast && (
        <div className="rounded-lg bg-green-50 p-4 border border-green-200 flex items-start gap-3 shadow-xs">
          <CheckCircle2 className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-xs font-semibold text-green-900">{successToast}</div>
          <button onClick={() => setSuccessToast(null)} className="text-xs text-green-800 hover:underline cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {offlineQueuedNotice && (
        <div className="rounded-lg bg-amber-50 p-4 border border-amber-200 flex items-start gap-3 shadow-xs">
          <CloudOff className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-xs font-medium text-amber-900">{offlineQueuedNotice}</div>
          <button onClick={() => setOfflineQueuedNotice(null)} className="text-xs text-amber-800 hover:underline cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="rounded-lg bg-red-50 p-4 border border-red-200 flex items-start gap-3 shadow-xs">
          <AlertCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-xs font-semibold text-red-900">{errorMessage}</div>
          <button onClick={() => setErrorMessage(null)} className="text-xs text-red-800 hover:underline cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {/* TAB 1: PM Verification Queue (For Project Manager & Owner) */}
      {isPMOrOwner && activeTab === 'verification' && (
        <div className="space-y-4">
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
                <span>DPR Review & Verification Queue</span>
                <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                  {pendingVerificationCount} awaiting sign-off
                </span>
              </h2>
              <p className="text-xs text-gray-500">
                Inspect technical boring depth, calculate concrete overbreak against theoretical cylinder, and approve or reject.
              </p>
            </div>
          </div>

          {dprQueue.map((item) => (
            <div
              key={item.id}
              className={`bg-white rounded-xl border p-5 shadow-xs space-y-4 transition-all ${
                item.status === 'VERIFIED' ? 'border-emerald-200 bg-emerald-50/20' : 'border-gray-200'
              }`}
            >
              {/* Card Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900 text-sm">DPR #{item.id}</span>
                    <span className="text-xs text-gray-500">• {item.site_name}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700">
                      {item.shift} SHIFT
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    Submitted by <span className="font-semibold text-gray-700">{item.submitter_name}</span> on{' '}
                    {item.operational_date}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                      item.status === 'VERIFIED'
                        ? 'bg-emerald-100 text-emerald-800'
                        : item.status === 'REJECTED'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
              </div>

              {/* Technical Details Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                {/* Piling Boring */}
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <div className="font-bold text-gray-800 mb-1 flex items-center gap-1.5">
                    <HardHat className="h-3.5 w-3.5 text-indigo-600" />
                    <span>Piling: {item.piling_summary.pile_number}</span>
                  </div>
                  <div className="space-y-1 text-gray-600">
                    <div>Drilled Today: <span className="font-bold text-gray-900">{item.piling_summary.depth_drilled_m}m</span> (Socket: {item.piling_summary.rock_socket_m}m)</div>
                    <div>Strata: <span className="font-semibold text-gray-800">{item.piling_summary.strata}</span></div>
                    <div>Diameter: {item.piling_summary.diameter_mm} mm</div>
                  </div>
                </div>

                {/* Concrete Overbreak Guard */}
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <div className="font-bold text-gray-800 mb-1 flex items-center gap-1.5">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                    <span>Concrete Overbreak</span>
                  </div>
                  <div className="space-y-1 text-gray-600">
                    <div>Planned: {item.piling_summary.planned_concrete_m3} m³</div>
                    <div>Actual Poured: <span className="font-bold text-gray-900">{item.piling_summary.actual_concrete_m3} m³</span></div>
                    <div className="flex items-center gap-1">
                      <span>Variance:</span>
                      <span className="font-bold text-amber-700 bg-amber-50 px-1.5 py-0.2 rounded border border-amber-200">
                        +{item.piling_summary.overbreak_pct}%
                      </span>
                      <span className="text-[10px] text-gray-400">(Tolerance &lt;15%)</span>
                    </div>
                  </div>
                </div>

                {/* Equipment & Delays */}
                <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <div className="font-bold text-gray-800 mb-1 flex items-center gap-1.5">
                    <Clock className="h-3.5 w-3.5 text-blue-600" />
                    <span>Rig Runtime & Delays</span>
                  </div>
                  <div className="space-y-1 text-gray-600">
                    <div>{item.equipment_summary.name}</div>
                    <div>Run: {item.equipment_summary.hours_run}h | Downtime: {item.equipment_summary.breakdown_hours}h</div>
                    {item.delays && <div className="text-[11px] text-amber-700 truncate font-medium">{item.delays}</div>}
                  </div>
                </div>
              </div>

              {/* Action Buttons for PM */}
              <div className="flex items-center justify-between pt-2 border-t border-gray-100">
                <div className="text-xs text-gray-500 font-medium">
                  {item.verified_at ? (
                    <span className="text-emerald-700 font-semibold flex items-center gap-1">
                      <Check className="h-3.5 w-3.5" />
                      {item.verified_at}
                    </span>
                  ) : (
                    <span>Pending review by Project Manager</span>
                  )}
                </div>

                {item.status === 'SUBMITTED' && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleRejectDpr(item.id)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 border border-red-200 bg-red-50 text-red-700 rounded-lg text-xs font-bold hover:bg-red-100 transition-colors cursor-pointer"
                    >
                      <Ban className="h-3.5 w-3.5" />
                      <span>Request Revision</span>
                    </button>
                    <button
                      onClick={() => handleVerifyDpr(item.id)}
                      className="inline-flex items-center gap-1 px-4 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-bold hover:bg-emerald-700 transition-colors shadow-xs cursor-pointer"
                    >
                      <Check className="h-3.5 w-3.5" />
                      <span>Verify & Sign Off</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 2: Technical DPR Form (Site Engineer Workstation) */}
      {(activeTab === 'entry' || !isPMOrOwner) && (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Section 1: Shift Header */}
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">1</span>
              Shift & Site Header
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-700">Project / Site</label>
                <select
                  value={siteId}
                  onChange={(e) => setSiteId(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="1">ADANI-ODIPKS AVRP Flyover (Site #1)</option>
                  <option value="2">Vadakara Bypass Bridge Package (Site #2)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700">Operational Date</label>
                <input
                  type="date"
                  value={operationalDate}
                  onChange={(e) => setOperationalDate(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700">Shift</label>
                <div className="mt-1 grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setShift('DAY')}
                    className={`py-2 text-xs font-semibold rounded-lg border transition-colors ${
                      shift === 'DAY'
                        ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                        : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Day Shift
                  </button>
                  <button
                    type="button"
                    onClick={() => setShift('NIGHT')}
                    className={`py-2 text-xs font-semibold rounded-lg border transition-colors ${
                      shift === 'NIGHT'
                        ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                        : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Night Shift
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700">Weather Condition</label>
                <select
                  value={weather}
                  onChange={(e) => setWeather(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="SUNNY">Sunny / Clear Sky</option>
                  <option value="OVERCAST">Overcast / Cloudy</option>
                  <option value="LIGHT_RAIN">Light Rain / Intermittent</option>
                  <option value="HEAVY_RAIN">Heavy Monsoonal Downpour</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Piling Boring & Concreting */}
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpandPiling(!expandPiling)}>
              <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">2</span>
                Piling Boring & Concreting Log
              </h2>
              {expandPiling ? <ChevronUp className="h-5 w-5 text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-400" />}
            </div>

            {expandPiling && (
              <div className="space-y-4 pt-2 border-t border-gray-100">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Pile ID / Pier Location</label>
                    <input
                      type="text"
                      value={pileNumber}
                      onChange={(e) => setPileNumber(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700">Pile Diameter (mm) *</label>
                    <input
                      type="number"
                      required
                      min="400"
                      value={diameterMm}
                      onChange={(e) => setDiameterMm(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs font-semibold"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700">Strata Encountered</label>
                    <select
                      value={strataType}
                      onChange={(e) => setStrataType(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                    >
                      <option value="SOIL">Top Soil / Alluvial Clay</option>
                      <option value="CLAY">Stiff Clay</option>
                      <option value="SAND">Medium Dense Sand</option>
                      <option value="WEATHERED_ROCK">Weathered Sedimentary Rock</option>
                      <option value="HARD_ROCK">Hard Granite Rock Core</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Drilled Depth Today (m) *</label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={drilledDepth}
                      onChange={(e) => setDrilledDepth(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs font-semibold"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700">Rock Socket Depth (m)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={rockSocketDepth}
                      onChange={(e) => setRockSocketDepth(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700">Planned Concrete (m³)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={plannedConcreteM3}
                      onChange={(e) => setPlannedConcreteM3(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700">Actual Poured (m³) *</label>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={actualConcreteM3}
                      onChange={(e) => setActualConcreteM3(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs font-bold text-gray-900"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Section 3: Equipment & Rig Run Hours */}
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpandEquipment(!expandEquipment)}>
              <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">3</span>
                Equipment Utilization & Breakdown Log
              </h2>
              {expandEquipment ? <ChevronUp className="h-5 w-5 text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-400" />}
            </div>

            {expandEquipment && (
              <div className="space-y-4 pt-2 border-t border-gray-100">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Equipment Name</label>
                    <input
                      type="text"
                      value={equipmentName}
                      onChange={(e) => setEquipmentName(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700">Hours Operated (h)</label>
                    <input
                      type="number"
                      step="0.5"
                      value={hoursOperated}
                      onChange={(e) => setHoursOperated(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700">Breakdown (h)</label>
                    <input
                      type="number"
                      step="0.5"
                      value={breakdownHours}
                      onChange={(e) => setBreakdownHours(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs text-red-600 font-semibold"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-700">Diesel Issued (Liters)</label>
                    <input
                      type="number"
                      value={fuelLiters}
                      onChange={(e) => setFuelLiters(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-xs"
                    />
                  </div>
                </div>

                {parseFloat(breakdownHours) > 0 && (
                  <div>
                    <label className="block text-xs font-medium text-red-700">Breakdown Reason & Mechanic Action</label>
                    <input
                      type="text"
                      value={breakdownReason}
                      onChange={(e) => setBreakdownReason(e.target.value)}
                      placeholder="e.g. Hydraulic pressure hose leak - replaced O-ring"
                      className="mt-1 block w-full rounded-lg border border-red-300 bg-red-50/50 px-3 py-2 text-sm shadow-xs text-red-900"
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Section 4: Photo Attachments with Canvas Compression */}
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-gray-900 flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">4</span>
              Site Photos (Progress & Spoil Inspection)
            </h2>

            <div className="flex items-center gap-4">
              <label className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-bold rounded-lg cursor-pointer hover:bg-indigo-100 transition-colors shadow-xs">
                <Camera className="h-4 w-4" />
                <span>Upload Photos</span>
                <input type="file" multiple accept="image/*" onChange={handlePhotoUpload} className="hidden" />
              </label>
              {isCompressing && <span className="text-xs text-indigo-600 animate-pulse">Compressing high-res photos...</span>}
            </div>

            {photos.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                {photos.map((p, idx) => (
                  <div key={idx} className="relative group border rounded-lg overflow-hidden bg-gray-100 aspect-video">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={p.dataUrl} alt={p.name} className="w-full h-full object-cover" />
                    <button
                      type="button"
                      onClick={() => removePhoto(idx)}
                      className="absolute top-1 right-1 p-1 bg-black/60 text-white rounded hover:bg-red-600 transition-colors cursor-pointer"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Submit Button */}
          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white text-sm font-bold rounded-lg shadow-xs hover:bg-indigo-700 disabled:opacity-50 transition-colors cursor-pointer"
            >
              <Send className="h-4 w-4" />
              <span>{isSubmitting ? 'Submitting DPR...' : 'Submit DPR for Verification'}</span>
            </button>
          </div>
        </form>
      )}

      {/* TAB 3: DPR History */}
      {activeTab === 'history' && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
          <div className="p-4 border-b border-gray-100">
            <h2 className="text-base font-bold text-gray-900">Historical DPR Submissions</h2>
            <p className="text-xs text-gray-500">Record of daily progress reports and their verification status</p>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
              <thead className="bg-gray-50 text-gray-500 font-semibold uppercase">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Shift</th>
                  <th className="px-4 py-3">Pile / Pier</th>
                  <th className="px-4 py-3">Drilled (m)</th>
                  <th className="px-4 py-3">Concrete (m³)</th>
                  <th className="px-4 py-3 text-center">Status</th>
                  <th className="px-4 py-3 text-right">Sign-Off</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 bg-white">
                {dprQueue.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50/70">
                    <td className="px-4 py-3 font-bold text-gray-900">#{item.id}</td>
                    <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{item.operational_date}</td>
                    <td className="px-4 py-3 font-semibold text-gray-800">{item.shift}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{item.piling_summary.pile_number}</td>
                    <td className="px-4 py-3 text-gray-800 font-bold">{item.piling_summary.depth_drilled_m}m</td>
                    <td className="px-4 py-3 text-gray-800 font-bold">
                      {item.piling_summary.actual_concrete_m3} m³
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          item.status === 'VERIFIED'
                            ? 'bg-emerald-100 text-emerald-800'
                            : item.status === 'REJECTED'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-500">
                      {item.verified_at || 'Pending PM Verification'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
