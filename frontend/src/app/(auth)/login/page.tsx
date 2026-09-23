'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import apiClient from '@/lib/api-client';
import { HardHat, Lock, User, AlertCircle, ArrowRight, Eye, EyeOff } from 'lucide-react';
import axios from 'axios';

interface DemoAccount {
  label: string;
  role: string;
  identifier: string;
  secret: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  { label: 'Site Engineer', role: 'SITE_ENGINEER', identifier: '9876543210', secret: '1234' },
  { label: 'Project Manager', role: 'PROJECT_MANAGER', identifier: 'engineer@odipks.com', secret: 'password123' },
  { label: 'Company Owner', role: 'OWNER', identifier: 'owner@odipks.com', secret: 'password123' },
  { label: 'Supervisor', role: 'SUPERVISOR', identifier: '9876543211', secret: '1234' },
  { label: 'Finance Head', role: 'FINANCE_HEAD', identifier: 'finance@odipks.com', secret: 'password123' },
];

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [identifier, setIdentifier] = useState('');
  const [secret, setSecret] = useState('');
  const [showSecret, setShowSecret] = useState(false);
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
    if (!identifier.trim() || !secret.trim()) {
      setErrorMessage('Please enter both your email/phone and password/PIN.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const isEmail = identifier.includes('@');
    const isNumericPin = /^\d{4,6}$/.test(secret);

    // Build unified login payload
    const payload = isEmail
      ? {
          email: identifier.trim().toLowerCase(),
          password: secret,
          pin: isNumericPin ? secret : undefined,
        }
      : {
          phone: identifier.trim().replace(/\s+/g, ''),
          password: secret,
          pin: isNumericPin ? secret : undefined,
        };

    try {
      const res = await apiClient.post('/auth/login', payload);
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
        detailMessage || 'Invalid credentials. Please verify your email/phone and password/PIN.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const applyDemo = (demo: DemoAccount) => {
    setIdentifier(demo.identifier);
    setSecret(demo.secret);
    setErrorMessage(null);
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6">
        {/* Main Clean Standard Login Card */}
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-gray-200">
          {/* Header & Branding */}
          <div className="text-center mb-6">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm mb-3">
              <HardHat className="h-6 w-6" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 tracking-tight">ODIPKS Construction OS</h1>
            <p className="text-xs text-gray-500 mt-1">
              Civil Infrastructure & Heavy Engineering Portal
            </p>
          </div>

          {/* Error Message */}
          {errorMessage && (
            <div className="rounded-lg bg-red-50 p-3 mb-4 border border-red-200 text-xs text-red-800 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Simple Dual-Input Form */}
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label htmlFor="identifier" className="block text-xs font-semibold text-gray-700 mb-1">
                Email or Mobile Number
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 pointer-events-none">
                  <User className="h-4 w-4" />
                </span>
                <input
                  id="identifier"
                  type="text"
                  required
                  autoComplete="username"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="name@odipks.com or 10-digit mobile"
                  className="block w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2.5 text-sm shadow-xs placeholder-gray-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-gray-900 font-medium"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label htmlFor="secret" className="block text-xs font-semibold text-gray-700">
                  Password or Security PIN
                </label>
              </div>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-400 pointer-events-none">
                  <Lock className="h-4 w-4" />
                </span>
                <input
                  id="secret"
                  type={showSecret ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  placeholder="Account password or 4-digit PIN"
                  className="block w-full rounded-lg border border-gray-300 pl-10 pr-10 py-2.5 text-sm shadow-xs placeholder-gray-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-gray-900 font-medium"
                />
                <button
                  type="button"
                  onClick={() => setShowSecret(!showSecret)}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 cursor-pointer"
                  title={showSecret ? 'Hide secret' : 'Show secret'}
                >
                  {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full mt-2 inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:opacity-50 transition-colors cursor-pointer"
            >
              <span>{isSubmitting ? 'Authenticating...' : 'Sign In'}</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>
        </div>

        {/* Discrete Demo / Testing Helper at the bottom */}
        <div className="bg-white/80 p-3.5 rounded-xl border border-gray-200/80 text-center">
          <div className="text-[11px] font-semibold text-gray-500 mb-2">
            Demo quick fill:
          </div>
          <div className="flex flex-wrap items-center justify-center gap-1.5">
            {DEMO_ACCOUNTS.map((d) => (
              <button
                key={d.role}
                type="button"
                onClick={() => applyDemo(d)}
                className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-gray-100 hover:bg-indigo-50 text-gray-700 hover:text-indigo-700 transition-colors cursor-pointer border border-gray-200 hover:border-indigo-200"
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>

        <p className="text-center text-[11px] text-gray-400">
          Protected civil engineering operating system. Unauthorized access strictly prohibited.
        </p>
      </div>
    </div>
  );
}
