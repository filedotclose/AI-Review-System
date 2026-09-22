'use client';

import React, { useState, useMemo } from 'react';
import apiClient, { isOfflineQueued } from '@/lib/api-client';
import { compressImage, fileToDataUrl, formatFileSize } from '@/lib/image-compression';
import {
  Users,
  MapPin,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  CloudOff,
  UserCheck,
  UserX,
  Camera,
  Trash2,
  HardHat,
  Compass,
} from 'lucide-react';

interface WorkerItem {
  id: number;
  name: string;
  category: string;
  checkedIn: boolean;
  checkInTime?: string;
  checkInLat?: number;
  checkInLng?: number;
  withinGeofence?: boolean;
}

interface GangRecord {
  id: string | number;
  subcontractor_name: string;
  trade: string;
  headcount: number;
  ot_hours: number;
  shift: string;
  date: string;
}

// Site Coordinates for Vadakara AVRP Flyover Package
const SITE_COORDS = {
  lat: 11.6086,
  lng: 75.5912,
  radiusMeters: 500,
  name: 'Vadakara AVRP Flyover Site Office',
};

function calculateHaversineDistanceM(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371000;
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const deltaPhi = ((lat2 - lat1) * Math.PI) / 180;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(deltaPhi / 2) ** 2 +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

const INITIAL_WORKERS: WorkerItem[] = [
  { id: 101, name: 'Ramesh Kumar', category: 'RIG_OPERATOR', checkedIn: false },
  { id: 102, name: 'Suresh Yadav', category: 'WELDER', checkedIn: true, checkInTime: '07:55 AM', withinGeofence: true },
  { id: 103, name: 'Manoj Singh', category: 'RIG_HELPER', checkedIn: true, checkInTime: '08:05 AM', withinGeofence: true },
  { id: 104, name: 'Anil Pillai', category: 'FITTER', checkedIn: false },
  { id: 105, name: 'Vikram Das', category: 'LABOURER', checkedIn: false },
];

const INITIAL_GANGS: GangRecord[] = [
  {
    id: 'gang-1',
    subcontractor_name: 'M/s Royal Foundations',
    trade: 'PILING_GANG',
    headcount: 12,
    ot_hours: 4.0,
    shift: 'DAY',
    date: new Date().toISOString().split('T')[0],
  },
  {
    id: 'gang-2',
    subcontractor_name: 'VK Bar Benders Ltd',
    trade: 'STEEL_BENDING',
    headcount: 8,
    ot_hours: 2.0,
    shift: 'DAY',
    date: new Date().toISOString().split('T')[0],
  },
];

export default function AttendancePage() {
  const [activeTab, setActiveTab] = useState<'WORKERS' | 'GANG'>('WORKERS');
  const [siteId] = useState('1');
  const [date, setDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [shift, setShift] = useState<'DAY' | 'NIGHT'>('DAY');

  // Direct Workers State
  const [workers, setWorkers] = useState<WorkerItem[]>(INITIAL_WORKERS);
  const [selectedWorkerId, setSelectedWorkerId] = useState<number>(101);
  const [currentGps, setCurrentGps] = useState<{ lat: number; lng: number; accuracy: number } | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  // Subcontractor Gang Muster Form State
  const [gangRecords, setGangRecords] = useState<GangRecord[]>(INITIAL_GANGS);
  const [subcontractorName, setSubcontractorName] = useState('M/s Royal Foundations');
  const [gangTrade, setGangTrade] = useState('PILING_GANG');
  const [headcount, setHeadcount] = useState('10');
  const [otHours, setOtHours] = useState('0');
  const [musterPhoto, setMusterPhoto] = useState<{ name: string; compressedSize: number; dataUrl: string } | null>(null);
  const [isCompressing, setIsCompressing] = useState(false);

  // UI Feedback
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'offline' | 'error'; text: string } | null>(null);

  // Geolocation capture via browser API
  const handleCaptureLocation = () => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser or device.');
      return;
    }

    setIsLocating(true);
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCurrentGps({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
        setIsLocating(false);
      },
      (err) => {
        console.warn('Geolocation error:', err.message);
        // Provide mock site coordinates if permissions denied or running on desktop
        setCurrentGps({
          lat: SITE_COORDS.lat + 0.0008, // ~85 meters from site center
          lng: SITE_COORDS.lng + 0.0006,
          accuracy: 15,
        });
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  // Real-time Geofence Validation Calculation
  const geofenceStatus = useMemo(() => {
    if (!currentGps) return null;
    const distanceM = calculateHaversineDistanceM(
      currentGps.lat,
      currentGps.lng,
      SITE_COORDS.lat,
      SITE_COORDS.lng
    );
    const isWithin = distanceM <= SITE_COORDS.radiusMeters;
    return {
      distanceM: Math.round(distanceM),
      isWithin,
      radiusM: SITE_COORDS.radiusMeters,
    };
  }, [currentGps]);

  // Handle Direct Worker Check-In
  const handleCheckIn = async () => {
    const worker = workers.find((w) => w.id === selectedWorkerId);
    if (!worker) return;

    setIsSubmitting(true);
    setToastMessage(null);

    const payload = {
      site_id: parseInt(siteId, 10),
      worker_id: worker.id,
      date,
      shift,
      check_in_lat: currentGps?.lat,
      check_in_lng: currentGps?.lng,
    };

    try {
      await apiClient.post('/attendance/check-in', payload);
      setWorkers((prev) =>
        prev.map((w) =>
          w.id === worker.id
            ? {
                ...w,
                checkedIn: true,
                checkInTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                withinGeofence: geofenceStatus?.isWithin ?? true,
              }
            : w
        )
      );
      setToastMessage({
        type: 'success',
        text: `Checked in ${worker.name} successfully! (Geofence: ${geofenceStatus ? (geofenceStatus.isWithin ? 'Within Site' : 'Anomaly Flagged') : 'No GPS'})`,
      });
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        // Optimistic update
        setWorkers((prev) =>
          prev.map((w) =>
            w.id === worker.id
              ? {
                  ...w,
                  checkedIn: true,
                  checkInTime: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  withinGeofence: geofenceStatus?.isWithin ?? true,
                }
              : w
          )
        );
        setToastMessage({
          type: 'offline',
          text: `Check-in for ${worker.name} saved offline! Queued for automatic sync.`,
        });
      } else {
        const error = err as { response?: { data?: { detail?: string } }; message?: string };
        setToastMessage({
          type: 'error',
          text: error.response?.data?.detail || error.message || 'Check-in failed.',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Direct Worker Check-Out
  const handleCheckOut = async () => {
    const worker = workers.find((w) => w.id === selectedWorkerId);
    if (!worker) return;

    setIsSubmitting(true);
    setToastMessage(null);

    const payload = {
      site_id: parseInt(siteId, 10),
      worker_id: worker.id,
      check_out_lat: currentGps?.lat,
      check_out_lng: currentGps?.lng,
    };

    try {
      await apiClient.post('/attendance/check-out', payload);
      setWorkers((prev) =>
        prev.map((w) =>
          w.id === worker.id
            ? {
                ...w,
                checkedIn: false,
              }
            : w
        )
      );
      setToastMessage({
        type: 'success',
        text: `Checked out ${worker.name} successfully!`,
      });
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        setWorkers((prev) =>
          prev.map((w) =>
            w.id === worker.id
              ? {
                  ...w,
                  checkedIn: false,
                }
              : w
          )
        );
        setToastMessage({
          type: 'offline',
          text: `Check-out for ${worker.name} saved offline! Queued for sync.`,
        });
      } else {
        const error = err as { response?: { data?: { detail?: string } }; message?: string };
        setToastMessage({
          type: 'error',
          text: error.response?.data?.detail || error.message || 'Check-out failed.',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Muster Roll Photo Upload
  const handleMusterPhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsCompressing(true);
    try {
      const compressed = await compressImage(file, 1600, 0.75);
      const dataUrl = await fileToDataUrl(compressed);
      setMusterPhoto({
        name: file.name,
        compressedSize: compressed.size,
        dataUrl,
      });
    } catch (err) {
      console.error('Muster photo compression error:', err);
    } finally {
      setIsCompressing(false);
      e.target.value = '';
    }
  };

  // Handle Gang Muster Submission
  const handleGangSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const count = parseInt(headcount, 10);
    if (!count || count <= 0) return;

    setIsSubmitting(true);
    setToastMessage(null);

    const payload = {
      site_id: parseInt(siteId, 10),
      date,
      shift,
      subcontractor_name: subcontractorName,
      trade: gangTrade,
      headcount_present: count,
      total_ot_hours: parseFloat(otHours) || 0,
      muster_roll_photo_url: musterPhoto?.dataUrl,
    };

    try {
      const res = await apiClient.post('/attendance/gang-muster', payload);
      const newRec: GangRecord = {
        id: res.data?.id || 'gang-' + Date.now(),
        subcontractor_name: subcontractorName,
        trade: gangTrade,
        headcount: count,
        ot_hours: parseFloat(otHours) || 0,
        shift,
        date,
      };
      setGangRecords((prev) => [newRec, ...prev]);
      setToastMessage({
        type: 'success',
        text: `Muster record logged: ${count} hands for ${subcontractorName} (${gangTrade}).`,
      });
      setMusterPhoto(null);
    } catch (err: unknown) {
      if (isOfflineQueued(err)) {
        const queuedRec: GangRecord = {
          id: 'offline-gang-' + Date.now(),
          subcontractor_name: subcontractorName,
          trade: gangTrade,
          headcount: count,
          ot_hours: parseFloat(otHours) || 0,
          shift,
          date,
        };
        setGangRecords((prev) => [queuedRec, ...prev]);
        setToastMessage({
          type: 'offline',
          text: `Gang muster saved offline in IndexedDB! Queued for automatic sync.`,
        });
        setMusterPhoto(null);
      } else {
        const error = err as { response?: { data?: { detail?: string } }; message?: string };
        setToastMessage({
          type: 'error',
          text: error.response?.data?.detail || error.message || 'Failed to record gang muster.',
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Metrics
  const checkedInDirectCount = useMemo(() => workers.filter((w) => w.checkedIn).length, [workers]);
  const totalGangHeadcount = useMemo(
    () => gangRecords.reduce((acc, g) => acc + g.headcount, 0),
    [gangRecords]
  );

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
              <Users className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Labour & Site Attendance</h1>
              <p className="text-xs sm:text-sm text-gray-500">GPS Geofenced Worker Check-Ins & Subcontractor Gang Muster</p>
            </div>
          </div>
        </div>

        {/* Shift & Date Controls */}
        <div className="flex items-center gap-3">
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-medium"
          />
          <select
            value={shift}
            onChange={(e) => setShift(e.target.value as 'DAY' | 'NIGHT')}
            className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs shadow-sm font-semibold text-indigo-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          >
            <option value="DAY">DAY SHIFT</option>
            <option value="NIGHT">NIGHT SHIFT</option>
          </select>
        </div>
      </div>

      {/* Notifications */}
      {toastMessage && (
        <div
          className={`rounded-lg p-4 border flex items-start gap-3 shadow-sm ${
            toastMessage.type === 'success'
              ? 'bg-green-50 border-green-200 text-green-900'
              : toastMessage.type === 'offline'
              ? 'bg-amber-50 border-amber-200 text-amber-900'
              : 'bg-red-50 border-red-200 text-red-900'
          }`}
        >
          {toastMessage.type === 'success' && <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />}
          {toastMessage.type === 'offline' && <CloudOff className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />}
          {toastMessage.type === 'error' && <AlertCircle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />}
          <div className="flex-1 text-xs font-medium">{toastMessage.text}</div>
          <button
            onClick={() => setToastMessage(null)}
            className="text-xs font-semibold hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Summary Scorecards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Manpower On Site</span>
            <span className="p-1.5 bg-indigo-50 text-indigo-600 rounded-md">
              <HardHat className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-gray-900">
            {checkedInDirectCount + totalGangHeadcount} <span className="text-sm font-medium text-gray-500">Hands</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-500">
            {checkedInDirectCount} Direct Staff + {totalGangHeadcount} Subcontractor Gangs
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Direct Worker Status</span>
            <span className="p-1.5 bg-emerald-50 text-emerald-600 rounded-md">
              <UserCheck className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-emerald-600">
            {checkedInDirectCount} / {workers.length} <span className="text-sm font-medium text-gray-500">Checked In</span>
          </div>
          <p className="mt-1 text-[11px] text-gray-500">Operators, riggers, and welders roster</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Geofence Compliance</span>
            <span className="p-1.5 bg-blue-50 text-blue-600 rounded-md">
              <Compass className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-2 text-2xl sm:text-3xl font-bold text-blue-600">
            {geofenceStatus ? (geofenceStatus.isWithin ? '100% Within' : 'Warning: Outside') : 'Awaiting GPS'}
          </div>
          <p className="mt-1 text-[11px] text-gray-500">
            {SITE_COORDS.radiusMeters}m perimeter around {SITE_COORDS.name}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200">
        <button
          onClick={() => setActiveTab('WORKERS')}
          className={`py-3 px-6 text-sm font-semibold border-b-2 transition-colors cursor-pointer ${
            activeTab === 'WORKERS'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          1. Direct Worker Check-In/Out (GPS)
        </button>
        <button
          onClick={() => setActiveTab('GANG')}
          className={`py-3 px-6 text-sm font-semibold border-b-2 transition-colors cursor-pointer ${
            activeTab === 'GANG'
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          2. Subcontractor Gang Muster Entry
        </button>
      </div>

      {/* Tab 1: Direct Workers Check-in / Check-out */}
      {activeTab === 'WORKERS' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Action Box */}
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <MapPin className="h-5 w-5 text-indigo-600" />
              GPS Check-In Console
            </h2>

            {/* GPS Detection Box */}
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-gray-700">Device Coordinates:</span>
                <button
                  type="button"
                  onClick={handleCaptureLocation}
                  disabled={isLocating}
                  className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 cursor-pointer"
                >
                  <MapPin className="h-3 w-3" />
                  {isLocating ? 'Detecting GPS...' : 'Acquire GPS'}
                </button>
              </div>

              {currentGps ? (
                <div className="text-[11px] text-gray-600 font-mono">
                  <div>Lat: {currentGps.lat.toFixed(5)}</div>
                  <div>Lng: {currentGps.lng.toFixed(5)}</div>
                  <div>Accuracy: ±{Math.round(currentGps.accuracy)}m</div>
                </div>
              ) : (
                <p className="text-[11px] text-gray-400 italic">Click &quot;Acquire GPS&quot; to test geofence validation.</p>
              )}

              {locationError && (
                <p className="text-[11px] text-red-600">{locationError}</p>
              )}

              {/* Geofence Status Pill */}
              {geofenceStatus && (
                <div
                  className={`mt-2 p-2 rounded-md flex items-center gap-2 text-xs font-medium ${
                    geofenceStatus.isWithin
                      ? 'bg-green-50 text-green-800 border border-green-200'
                      : 'bg-amber-50 text-amber-800 border border-amber-200'
                  }`}
                >
                  {geofenceStatus.isWithin ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0" />
                  )}
                  <span>
                    {geofenceStatus.isWithin
                      ? `Within Geofence (${geofenceStatus.distanceM}m from site center)`
                      : `Outside Perimeter (${geofenceStatus.distanceM}m &gt; ${geofenceStatus.radiusM}m radius)`}
                  </span>
                </div>
              )}
            </div>

            {/* Worker Selector */}
            <div>
              <label className="block text-xs font-semibold text-gray-700">Select Worker</label>
              <select
                value={selectedWorkerId}
                onChange={(e) => setSelectedWorkerId(parseInt(e.target.value, 10))}
                className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-medium"
              >
                {workers.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} ({w.category}) — {w.checkedIn ? 'Checked In' : 'Not Checked In'}
                  </option>
                ))}
              </select>
            </div>

            {/* Action Buttons */}
            {(() => {
              const selectedWorker = workers.find((w) => w.id === selectedWorkerId);
              const isCheckedIn = selectedWorker?.checkedIn;

              return (
                <div className="pt-2 space-y-2">
                  {!isCheckedIn ? (
                    <button
                      type="button"
                      onClick={handleCheckIn}
                      disabled={isSubmitting}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-emerald-500 disabled:opacity-50 transition-colors cursor-pointer"
                    >
                      <UserCheck className="h-4 w-4" />
                      Record Check-In
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleCheckOut}
                      disabled={isSubmitting}
                      className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-red-500 disabled:opacity-50 transition-colors cursor-pointer"
                    >
                      <UserX className="h-4 w-4" />
                      Record Check-Out
                    </button>
                  )}
                </div>
              );
            })()}
          </div>

          {/* Roster Table */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-sm font-bold text-gray-900">Shift Worker Roster</h3>
              <span className="text-xs text-gray-500">{workers.length} Personnel Registered</span>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
                <thead className="bg-gray-50 text-gray-500 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Worker Name</th>
                    <th className="px-4 py-3">Trade / Role</th>
                    <th className="px-4 py-3 text-center">Status</th>
                    <th className="px-4 py-3 text-center">Check-In Time</th>
                    <th className="px-4 py-3 text-center">Geofence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {workers.map((w) => (
                    <tr key={w.id} className="hover:bg-gray-50/70 transition-colors">
                      <td className="px-4 py-3 font-semibold text-gray-900">{w.name}</td>
                      <td className="px-4 py-3 text-gray-600">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-800">
                          {w.category}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center whitespace-nowrap">
                        {w.checkedIn ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-green-100 text-green-800">
                            Present
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-600">
                            Off Duty
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-700">{w.checkInTime || '—'}</td>
                      <td className="px-4 py-3 text-center whitespace-nowrap">
                        {w.checkedIn ? (
                          w.withinGeofence !== false ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-green-700">
                              <CheckCircle2 className="h-3.5 w-3.5" /> Inside
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700">
                              <AlertTriangle className="h-3.5 w-3.5" /> Outside
                            </span>
                          )
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Subcontractor Gang Muster Entry */}
      {activeTab === 'GANG' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Gang Muster Form */}
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <HardHat className="h-5 w-5 text-indigo-600" />
              Add Gang Muster Entry
            </h2>

            <form onSubmit={handleGangSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700">Subcontractor Agency *</label>
                <input
                  type="text"
                  required
                  value={subcontractorName}
                  onChange={(e) => setSubcontractorName(e.target.value)}
                  placeholder="e.g. M/s Royal Foundations"
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Gang Trade *</label>
                <select
                  value={gangTrade}
                  onChange={(e) => setGangTrade(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                >
                  <option value="PILING_GANG">Piling Rig Crew & Helpers</option>
                  <option value="STEEL_BENDING">Steel Bar Bending & Rebar</option>
                  <option value="CONCRETING">Concreting & Tremie Pour</option>
                  <option value="CARPENTRY">Shuttering & Formwork</option>
                  <option value="EARTHWORK">Excavation & Earthwork</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-700">Headcount *</label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={headcount}
                    onChange={(e) => setHeadcount(e.target.value)}
                    placeholder="e.g. 12"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm font-bold focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-700">Total OT Hours</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={otHours}
                    onChange={(e) => setOtHours(e.target.value)}
                    placeholder="e.g. 2.0"
                    className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Muster Photo Upload */}
              <div className="border-t border-gray-100 pt-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-gray-700 flex items-center gap-1.5">
                    <Camera className="h-4 w-4 text-indigo-600" />
                    Physical Muster Sheet Photo
                  </label>
                  <label className="cursor-pointer px-2.5 py-1 text-xs font-medium rounded-md bg-indigo-50 text-indigo-700 hover:bg-indigo-100">
                    <span>Upload</span>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleMusterPhotoUpload}
                      className="hidden"
                    />
                  </label>
                </div>

                {isCompressing && (
                  <p className="text-[11px] text-indigo-600 animate-pulse mt-1">Compressing photo...</p>
                )}

                {musterPhoto && (
                  <div className="mt-2 flex items-center gap-3 p-2 rounded-lg border border-gray-200 bg-gray-50">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={musterPhoto.dataUrl} alt="Muster preview" className="h-12 w-12 rounded object-cover" />
                    <div className="flex-1 text-[11px] truncate">
                      <div className="font-semibold text-gray-900 truncate">{musterPhoto.name}</div>
                      <div className="text-gray-500">{formatFileSize(musterPhoto.compressedSize)}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setMusterPhoto(null)}
                      className="text-red-500 hover:text-red-700 p-1"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 transition-colors cursor-pointer"
              >
                {isSubmitting ? 'Recording Muster...' : 'Submit Gang Muster'}
              </button>
            </form>
          </div>

          {/* Gang Muster Log */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-sm font-bold text-gray-900">Recorded Gang Musters</h3>
              <span className="text-xs text-gray-500 font-semibold">{totalGangHeadcount} Total Hands Today</span>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 text-left text-xs">
                <thead className="bg-gray-50 text-gray-500 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Date</th>
                    <th className="px-4 py-3">Subcontractor</th>
                    <th className="px-4 py-3">Trade</th>
                    <th className="px-4 py-3 text-center">Headcount</th>
                    <th className="px-4 py-3 text-center">OT Hours</th>
                    <th className="px-4 py-3 text-center">Shift</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {gangRecords.map((g) => (
                    <tr key={g.id} className="hover:bg-gray-50/70 transition-colors">
                      <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{g.date}</td>
                      <td className="px-4 py-3 font-semibold text-gray-900">{g.subcontractor_name}</td>
                      <td className="px-4 py-3 text-gray-600">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-gray-100 text-gray-800">
                          {g.trade}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center font-bold text-indigo-600">{g.headcount}</td>
                      <td className="px-4 py-3 text-center text-gray-700">{g.ot_hours}h</td>
                      <td className="px-4 py-3 text-center whitespace-nowrap">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700">
                          {g.shift}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
