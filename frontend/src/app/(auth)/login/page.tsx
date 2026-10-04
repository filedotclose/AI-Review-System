'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import apiClient from '@/lib/api-client';
import {
  Compass,
  Lock,
  User,
  AlertCircle,
  ArrowRight,
  Shield,
  CheckCircle2,
} from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { ThemeSegmentedControl } from '@/components/ui/ThemeSegmentedControl';
import axios from 'axios';

interface DemoAccount {
  label: string;
  role: string;
  name: string;
  duty: string;
  identifier: string;
  secret: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    label: 'Site Engineer',
    role: 'SITE_ENGINEER',
    name: 'Rajesh Sharma',
    duty: 'Piling log entry & rig downtime',
    identifier: '9876543210',
    secret: '1234',
  },
  {
    label: 'Project Manager',
    role: 'PROJECT_MANAGER',
    name: 'Vikram Mehta',
    duty: 'AI Review & quality sign-off',
    identifier: 'engineer@odipks.com',
    secret: 'password123',
  },
  {
    label: 'Company Owner',
    role: 'OWNER',
    name: 'Pradeep K. Sharma',
    duty: 'Executive 8 AM brief & oversight',
    identifier: 'owner@odipks.com',
    secret: 'password123',
  },
  {
    label: 'Finance Head',
    role: 'FINANCE_HEAD',
    name: 'Ananya Sen',
    duty: 'Petty cash audits & disbursements',
    identifier: 'finance@odipks.com',
    secret: 'password123',
  },
  {
    label: 'Supervisor',
    role: 'SUPERVISOR',
    name: 'Sunil Varma',
    duty: 'Labour muster & ground claims',
    identifier: '9876543211',
    secret: '1234',
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [identifier, setIdentifier] = useState('engineer@odipks.com');
  const [secret, setSecret] = useState('password123');
  const [selectedRole, setSelectedRole] = useState<string>('PROJECT_MANAGER');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If already authenticated on this device, redirect to brief
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace('/brief');
    }
  }, [isAuthenticated, authLoading, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !secret.trim()) {
      setErrorMessage('Please enter your email/phone and password/PIN.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const isEmail = identifier.includes('@');
    const isNumericPin = /^\d{4,6}$/.test(secret);

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
    setSelectedRole(demo.role);
    setErrorMessage(null);
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center bg-bg px-4 sm:px-6 py-10 transition-colors duration-base select-none font-sans overflow-hidden">
      {/* Ambient background glow orbs for authentic glassmorphic light refraction */}
      <div className="absolute -top-32 -left-32 w-96 h-96 bg-accent/15 rounded-pill filter blur-[120px] pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-status-warning/15 rounded-pill filter blur-[120px] pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-accent/8 rounded-pill filter blur-[140px] pointer-events-none" />

      {/* Top Bar Floating Control with Prominent Theme Switcher */}
      <header className="absolute top-6 right-6 flex items-center gap-3 z-20">
        <ThemeSegmentedControl size="md" className="glass-panel" />
      </header>

      {/* Main Login Envelope */}
      <div className="w-full max-w-lg space-y-6 relative z-10">
        {/* Architectural Glassmorphic Portal Card */}
        <div className="glass-panel rounded-lg p-7 sm:p-9 space-y-6">
          {/* Header */}
          <div className="text-center space-y-2">
            <div className="inline-flex h-11 w-11 items-center justify-center rounded-md bg-accent-soft text-accent border border-accent/20 mb-1 shadow-soft">
              <Compass className="h-5 w-5" />
            </div>
            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-text">
              ODIPKS Construction OS
            </h1>
            <p className="text-xs text-text-muted leading-relaxed max-w-sm mx-auto">
              Precision AI Review & Heavy Civil Engineering Workspace
            </p>
          </div>

          {/* Quick Persona Selector: Clear, visual 1-click select */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-text-muted">
              <span>Select Active Role</span>
              <span className="text-text-faint font-normal">Click to fill</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {DEMO_ACCOUNTS.map((d) => {
                const isSelected = selectedRole === d.role;
                return (
                  <button
                    key={d.role}
                    type="button"
                    onClick={() => applyDemo(d)}
                    className={`flex flex-col text-left p-2.5 rounded-md transition-all duration-fast cursor-pointer ${
                      isSelected
                        ? 'bg-accent/15 text-text border border-accent ring-1 ring-accent/30 shadow-soft'
                        : 'glass-card border-border/60 text-text-muted hover:border-accent/40 hover:text-text'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-xs font-semibold text-text flex items-center gap-1.5">
                        {isSelected && <CheckCircle2 className="h-3 w-3 text-accent" />}
                        {d.label}
                      </span>
                      <span className="text-[10px] text-text-faint font-mono">
                        {d.name.split(' ')[0]}
                      </span>
                    </div>
                    <span className="text-[11px] text-text-muted mt-0.5 line-clamp-1">
                      {d.duty}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="rounded-md bg-status-danger-soft p-3 border border-status-danger/20 text-xs text-status-danger flex items-center gap-2.5">
              <AlertCircle className="h-4 w-4 shrink-0 text-status-danger" />
              <span className="leading-tight">{errorMessage}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleLogin} className="space-y-3.5">
            <Input
              label="Email or Mobile Identifier"
              type="text"
              required
              autoComplete="username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="name@odipks.com or 10-digit mobile"
              leftIcon={<User className="h-4 w-4" />}
            />

            <Input
              label="Security Password or PIN"
              isPassword
              required
              autoComplete="current-password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="Password or 4-digit PIN"
              leftIcon={<Lock className="h-4 w-4" />}
            />

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full"
                isLoading={isSubmitting}
                rightIcon={<ArrowRight className="h-4 w-4" />}
              >
                {isSubmitting ? 'Authenticating...' : 'Sign In to Workplace'}
              </Button>
            </div>
          </form>

          {/* Confidential Trust Footer */}
          <div className="pt-3 border-t border-border flex items-center justify-center gap-2 text-[11px] text-text-faint">
            <Shield className="h-3.5 w-3.5 text-accent" />
            <span>256-bit Encrypted Multi-Tenant Session • Vadakara Package</span>
          </div>
        </div>
      </div>
    </div>
  );
}
