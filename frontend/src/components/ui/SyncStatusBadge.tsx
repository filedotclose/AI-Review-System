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
        <span className="inline-flex items-center gap-1.5 rounded-pill bg-status-success-soft px-2.5 py-1 text-xs font-medium text-status-success border border-status-success/20">
          <Wifi className="h-3 w-3" />
          <span>Online</span>
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 rounded-pill bg-status-warning-soft px-2.5 py-1 text-xs font-medium text-status-warning border border-status-warning/20">
          <WifiOff className="h-3 w-3" />
          <span>Offline Buffer</span>
        </span>
      )}

      {status.count > 0 && (
        <button
          type="button"
          onClick={handleManualSync}
          disabled={!status.isOnline || status.isSyncing}
          className={`inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 text-xs font-medium transition-all duration-fast ${
            status.isOnline
              ? 'bg-accent-soft text-accent hover:bg-accent/20 border border-accent/20 cursor-pointer'
              : 'bg-surface-sunk text-text-faint border border-border cursor-not-allowed'
          }`}
          title={status.isOnline ? 'Click to sync offline buffer now' : 'Offline: items will sync automatically upon reconnection'}
        >
          <RefreshCw className={`h-3 w-3 ${status.isSyncing ? 'animate-spin text-accent' : ''}`} />
          <span>{status.count} queued</span>
          {status.isSyncing && <span className="text-[10px] text-accent">Syncing...</span>}
        </button>
      )}
    </div>
  );
}

export default SyncStatusBadge;
