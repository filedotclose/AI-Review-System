'use client';

import React, { useEffect, useState } from 'react';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';
import { subscribeToQueue, syncPendingRequests } from '@/lib/offline-sync';

export function SyncStatusBadge() {
  const [status, setStatus] = useState<{ count: number; isSyncing: boolean; isOnline: boolean }>({
    count: 0,
    isSyncing: false,
    isOnline: true,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const unsubscribe = subscribeToQueue((newStatus) => {
      setStatus(newStatus);
    });
    return () => unsubscribe();
  }, []);

  const handleManualSync = async () => {
    if (!status.isOnline || status.isSyncing) return;
    try {
      await syncPendingRequests();
    } catch (err) {
      console.error('Manual sync failed:', err);
    }
  };

  return (
    <div className="flex items-center gap-2">
      {status.isOnline ? (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
          <Wifi className="h-3.5 w-3.5 text-green-600" />
          Online
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800 ring-1 ring-inset ring-amber-600/20">
          <WifiOff className="h-3.5 w-3.5 text-amber-600" />
          Offline Mode
        </span>
      )}

      {status.count > 0 && (
        <button
          type="button"
          onClick={handleManualSync}
          disabled={!status.isOnline || status.isSyncing}
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-all ${
            status.isOnline
              ? 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 ring-1 ring-inset ring-indigo-700/20 cursor-pointer'
              : 'bg-gray-100 text-gray-600 ring-1 ring-inset ring-gray-500/20 cursor-not-allowed'
          }`}
          title={status.isOnline ? 'Click to sync now' : 'Offline: items will sync when online'}
        >
          <RefreshCw className={`h-3 w-3 ${status.isSyncing ? 'animate-spin text-indigo-600' : ''}`} />
          <span>{status.count} queued</span>
          {status.isSyncing && <span className="text-[10px] text-indigo-500">Syncing...</span>}
        </button>
      )}
    </div>
  );
}

export default SyncStatusBadge;
