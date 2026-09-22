import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { addPendingRequest, syncPendingRequests, subscribeToQueue } from './offline-sync';

export class OfflineQueuedError extends Error {
  isOfflineQueued = true;
  queuedId?: string;

  constructor(message = 'Request saved offline and queued for automatic sync.') {
    super(message);
    this.name = 'OfflineQueuedError';
  }
}

export function isOfflineQueued(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false;
  const err = error as Record<string, unknown>;
  return (
    err.isOfflineQueued === true ||
    err.name === 'OfflineQueuedError' ||
    (typeof err.message === 'string' && (
      err.message.toLowerCase().includes('queued') ||
      err.message.toLowerCase().includes('offline')
    ))
  );
}

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  // Check if browser is strictly offline
  if (typeof window !== 'undefined' && typeof navigator !== 'undefined' && !navigator.onLine) {
    if (config.method && config.method.toLowerCase() !== 'get') {
      const queuedId = await addPendingRequest({
        url: config.url || '',
        method: config.method || 'post',
        body: config.data,
        headers: (config.headers as unknown) as Record<string, string>,
      });
      const offlineErr = new OfflineQueuedError();
      offlineErr.queuedId = queuedId;
      return Promise.reject(offlineErr);
    }
  }

  // Attach JWT Bearer token if available
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    // If request failed because of network connectivity drop or offline condition
    if (
      typeof window !== 'undefined' &&
      !error.response &&
      error.config &&
      error.config.method &&
      error.config.method.toLowerCase() !== 'get'
    ) {
      const queuedId = await addPendingRequest({
        url: error.config.url || '',
        method: error.config.method || 'post',
        body: error.config.data,
        headers: (error.config.headers as unknown) as Record<string, string>,
      });
      const offlineErr = new OfflineQueuedError('Network connection lost. Request queued for sync.');
      offlineErr.queuedId = queuedId;
      return Promise.reject(offlineErr);
    }

    return Promise.reject(error);
  }
);

export { syncPendingRequests, subscribeToQueue };
export default apiClient;
