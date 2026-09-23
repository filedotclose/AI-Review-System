'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import apiClient from '@/lib/api-client';
import {
  HardHat,
  Users,
  Building2,
  Wallet,
  ShieldCheck,
  Lock,
  Phone,
  Mail,
  AlertCircle,
  UserCheck,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import axios from 'axios';

export type RoleType = 'SITE_ENGINEER' | 'SUPERVISOR' | 'PROJECT_MANAGER' | 'FINANCE_HEAD' | 'OWNER' | 'CUSTOM';

interface RolePersona {
  role: RoleType;
  title: string;
  name: string;
  scope: string;
  phone: string;
  email: string;
  pin: string;
  password: string;
  defaultMode: 'PIN' | 'PASSWORD';
  color: {
    bg: string;
    border: string;
    text: string;
    badge: string;
    iconBg: string;
  };
}

const ROLE_PERSONAS: RolePersona[] = [
  {
    role: 'SITE_ENGINEER',
    title: 'Site Engineer',
    name: 'Rajesh Sharma',
    scope: 'DPR, Piling & Concrete Logs',
    phone: '9876543210',
    email: 'rajesh@odipks.com',
    pin: '1234',
    password: 'password123',
    defaultMode: 'PIN',
    color: {
      bg: 'bg-indigo-50/60',
      border: 'border-indigo-600',
      text: 'text-indigo-700',
      badge: 'bg-indigo-100 text-indigo-800',
      iconBg: 'bg-indigo-600',
    },
  },
  {
    role: 'SUPERVISOR',
    title: 'Site Supervisor',
    name: 'Sunil Varma',
    scope: 'Labour & Gang Attendance',
    phone: '9876543211',
    email: 'supervisor@odipks.com',
    pin: '1234',
    password: 'password123',
    defaultMode: 'PIN',
    color: {
      bg: 'bg-amber-50/60',
      border: 'border-amber-600',
      text: 'text-amber-700',
      badge: 'bg-amber-100 text-amber-800',
      iconBg: 'bg-amber-600',
    },
  },
  {
    role: 'PROJECT_MANAGER',
    title: 'Project Manager',
    name: 'Vikram Mehta',
    scope: 'Operations, Machinery & Approvals',
    phone: '9811122233',
    email: 'engineer@odipks.com',
    pin: '9999',
    password: 'password123',
    defaultMode: 'PASSWORD',
    color: {
      bg: 'bg-blue-50/60',
      border: 'border-blue-600',
      text: 'text-blue-700',
      badge: 'bg-blue-100 text-blue-800',
      iconBg: 'bg-blue-600',
    },
  },
  {
    role: 'FINANCE_HEAD',
    title: 'Finance Head',
    name: 'Ananya Sen',
    scope: 'Petty Cash, Vouchers & Ledgers',
    phone: '9800000002',
    email: 'finance@odipks.com',
    pin: '1234',
    password: 'password123',
    defaultMode: 'PASSWORD',
    color: {
      bg: 'bg-emerald-50/60',
      border: 'border-emerald-600',
      text: 'text-emerald-700',
      badge: 'bg-emerald-100 text-emerald-800',
      iconBg: 'bg-emerald-600',
    },
  },
  {
    role: 'OWNER',
    title: 'Company Owner',
    name: 'Pradeep K. Sharma',
    scope: 'Executive Brief & System Analytics',
    phone: '9800000001',
    email: 'owner@odipks.com',
    pin: '1234',
    password: 'password123',
    defaultMode: 'PASSWORD',
    color: {
      bg: 'bg-purple-50/60',
      border: 'border-purple-600',
      text: 'text-purple-700',
      badge: 'bg-purple-100 text-purple-800',
      iconBg: 'bg-purple-600',
    },
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [selectedRole, setSelectedRole] = useState<RoleType>('SITE_ENGINEER');
  const [loginMode, setLoginMode] = useState<'PIN' | 'PASSWORD'>('PIN');
  const [phone, setPhone] = useState('9876543210');
  const [pin, setPin] = useState('1234');
  const [email, setEmail] = useState('rajesh@odipks.com');
  const [password, setPassword] = useState('password123');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If already authenticated on this device, redirect to dashboard
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace('/brief');
    }
  }, [isAuthenticated, authLoading, router]);

  const selectPersona = (p: RolePersona) => {
    setSelectedRole(p.role);
    setLoginMode(p.defaultMode);
    setPhone(p.phone);
    setEmail(p.email);
    setPin(p.pin);
    setPassword(p.password);
    setErrorMessage(null);
  };

  const selectCustom = () => {
    setSelectedRole('CUSTOM');
    setPhone('');
    setEmail('');
    setPin('');
    setPassword('');
    setErrorMessage(null);
  };

  const activePersona = ROLE_PERSONAS.find((p) => p.role === selectedRole);

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

  const renderRoleIcon = (role: RoleType) => {
    switch (role) {
      case 'SITE_ENGINEER':
        return <HardHat className="h-4 w-4 text-white" />;
      case 'SUPERVISOR':
        return <Users className="h-4 w-4 text-white" />;
      case 'PROJECT_MANAGER':
        return <Building2 className="h-4 w-4 text-white" />;
      case 'FINANCE_HEAD':
        return <Wallet className="h-4 w-4 text-white" />;
      case 'OWNER':
        return <ShieldCheck className="h-4 w-4 text-white" />;
      default:
        return <Sparkles className="h-4 w-4 text-white" />;
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
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-2xl space-y-6 bg-white p-6 sm:p-8 rounded-2xl shadow-sm border border-gray-200">
        <div className="text-center">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm mb-3">
            <HardHat className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">ODIPKS Construction OS</h1>
          <p className="text-xs text-gray-500 mt-1">
            Heavy Civil Operations • Select your system role to establish your session on this device
          </p>
        </div>

        {/* Step 1: Select Role in Database */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <label className="text-xs font-bold uppercase tracking-wider text-gray-700">
              1. Select System Role & Persona ({ROLE_PERSONAS.length} Roles Registered)
            </label>
            <button
              type="button"
              onClick={selectCustom}
              className={`text-xs font-semibold cursor-pointer transition-colors ${
                selectedRole === 'CUSTOM'
                  ? 'text-indigo-600 underline font-bold'
                  : 'text-gray-400 hover:text-gray-700'
              }`}
            >
              + Other Account
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
            {ROLE_PERSONAS.map((p) => {
              const isSelected = selectedRole === p.role;
              return (
                <button
                  key={p.role}
                  type="button"
                  onClick={() => selectPersona(p)}
                  className={`p-3 rounded-xl border text-left transition-all cursor-pointer relative ${
                    isSelected
                      ? `${p.color.border} ${p.color.bg} ring-2 ring-indigo-500/20 shadow-xs`
                      : 'border-gray-200 hover:border-gray-300 bg-white hover:bg-gray-50/50'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className={`flex h-7 w-7 items-center justify-center rounded-lg ${p.color.iconBg}`}>
                      {renderRoleIcon(p.role)}
                    </div>
                    {isSelected && (
                      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600 text-white">
                        <UserCheck className="h-3 w-3" />
                      </span>
                    )}
                  </div>
                  <div className="mt-2">
                    <div className="text-xs font-bold text-gray-900 leading-tight truncate">{p.name}</div>
                    <div className={`text-[11px] font-semibold mt-0.5 truncate ${p.color.text}`}>{p.title}</div>
                    <div className="text-[10px] text-gray-400 mt-1 line-clamp-1">{p.scope}</div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Step 2: Authentication Mode & Credentials */}
        <div className="pt-3 border-t border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <label className="text-xs font-bold uppercase tracking-wider text-gray-700">
              2. Authenticate as{' '}
              <span className="text-indigo-600">
                {activePersona ? `${activePersona.name} (${activePersona.title})` : 'Custom Account'}
              </span>
            </label>
            <div className="flex rounded-lg bg-gray-100 p-0.5 text-[11px] font-semibold">
              <button
                type="button"
                onClick={() => setLoginMode('PIN')}
                className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  loginMode === 'PIN' ? 'bg-white text-indigo-700 shadow-xs' : 'text-gray-500'
                }`}
              >
                PIN Login
              </button>
              <button
                type="button"
                onClick={() => setLoginMode('PASSWORD')}
                className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                  loginMode === 'PASSWORD' ? 'bg-white text-indigo-700 shadow-xs' : 'text-gray-500'
                }`}
              >
                Password Login
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
                  <label className="block text-xs font-semibold text-gray-700">Registered Phone Number</label>
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
                      className="block w-full rounded-lg border border-gray-300 pl-9 pr-3 py-2 text-sm shadow-xs focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-medium"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-semibold text-gray-700">Security PIN (4-6 digits)</label>
                    <span className="text-[10px] text-gray-400 font-mono">
                      {activePersona ? `Default PIN: ${activePersona.pin}` : '4-6 digits'}
                    </span>
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
                  <label className="block text-xs font-semibold text-gray-700">Registered Email Address</label>
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
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-semibold text-gray-700">Account Password</label>
                    <span className="text-[10px] text-gray-400 font-mono">
                      {activePersona ? `Default: ${activePersona.password}` : 'Password'}
                    </span>
                  </div>
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
                  : activePersona
                  ? `Sign In as ${activePersona.title} (${activePersona.name})`
                  : 'Sign In to Session'}
              </span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </form>
        </div>

        <div className="text-center text-[11px] text-gray-400 pt-1">
          ODIPKS Civil Construction ERP • Role-based access and device session security enabled
        </div>
      </div>
    </div>
  );
}
