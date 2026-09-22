import { openDB, DBSchema, IDBPDatabase } from 'idb';
import axios from 'axios';

interface ConstructionDB extends DBSchema {
  pending_requests: {
    key: string;
    value: {
      id: string;
      url: string;
      method: string;
      body: unknown;
      headers: Record<string, string>;
      timestamp: number;
    };
  };
}

let dbPromise: Promise<IDBPDatabase<ConstructionDB>> | null = null;
let isSyncing = false;

if (typeof window !== 'undefined') {
  dbPromise = openDB<ConstructionDB>('construction-os-db', 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('pending_requests')) {
        db.createObjectStore('pending_requests', { keyPath: 'id' });
      }
    },
  });

  window.addEventListener('online', () => {
    syncPendingRequests();
    notifySubscribers();
  });
  window.addEventListener('offline', () => {
    notifySubscribers();
  });
}

type SyncStatus = { count: number; isSyncing: boolean; isOnline: boolean; };
const subscribers: ((status: SyncStatus) => void)[] = [];

export function subscribeToQueue(callback: (status: SyncStatus) => void) {
  subscribers.push(callback);
  getPendingRequests().then(reqs => callback({
      count: reqs.length,
      isSyncing,
      isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true
  }));
  return () => {
    const idx = subscribers.indexOf(callback);
    if (idx > -1) subscribers.splice(idx, 1);
  };
}

async function notifySubscribers() {
  const reqs = await getPendingRequests();
  const status: SyncStatus = {
      count: reqs.length,
      isSyncing,
      isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true
  };
  subscribers.forEach(cb => cb(status));
}

export async function addPendingRequest(request: { url: string; method: string; body: unknown; headers: Record<string, string> }) {
  if (!dbPromise) return undefined;
  const db = await dbPromise;
  const reqId = crypto.randomUUID();
  await db.put('pending_requests', {
    ...request,
    id: reqId,
    timestamp: Date.now(),
  });
  notifySubscribers();
  return reqId;
}

export async function getPendingRequests() {
  if (!dbPromise) return [];
  const db = await dbPromise;
  return await db.getAll('pending_requests');
}

export async function removePendingRequest(id: string) {
  if (!dbPromise) return;
  const db = await dbPromise;
  await db.delete('pending_requests', id);
  notifySubscribers();
}

export async function syncPendingRequests() {
  if (!dbPromise || isSyncing) return;
  
  const requests = await getPendingRequests();
  if (requests.length === 0) return;

  const token = localStorage.getItem('token');
  if (!token) return;

  isSyncing = true;
  notifySubscribers();

  requests.sort((a, b) => a.timestamp - b.timestamp);

  for (const req of requests) {
    try {
      await axios({
        url: req.url,
        method: req.method,
        data: req.body,
        headers: {
            ...req.headers,
            'Authorization': `Bearer ${token}`
        }
      });
      await removePendingRequest(req.id);
    } catch (error: unknown) {
      const err = error as { response?: { status: number } };
      if (err.response && err.response.status >= 400 && err.response.status < 500) {
        if (err.response.status === 401) {
            console.error('Token expired during sync');
            break;
        }
        await removePendingRequest(req.id);
      }
    }
  }
  
  isSyncing = false;
  notifySubscribers();
}
