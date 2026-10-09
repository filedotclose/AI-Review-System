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
  HardHat,
  CheckCircle2,
} from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { ThemeSegmentedControl } from '@/components/ui/ThemeSegmentedControl';
import axios from 'axios';

interface SiteEngineerAccount {
  id: string;
  name: string;
  code: string;
  email: string;
  password: string;
  assignment: string;
}

const SITE_ENGINEERS: SiteEngineerAccount[] = [
  {
    id: 'engga',
    name: 'Site Engineer A',
    code: 'enggA',
    email: 'engga@odipks.com',
    password: 'password123',
    assignment: 'Pier P1–P4 (Piling)',
  },
  {
    id: 'enggb',
    name: 'Site Engineer B',
    code: 'enggB',
    email: 'enggb@odipks.com',
    password: 'password123',
    assignment: 'Pier P5–P8 (Superstructure)',
  },
  {
    id: 'enggc',
    name: 'Site Engineer C',
    code: 'enggC',
    email: 'enggc@odipks.com',
    password: 'password123',
    assignment: 'Well Foundations W1–W3',
  },
];

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();

  const [identifier, setIdentifier] = useState('');
  const [secret, setSecret] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // If already authenticated on this device, redirect to brief
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace('/brief');
    }
  }, [isAuthenticated, authLoading, router]);

  const fillEngineerCredentials = (eng: SiteEngineerAccount) => {
    setIdentifier(eng.code);
    setSecret(eng.password);
    setErrorMessage(null);
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedId = identifier.trim();
    const trimmedSecret = secret.trim();

    if (!trimmedId || !trimmedSecret) {
      setErrorMessage('Please enter your user ID/email and password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const isEmail = trimmedId.includes('@');
    const isNumericPin = /^\d{4,6}$/.test(trimmedSecret);

    const payload = {
      email: isEmail ? trimmedId.toLowerCase() : trimmedId,
      phone: !isEmail ? trimmedId : undefined,
      password: trimmedSecret,
      pin: isNumericPin ? trimmedSecret : undefined,
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
        detailMessage || 'Invalid credentials. Please verify your ID/email and password.'
      );
    } finally {
      setIsSubmitting(false);
    }
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
        <div className="glass-panel rounded-lg p-7 sm:p-8 space-y-5">
          {/* Header */}
          <div className="text-center space-y-1.5">
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

          {/* Site Engineer Quick Access / Login Info */}
          <div className="space-y-2 pt-1">
            <div className="flex items-center justify-between text-[11px] font-medium text-text-muted">
              <span className="flex items-center gap-1.5 uppercase tracking-wider font-semibold text-text">
                <HardHat className="h-3.5 w-3.5 text-accent" />
                Site Engineer Login Info
              </span>
              <span className="text-[10px] text-text-faint">1-Click Auto Fill</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {SITE_ENGINEERS.map((eng) => {
                const isActive =
                  identifier === eng.code ||
                  identifier.toLowerCase() === eng.email.toLowerCase();
                return (
                  <button
                    key={eng.id}
                    type="button"
                    onClick={() => fillEngineerCredentials(eng)}
                    className={`p-2.5 rounded-md text-left transition-all duration-fast cursor-pointer border ${
                      isActive
                        ? 'bg-accent/15 border-accent ring-1 ring-accent/30 text-text shadow-soft'
                        : 'glass-card border-border/70 text-text-muted hover:border-accent/40 hover:text-text'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-text flex items-center gap-1">
                        {isActive && <CheckCircle2 className="h-3 w-3 text-accent shrink-0" />}
                        {eng.name}
                      </span>
                    </div>
                    <div className="text-[10px] text-text-muted mt-1 truncate">
                      {eng.assignment}
                    </div>
                    <div className="mt-1.5 pt-1 border-t border-border/40 text-[10px] flex flex-col gap-0.5 font-mono">
                      <div className="flex items-center justify-between">
                        <span className="text-text-faint">ID:</span>
                        <span className="text-text font-bold">{eng.code}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-text-faint">Pass:</span>
                        <span className="text-accent font-semibold">{eng.password}</span>
                      </div>
                    </div>
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
          <form onSubmit={handleLogin} className="space-y-4">
            <Input
              label="User ID or Email"
              type="text"
              required
              autoComplete="username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="e.g. enggA, owner@odipks.com"
              leftIcon={<User className="h-4 w-4" />}
            />

            <Input
              label="Password"
              isPassword
              required
              autoComplete="current-password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              placeholder="Enter your account password"
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

            {/* Other Roles Quick Fills */}
            <div className="pt-1 flex flex-wrap items-center justify-center gap-1.5 text-[11px] text-text-muted">
              <span className="text-text-faint text-[10px]">Other Roles:</span>
              <button
                type="button"
                onClick={() => { setIdentifier('owner@odipks.com'); setSecret('password123'); setErrorMessage(null); }}
                className="px-2 py-0.5 rounded text-[10px] glass-card border border-border hover:border-accent/40 text-text-muted hover:text-text transition-colors"
              >
                Owner
              </button>
              <button
                type="button"
                onClick={() => { setIdentifier('pm@odipks.com'); setSecret('password123'); setErrorMessage(null); }}
                className="px-2 py-0.5 rounded text-[10px] glass-card border border-border hover:border-accent/40 text-text-muted hover:text-text transition-colors"
              >
                Project Manager
              </button>
              <button
                type="button"
                onClick={() => { setIdentifier('finance@odipks.com'); setSecret('password123'); setErrorMessage(null); }}
                className="px-2 py-0.5 rounded text-[10px] glass-card border border-border hover:border-accent/40 text-text-muted hover:text-text transition-colors"
              >
                Finance Head
              </button>
              <button
                type="button"
                onClick={() => { setIdentifier('supervisor@odipks.com'); setSecret('password123'); setErrorMessage(null); }}
                className="px-2 py-0.5 rounded text-[10px] glass-card border border-border hover:border-accent/40 text-text-muted hover:text-text transition-colors"
              >
                Supervisor
              </button>
            </div>
          </form>

          {/* Confidential Trust Footer */}
          <div className="pt-3 border-t border-border flex items-center justify-center gap-2 text-[11px] text-text-faint">
            <Shield className="h-3.5 w-3.5 text-accent" />
            <span>256-bit Encrypted Multi-Tenant Session • AWS Production</span>
          </div>
        </div>
      </div>
    </div>
  );
}
