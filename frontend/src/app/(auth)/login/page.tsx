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
} from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { ThemeSegmentedControl } from '@/components/ui/ThemeSegmentedControl';
import axios from 'axios';

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
      <div className="w-full max-w-md space-y-6 relative z-10">
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
