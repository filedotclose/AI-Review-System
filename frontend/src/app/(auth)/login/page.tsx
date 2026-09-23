'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import apiClient from '@/lib/api-client';
import { HardHat, Lock, Phone, Mail, AlertCircle, KeyRound } from 'lucide-react';
import axios from 'axios';

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [loginMode, setLoginMode] = useState<'PIN' | 'PASSWORD'>('PIN');
  const [phone, setPhone] = useState('9876543210');
  const [pin, setPin] = useState('1234');
  const [email, setEmail] = useState('engineer@odipks.com');
  const [password, setPassword] = useState('password123');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If already authenticated on this device, redirect to dashboard
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace('/brief');
    }
  }, [isAuthenticated, authLoading, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    const endpoint = loginMode === 'PIN' ? '/auth/pin-login' : '/auth/email-login';
    const payload =
      loginMode === 'PIN'
        ? { phone, pin }
        : { email, password };

    try {
      const res = await apiClient.post(endpoint, payload);
      if (res.data?.access_token) {
        await login(res.data.access_token, res.data.refresh_token);
        router.push('/brief');
      } else {
        setErrorMessage('Authentication server returned an unrecognized response.');
      }
    } catch (err: unknown) {
      console.error('Authentication failure:', err);
      let detailMessage: string | null = null;
      if (axios.isAxiosError(err)) {
        const detail = err.response?.data?.detail;
        if (typeof detail === 'string') {
          detailMessage = detail;
        } else if (Array.isArray(detail) && detail.length > 0) {
          detailMessage = detail[0]?.msg || 'Invalid submission format.';
        }
      }
      setErrorMessage(
        detailMessage || 'Invalid credentials or authentication server is unreachable. Please check connection.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const setFieldWorkerDemo = () => {
    setLoginMode('PIN');
    setPhone('9876543210');
    setPin('1234');
    setErrorMessage(null);
  };

  const setManagerDemo = () => {
    setLoginMode('PASSWORD');
    setEmail('engineer@odipks.com');
    setPassword('password123');
    setErrorMessage(null);
  };

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
            <HardHat className="h-6 w-6 animate-pulse" />
          </div>
          <p className="text-xs text-gray-500 font-medium">Checking authorization...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6 bg-white p-8 rounded-2xl shadow-sm border border-gray-200">
        <div className="text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm mb-3">
            <HardHat className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">ODIPKS Construction OS</h2>
          <p className="text-xs text-gray-500 mt-1">Field Engineering & Heavy Civil Operations</p>
        </div>

        {/* Tab switch: Field PIN vs Management Email */}
        <div className="flex rounded-lg bg-gray-100 p-1">
          <button
            type="button"
            onClick={() => setLoginMode('PIN')}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
              loginMode === 'PIN'
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            Field Worker (PIN)
          </button>
          <button
            type="button"
            onClick={() => setLoginMode('PASSWORD')}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all ${
              loginMode === 'PASSWORD'
                ? 'bg-white text-indigo-700 shadow-sm'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            Management (Email)
          </button>
        </div>

        {errorMessage && (
          <div className="rounded-lg bg-red-50 p-3 border border-red-200 text-xs text-red-800 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          {loginMode === 'PIN' ? (
            <>
              <div>
                <label className="block text-xs font-semibold text-gray-700">Mobile Phone Number</label>
                <div className="relative mt-1">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
                    <Phone className="h-4 w-4" />
                  </span>
                  <input
                    type="tel"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="10-digit mobile number"
                    className="block w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-medium"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Field PIN (4-6 digits)</label>
                <div className="relative mt-1">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
                    <Lock className="h-4 w-4" />
                  </span>
                  <input
                    type="password"
                    required
                    maxLength={6}
                    value={pin}
                    onChange={(e) => setPin(e.target.value)}
                    placeholder="••••"
                    className="block w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 tracking-widest font-bold"
                  />
                </div>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-xs font-semibold text-gray-700">Email Address</label>
                <div className="relative mt-1">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
                    <Mail className="h-4 w-4" />
                  </span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="engineer@odipks.com"
                    className="block w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700">Password</label>
                <div className="relative mt-1">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
                    <Lock className="h-4 w-4" />
                  </span>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="block w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 transition-colors cursor-pointer"
          >
            {isSubmitting ? 'Authenticating...' : 'Sign In to Dashboard'}
          </button>
        </form>

        {/* Quick Demo Fill Buttons */}
        <div className="pt-2 border-t border-gray-100">
          <div className="text-[11px] font-semibold text-gray-500 mb-2 flex items-center gap-1">
            <KeyRound className="h-3 w-3 text-gray-400" />
            Quick Demo Credentials:
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <button
              type="button"
              onClick={setFieldWorkerDemo}
              className="p-2 rounded-lg border border-gray-200 hover:border-indigo-400 bg-gray-50/70 hover:bg-indigo-50/50 text-left transition-colors cursor-pointer"
            >
              <div className="font-semibold text-gray-800">Field Worker</div>
              <div className="text-gray-500 font-mono text-[10px]">9876543210</div>
              <div className="text-gray-500 font-mono text-[10px]">PIN: 1234</div>
            </button>
            <button
              type="button"
              onClick={setManagerDemo}
              className="p-2 rounded-lg border border-gray-200 hover:border-indigo-400 bg-gray-50/70 hover:bg-indigo-50/50 text-left transition-colors cursor-pointer"
            >
              <div className="font-semibold text-gray-800">Site Manager</div>
              <div className="text-gray-500 font-mono text-[10px]">engineer@odipks.com</div>
              <div className="text-gray-500 font-mono text-[10px]">Pass: password123</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
