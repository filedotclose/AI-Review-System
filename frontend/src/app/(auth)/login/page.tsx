'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import apiClient from '@/lib/api-client';
import { HardHat, Lock, Phone, Mail, AlertCircle, ShieldCheck, UserCheck, ChevronRight } from 'lucide-react';
import axios from 'axios';

type PredefinedUser = 'RAJESH' | 'VIKRAM' | 'CUSTOM';

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [selectedUser, setSelectedUser] = useState<PredefinedUser>('RAJESH');
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

  const selectUser = (user: PredefinedUser) => {
    setSelectedUser(user);
    setErrorMessage(null);
    if (user === 'RAJESH') {
      setLoginMode('PIN');
      setPhone('9876543210');
      setPin('1234');
    } else if (user === 'VIKRAM') {
      setLoginMode('PASSWORD');
      setEmail('engineer@odipks.com');
      setPassword('password123');
    } else {
      setPhone('');
      setPin('');
      setEmail('');
      setPassword('');
    }
  };

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

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
            <HardHat className="h-6 w-6 animate-pulse" />
          </div>
          <p className="text-xs text-gray-500 font-medium">Checking device authorization...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 py-10 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-lg space-y-6 bg-white p-7 sm:p-8 rounded-2xl shadow-sm border border-gray-200">
        <div className="text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm mb-3">
            <HardHat className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">ODIPKS Construction OS</h1>
          <p className="text-xs text-gray-500 mt-1">Select your account to start your session on this device</p>
        </div>

        {/* Step 1: Who is using the system? */}
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2.5">
            1. Who is using the software?
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {/* User 1: Rajesh Sharma */}
            <button
              type="button"
              onClick={() => selectUser('RAJESH')}
              className={`p-3 rounded-xl border text-left transition-all cursor-pointer relative ${
                selectedUser === 'RAJESH'
                  ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-500/20 shadow-xs'
                  : 'border-gray-200 hover:border-gray-300 bg-white hover:bg-gray-50/50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-xs">
                  RS
                </div>
                {selectedUser === 'RAJESH' && (
                  <UserCheck className="h-4 w-4 text-indigo-600" />
                )}
              </div>
              <div className="mt-2.5">
                <div className="text-sm font-bold text-gray-900 leading-tight">Rajesh Sharma</div>
                <div className="text-[11px] font-semibold text-indigo-700 mt-0.5">Site Engineer</div>
                <div className="text-[10px] text-gray-500 mt-1">Vadakara AVRP Flyover</div>
              </div>
            </button>

            {/* User 2: Vikram Mehta */}
            <button
              type="button"
              onClick={() => selectUser('VIKRAM')}
              className={`p-3 rounded-xl border text-left transition-all cursor-pointer relative ${
                selectedUser === 'VIKRAM'
                  ? 'border-indigo-600 bg-indigo-50/60 ring-2 ring-indigo-500/20 shadow-xs'
                  : 'border-gray-200 hover:border-gray-300 bg-white hover:bg-gray-50/50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-white font-bold text-xs">
                  VM
                </div>
                {selectedUser === 'VIKRAM' && (
                  <ShieldCheck className="h-4 w-4 text-blue-600" />
                )}
              </div>
              <div className="mt-2.5">
                <div className="text-sm font-bold text-gray-900 leading-tight">Vikram Mehta</div>
                <div className="text-[11px] font-semibold text-blue-700 mt-0.5">Project Manager</div>
                <div className="text-[10px] text-gray-500 mt-1">Management & Approvals</div>
              </div>
            </button>
          </div>

          <div className="mt-2 flex justify-end">
            <button
              type="button"
              onClick={() => selectUser('CUSTOM')}
              className={`text-[11px] font-medium transition-colors ${
                selectedUser === 'CUSTOM'
                  ? 'text-indigo-600 font-bold underline'
                  : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              {selectedUser === 'CUSTOM' ? '• Custom Account Active' : '+ Log in with other phone/email'}
            </button>
          </div>
        </div>

        {/* Step 2: Authentication Mode & Form */}
        <div className="pt-2 border-t border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <label className="text-xs font-semibold uppercase tracking-wider text-gray-500">
              2. Enter Credentials for {selectedUser === 'RAJESH' ? 'Rajesh Sharma' : selectedUser === 'VIKRAM' ? 'Vikram Mehta' : 'Account'}
            </label>
            <div className="flex rounded-lg bg-gray-100 p-0.5 text-[10px] font-semibold">
              <button
                type="button"
                onClick={() => setLoginMode('PIN')}
                className={`px-2 py-1 rounded-md transition-all ${
                  loginMode === 'PIN' ? 'bg-white text-indigo-700 shadow-xs' : 'text-gray-500'
                }`}
              >
                PIN
              </button>
              <button
                type="button"
                onClick={() => setLoginMode('PASSWORD')}
                className={`px-2 py-1 rounded-md transition-all ${
                  loginMode === 'PASSWORD' ? 'bg-white text-indigo-700 shadow-xs' : 'text-gray-500'
                }`}
              >
                Password
              </button>
            </div>
          </div>

          {errorMessage && (
            <div className="rounded-lg bg-red-50 p-3 mb-3 border border-red-200 text-xs text-red-800 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-3.5">
            {loginMode === 'PIN' ? (
              <>
                <div>
                  <label className="block text-xs font-semibold text-gray-700">Mobile Phone</label>
                  <div className="relative mt-1">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
                      <Phone className="h-4 w-4" />
                    </span>
                    <input
                      type="tel"
                      required
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="10-digit phone number"
                      className="block w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-medium"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-semibold text-gray-700">Security PIN</label>
                    <span className="text-[10px] text-gray-400">4-6 digits</span>
                  </div>
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
                      className="block w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 tracking-widest font-bold"
                    />
                  </div>
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-semibold text-gray-700">Work Email</label>
                  <div className="relative mt-1">
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400">
                      <Mail className="h-4 w-4" />
                    </span>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@odipks.com"
                      className="block w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
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
                      className="block w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                    />
                  </div>
                </div>
              </>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 transition-colors cursor-pointer"
            >
              <span>
                {isSubmitting
                  ? 'Authenticating Session...'
                  : selectedUser === 'RAJESH'
                  ? 'Sign In as Rajesh Sharma (Site Engineer)'
                  : selectedUser === 'VIKRAM'
                  ? 'Sign In as Vikram Mehta (Project Manager)'
                  : 'Sign In to Session'}
              </span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </form>
        </div>

        <div className="text-center text-[11px] text-gray-400 pt-1">
          Each device maintains an isolated, authenticated session on the cloud server.
        </div>
      </div>
    </div>
  );
}
