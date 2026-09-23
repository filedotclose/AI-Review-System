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

export const getApiBaseUrl = (): string => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window !== 'undefined') {
    // When served via Nginx reverse proxy on standard ports (80/443), use clean relative path
    if (!window.location.port || window.location.port === '80' || window.location.port === '443') {
      return '/api/v1';
    }
    // Local development fallback when running frontend on separate dev port (e.g. :3000)
    return `http://${window.location.hostname}:8000/api/v1`;
  }
  return '/api/v1';
};

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

apiClient.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  if (typeof window !== 'undefined' && !process.env.NEXT_PUBLIC_API_URL) {
    config.baseURL = getApiBaseUrl();
  }

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

    // If session expired or unauthorized on protected routes
    if (typeof window !== 'undefined' && error.response?.status === 401) {
      const url = error.config?.url || '';
      if (!url.includes('/auth/pin-login') && !url.includes('/auth/email-login') && !url.includes('/auth/login')) {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login?reason=session_expired';
        }
      }
    }

    return Promise.reject(error);
  }
);

export { syncPendingRequests, subscribeToQueue };
export default apiClient;
