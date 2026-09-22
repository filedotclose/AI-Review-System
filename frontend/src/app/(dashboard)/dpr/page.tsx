'use client';

import React, { useState } from 'react';
import apiClient, { isOfflineQueued } from '@/lib/api-client';
import { compressImage, fileToDataUrl, formatFileSize } from '@/lib/image-compression';
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
} from 'lucide-react';

export default function DPRPage() {
  // General Shift State
  const [siteId, setSiteId] = useState('1');
  const [operationalDate, setOperationalDate] = useState(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [shift, setShift] = useState<'DAY' | 'NIGHT'>('DAY');
  const [weather, setWeather] = useState('SUNNY');
  const [submitterName, setSubmitterName] = useState('Rajesh Sharma (Site Engineer)');

  // Piling Progress State
  const [pileId, setPileId] = useState('1');
  const [pileNumber, setPileNumber] = useState('P-104 (Pier P12)');
  const [diameterMm, setDiameterMm] = useState('1000');
  const [drilledDepth, setDrilledDepth] = useState('18.5');
  const [cumulativeDepth, setCumulativeDepth] = useState('24.0');
  const [rockSocketDepth, setRockSocketDepth] = useState('3.2');
  const [strataType, setStrataType] = useState('WEATHERED_ROCK');
  const [casingDepth, setCasingDepth] = useState('6.0');
  const [casingType, setCasingType] = useState<'TEMPORARY' | 'PERMANENT'>('TEMPORARY');
  const [cageSections, setCageSections] = useState('2');
  const [cageWeightKg, setCageWeightKg] = useState('1450');
  const [plannedConcreteM3, setPlannedConcreteM3] = useState('14.5');
  const [actualConcreteM3, setActualConcreteM3] = useState('15.8');
  const [slumpMm, setSlumpMm] = useState('180');
  const [bentoniteDensity, setBentoniteDensity] = useState('1.05');

  // Equipment Shift State
  const [equipmentName, setEquipmentName] = useState('Bauer BG-28 Rotary Rig #1');
  const [hoursOperated, setHoursOperated] = useState('8.5');
  const [breakdownHours, setBreakdownHours] = useState('1.5');
  const [idleHours, setIdleHours] = useState('0.5');
  const [fuelLiters, setFuelLiters] = useState('180');
  const [breakdownReason, setBreakdownReason] = useState('Hydraulic pressure hose leak - replaced O-ring');

  // Delays & Notes
  const [delayReason, setDelayReason] = useState('Concrete transit mixer stuck in Vadakara bypass traffic');
  const [delayDurationHours, setDelayDurationHours] = useState('1.0');
  const [delayAction, setDelayAction] = useState('Re-routed backup mixer batch from plant #2');
  const [tomorrowsPlan, setTomorrowsPlan] = useState('Complete socketing on P-105; lower cage & cast concrete');

  // Manpower Headcounts
  const [pilingGangCount, setPilingGangCount] = useState('8');
  const [steelBendingCount, setSteelBendingCount] = useState('6');
  const [concretingCount, setConcretingCount] = useState('5');
  const [helpersCount, setHelpersCount] = useState('4');

  // Photos state
  const [photos, setPhotos] = useState<Array<{ name: string; size: number; compressedSize: number; dataUrl: string }>>([]);
  const [isCompressing, setIsCompressing] = useState(false);

  // Submission UI States (Loading, Success Toast, Error Recovery, Offline)
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successToast, setSuccessToast] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [offlineQueuedNotice, setOfflineQueuedNotice] = useState<string | null>(null);

  // Section collapse states
  const [expandPiling, setExpandPiling] = useState(true);
  const [expandEquipment, setExpandEquipment] = useState(true);
  const [expandManpower, setExpandManpower] = useState(true);

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

  // Submission Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSuccessToast(null);
    setErrorMessage(null);
    setOfflineQueuedNotice(null);

    // Build DPR Create Schema Payload
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
      setSuccessToast(`DPR #${res.data?.id || 'Recorded'} for ${operationalDate} (${shift}) submitted successfully!`);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        setOfflineQueuedNotice(
          `DPR Saved Offline! Your report for ${operationalDate} (${shift}) has been safely queued in IndexedDB and will automatically sync when connectivity returns.`
        );
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        const error = err as { response?: { data?: { detail?: string } }; message?: string };
        const detail = error.response?.data?.detail || error.message || 'Failed to submit DPR. Please check values and try again.';
        setErrorMessage(detail);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Daily Progress Report (DPR)</h1>
              <p className="text-xs sm:text-sm text-gray-500">Site Bored Piling, Equipment Shifts, Concrete & Delays</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            Shift: {shift}
          </span>
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-200">
            {operationalDate}
          </span>
        </div>
      </div>

      {/* Success Notification */}
      {successToast && (
        <div className="rounded-lg bg-green-50 p-4 border border-green-200 flex items-start gap-3 shadow-sm animate-fade-in">
          <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-green-900">Report Successfully Submitted</h3>
            <p className="text-xs text-green-700 mt-0.5">{successToast}</p>
          </div>
          <button
            onClick={() => setSuccessToast(null)}
            className="text-xs font-medium text-green-800 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Offline Queued Notification */}
      {offlineQueuedNotice && (
        <div className="rounded-lg bg-amber-50 p-4 border border-amber-200 flex items-start gap-3 shadow-sm animate-fade-in">
          <CloudOff className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-amber-900">Saved Offline in IndexedDB</h3>
            <p className="text-xs text-amber-800 mt-0.5">{offlineQueuedNotice}</p>
          </div>
          <button
            onClick={() => setOfflineQueuedNotice(null)}
            className="text-xs font-medium text-amber-800 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Error Recovery Banner */}
      {errorMessage && (
        <div className="rounded-lg bg-red-50 p-4 border border-red-200 flex items-start gap-3 shadow-sm">
          <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-900">Submission Error</h3>
            <p className="text-xs text-red-700 mt-0.5">{errorMessage}</p>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-xs font-medium text-red-800 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Section 1: Shift Header */}
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
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
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
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
                required
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700">Shift Type</label>
              <select
                value={shift}
                onChange={(e) => setShift(e.target.value as 'DAY' | 'NIGHT')}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-semibold text-indigo-700"
              >
                <option value="DAY">DAY SHIFT (08:00 - 20:00)</option>
                <option value="NIGHT">NIGHT SHIFT (20:00 - 08:00)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700">Weather Condition</label>
              <select
                value={weather}
                onChange={(e) => setWeather(e.target.value)}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              >
                <option value="SUNNY">Sunny / Clear</option>
                <option value="OVERCAST">Overcast / Cloudy</option>
                <option value="LIGHT_RAIN">Light Rain / Intermittent</option>
                <option value="HEAVY_RAIN">Heavy Monsoon Rain / Waterlogged</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-700">Submitting Field Engineer</label>
            <input
              type="text"
              value={submitterName}
              onChange={(e) => setSubmitterName(e.target.value)}
              className="mt-1 block w-full sm:max-w-md rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            />
          </div>
        </div>

        {/* Section 2: Bored Piling Progress */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div
            onClick={() => setExpandPiling(!expandPiling)}
            className="flex items-center justify-between p-5 cursor-pointer bg-gray-50/50 hover:bg-gray-50 border-b border-gray-100"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">2</span>
              <h2 className="text-base font-semibold text-gray-900">Foundation & Bored Piling Progress</h2>
            </div>
            {expandPiling ? <ChevronUp className="h-5 w-5 text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-400" />}
          </div>

          {expandPiling && (
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Pile ID / Number</label>
                  <select
                    value={pileId}
                    onChange={(e) => {
                      setPileId(e.target.value);
                      setPileNumber(e.target.options[e.target.selectedIndex].text);
                    }}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-semibold"
                  >
                    <option value="1">P-104 (Pier P12)</option>
                    <option value="2">P-105 (Pier P12)</option>
                    <option value="3">P-106 (Pier P13)</option>
                    <option value="4">P-107 (Pier P13)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Diameter (mm)</label>
                  <input
                    type="number"
                    min="400"
                    step="50"
                    value={diameterMm}
                    onChange={(e) => setDiameterMm(e.target.value)}
                    required
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                  <span className="text-[10px] text-gray-500">Min 400 mm required</span>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Depth Drilled Today (m)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={drilledDepth}
                    onChange={(e) => setDrilledDepth(e.target.value)}
                    required
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Cumulative Depth (m)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={cumulativeDepth}
                    onChange={(e) => setCumulativeDepth(e.target.value)}
                    required
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Rock Socket Depth Today (m)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={rockSocketDepth}
                    onChange={(e) => setRockSocketDepth(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Strata Type</label>
                  <select
                    value={strataType}
                    onChange={(e) => setStrataType(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="SOIL">Alluvial Soil / Silt</option>
                    <option value="CLAY">Soft / Stiff Clay</option>
                    <option value="SAND">Medium / Coarse Sand</option>
                    <option value="WEATHERED_ROCK">Weathered Gneiss / Rock</option>
                    <option value="HARD_ROCK">Hard Granite Rock</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Casing Depth (m)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={casingDepth}
                    onChange={(e) => setCasingDepth(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Casing Type</label>
                  <select
                    value={casingType}
                    onChange={(e) => setCasingType(e.target.value as 'TEMPORARY' | 'PERMANENT')}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  >
                    <option value="TEMPORARY">Temporary MS Casing</option>
                    <option value="PERMANENT">Permanent MS Liner</option>
                  </select>
                </div>
              </div>

              {/* Concrete & Reinforcement Sub-row */}
              <div className="border-t border-gray-100 pt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Cage Sections Lowered</label>
                  <input
                    type="number"
                    min="0"
                    value={cageSections}
                    onChange={(e) => setCageSections(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Cage Steel Weight (kg)</label>
                  <input
                    type="number"
                    min="0"
                    value={cageWeightKg}
                    onChange={(e) => setCageWeightKg(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Concrete Planned (m³)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={plannedConcreteM3}
                    onChange={(e) => setPlannedConcreteM3(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Concrete Actual Cast (m³)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    value={actualConcreteM3}
                    onChange={(e) => setActualConcreteM3(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                  {parseFloat(actualConcreteM3) > parseFloat(plannedConcreteM3) * 1.2 && (
                    <span className="text-[10px] text-amber-600 font-medium">Overbreak &gt; 20% alert</span>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Concrete Slump (mm)</label>
                  <input
                    type="number"
                    min="50"
                    max="250"
                    value={slumpMm}
                    onChange={(e) => setSlumpMm(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Bentonite Density (g/cc)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="1.0"
                    max="1.3"
                    value={bentoniteDensity}
                    onChange={(e) => setBentoniteDensity(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Section 3: Equipment & Fuel Register */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div
            onClick={() => setExpandEquipment(!expandEquipment)}
            className="flex items-center justify-between p-5 cursor-pointer bg-gray-50/50 hover:bg-gray-50 border-b border-gray-100"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">3</span>
              <h2 className="text-base font-semibold text-gray-900">Equipment Hours & Fuel Register</h2>
            </div>
            {expandEquipment ? <ChevronUp className="h-5 w-5 text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-400" />}
          </div>

          {expandEquipment && (
            <div className="p-5 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="lg:col-span-2">
                  <label className="block text-xs font-medium text-gray-700">Equipment Machine</label>
                  <input
                    type="text"
                    value={equipmentName}
                    onChange={(e) => setEquipmentName(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Hours Operated</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={hoursOperated}
                    onChange={(e) => setHoursOperated(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Fuel Issued (Liters)</label>
                  <input
                    type="number"
                    min="0"
                    value={fuelLiters}
                    onChange={(e) => setFuelLiters(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Breakdown Hours</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={breakdownHours}
                    onChange={(e) => setBreakdownHours(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Idle / Standby Hours</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={idleHours}
                    onChange={(e) => setIdleHours(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-gray-700">Breakdown Reason & Remedial Action</label>
                  <input
                    type="text"
                    value={breakdownReason}
                    onChange={(e) => setBreakdownReason(e.target.value)}
                    placeholder="Describe failure if breakdown hours > 0"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Section 4: Delays, Manpower & Site Photos */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <div
            onClick={() => setExpandManpower(!expandManpower)}
            className="flex items-center justify-between p-5 cursor-pointer bg-gray-50/50 hover:bg-gray-50 border-b border-gray-100"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold">4</span>
              <h2 className="text-base font-semibold text-gray-900">Manpower Muster, Delays & Photos</h2>
            </div>
            {expandManpower ? <ChevronUp className="h-5 w-5 text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-400" />}
          </div>

          {expandManpower && (
            <div className="p-5 space-y-5">
              {/* Manpower counts */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">Shift Labour Headcount</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Piling Operators/Riggers</label>
                    <input
                      type="number"
                      min="0"
                      value={pilingGangCount}
                      onChange={(e) => setPilingGangCount(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Steel Benders</label>
                    <input
                      type="number"
                      min="0"
                      value={steelBendingCount}
                      onChange={(e) => setSteelBendingCount(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Concreting Gang</label>
                    <input
                      type="number"
                      min="0"
                      value={concretingCount}
                      onChange={(e) => setConcretingCount(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700">Helpers / Unskilled</label>
                    <input
                      type="number"
                      min="0"
                      value={helpersCount}
                      onChange={(e) => setHelpersCount(e.target.value)}
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </div>

              {/* Delays & Tomorrow's Plan */}
              <div className="border-t border-gray-100 pt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Shift Delay Reason & Duration</label>
                  <input
                    type="text"
                    value={delayReason}
                    onChange={(e) => setDelayReason(e.target.value)}
                    placeholder="Delay description"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs text-gray-500">Duration:</span>
                    <input
                      type="number"
                      min="0"
                      step="0.5"
                      value={delayDurationHours}
                      onChange={(e) => setDelayDurationHours(e.target.value)}
                      className="w-20 rounded-lg border border-gray-300 px-2 py-1 text-sm shadow-sm"
                    />
                    <span className="text-xs text-gray-500">hours</span>
                  </div>

                  <div className="mt-2">
                    <label className="block text-xs font-medium text-gray-700">Action Taken / Remedial Measure</label>
                    <input
                      type="text"
                      value={delayAction}
                      onChange={(e) => setDelayAction(e.target.value)}
                      placeholder="e.g. Re-routed backup transit mixer"
                      className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-700">Tomorrow&apos;s Operational Target</label>
                  <textarea
                    rows={3}
                    value={tomorrowsPlan}
                    onChange={(e) => setTomorrowsPlan(e.target.value)}
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Site Photos with Canvas Compression */}
              <div className="border-t border-gray-100 pt-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 flex items-center gap-1.5">
                      <Camera className="h-4 w-4 text-indigo-600" />
                      Site Photos (Auto-compressed via Canvas)
                    </label>
                    <p className="text-[11px] text-gray-500">Photos are compressed client-side to &lt;300KB before upload or offline queueing</p>
                  </div>

                  <label className="cursor-pointer inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition-colors">
                    <Camera className="h-3.5 w-3.5" />
                    <span>Add Photos</span>
                    <input
                      type="file"
                      accept="image/*"
                      multiple
                      onChange={handlePhotoUpload}
                      className="hidden"
                    />
                  </label>
                </div>

                {isCompressing && (
                  <div className="text-xs text-indigo-600 font-medium animate-pulse py-2">
                    Compressing photo via HTML5 Canvas...
                  </div>
                )}

                {photos.length > 0 && (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                    {photos.map((photo, index) => (
                      <div key={index} className="relative group rounded-lg border border-gray-200 overflow-hidden bg-gray-50">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={photo.dataUrl}
                          alt={photo.name}
                          className="h-24 w-full object-cover"
                        />
                        <div className="p-1.5 bg-white text-[10px] text-gray-600 flex justify-between items-center">
                          <span className="truncate max-w-[100px]">{photo.name}</span>
                          <span className="text-gray-400 font-medium">{formatFileSize(photo.compressedSize)}</span>
                        </div>
                        <button
                          type="button"
                          onClick={() => removePhoto(index)}
                          className="absolute top-1 right-1 p-1 bg-red-600/80 hover:bg-red-600 text-white rounded-full transition-opacity opacity-90 group-hover:opacity-100"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-2">
          <button
            type="submit"
            disabled={isSubmitting || isCompressing}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 transition-all cursor-pointer"
          >
            {isSubmitting ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                <span>Submitting DPR...</span>
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                <span>Submit Daily Progress Report</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
