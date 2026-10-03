'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { useTheme } from '@/lib/theme-context';
import apiClient from '@/lib/api-client';
import {
  Compass,
  Lock,
  User,
  AlertCircle,
  ArrowRight,
  Sun,
  Moon,
  Shield,
} from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
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
  const { resolvedTheme, toggleTheme } = useTheme();

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
    setErrorMessage(null);
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center bg-bg px-4 sm:px-6 py-12 transition-colors duration-base select-none">
      {/* Top Bar Floating Control */}
      <header className="absolute top-6 right-6 flex items-center gap-3">
        <button
          type="button"
          onClick={toggleTheme}
          title={`Switch to ${resolvedTheme === 'dark' ? 'Light' : 'Dark'} mode`}
          className="p-2 text-text-muted hover:text-text rounded-pill bg-surface border border-border shadow-soft transition-colors cursor-pointer"
        >
          {resolvedTheme === 'dark' ? (
            <Sun className="h-4 w-4 text-status-warning" />
          ) : (
            <Moon className="h-4 w-4 text-accent" />
          )}
        </button>
      </header>

      {/* Main Login Envelope */}
      <div className="w-full max-w-md space-y-6">
        {/* Architectural Portal Card */}
        <div className="bg-surface border border-border rounded-lg shadow-float p-8 sm:p-10 space-y-6">
          {/* Header */}
          <div className="text-center space-y-2">
            <div className="inline-flex h-11 w-11 items-center justify-center rounded-md bg-accent-soft text-accent border border-accent/20 mb-1">
              <Compass className="h-5 w-5" />
            </div>
            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-text">
              ODIPKS Review OS
            </h1>
            <p className="text-xs text-text-muted leading-relaxed">
              Confidential AI Review & Heavy Engineering Operations
            </p>
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
            <span>256-bit Encrypted Multi-Tenant Session</span>
          </div>
        </div>

        {/* Demo Fast-Switch Pill Group */}
        <div className="bg-surface/70 border border-border rounded-lg p-4 text-center space-y-2.5 backdrop-blur-sm">
          <div className="text-[11px] font-medium text-text-muted uppercase tracking-wider">
            Quick Persona Fill
          </div>
          <div className="flex flex-wrap items-center justify-center gap-1.5">
            {DEMO_ACCOUNTS.map((d) => (
              <button
                key={d.role}
                type="button"
                onClick={() => applyDemo(d)}
                className="px-2.5 py-1 text-xs rounded-pill bg-surface-sunk border border-border text-text hover:border-accent hover:text-accent transition-colors duration-fast font-medium cursor-pointer"
              >
                {d.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
