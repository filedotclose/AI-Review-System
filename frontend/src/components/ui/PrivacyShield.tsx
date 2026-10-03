'use client';

import React, { useState, useEffect } from 'react';
import { Lock, Shield, ArrowRight } from 'lucide-react';
import Button from './Button';

interface PrivacyShieldProps {
  children: React.ReactNode;
  userRole?: string;
  userName?: string;
  idleTimeoutSeconds?: number;
  enableBlurOnTabSwitch?: boolean;
}

export const PrivacyShield: React.FC<PrivacyShieldProps> = ({
  children,
  userRole = 'Authorized User',
  userName = 'Operator',
  idleTimeoutSeconds = 300, // 5 minutes idle
  enableBlurOnTabSwitch = true,
}) => {
  const [isTabBlurred, setIsTabBlurred] = useState(false);
  const [isLocked, setIsLocked] = useState(false);
  const [pinInput, setPinInput] = useState('');
  const [pinError, setPinError] = useState(false);

  useEffect(() => {
    let idleTimer: NodeJS.Timeout;

    const startTimer = () => {
      clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        setIsLocked(true);
      }, idleTimeoutSeconds * 1000);
    };

    const handleActivity = () => {
      if (!isLocked) {
        startTimer();
      }
    };

    const handleWindowBlur = () => {
      if (enableBlurOnTabSwitch && !isLocked) {
        setIsTabBlurred(true);
      }
    };

    const handleWindowFocus = () => {
      setIsTabBlurred(false);
    };

    window.addEventListener('mousemove', handleActivity);
    window.addEventListener('keydown', handleActivity);
    window.addEventListener('click', handleActivity);
    window.addEventListener('blur', handleWindowBlur);
    window.addEventListener('focus', handleWindowFocus);

    startTimer();

    return () => {
      clearTimeout(idleTimer);
      window.removeEventListener('mousemove', handleActivity);
      window.removeEventListener('keydown', handleActivity);
      window.removeEventListener('click', handleActivity);
      window.removeEventListener('blur', handleWindowBlur);
      window.removeEventListener('focus', handleWindowFocus);
    };
  }, [idleTimeoutSeconds, enableBlurOnTabSwitch, isLocked]);

  const handleUnlock = (e: React.FormEvent) => {
    e.preventDefault();
    // Accept standard demo PIN '1234' or any 4+ digit entry or click unlock
    if (!pinInput || pinInput.length >= 4) {
      setIsLocked(false);
      setPinInput('');
      setPinError(false);
    } else {
      setPinError(true);
    }
  };

  return (
    <div className="relative min-h-screen">
      {/* Underlying Content with soft blur when tab inactive or locked */}
      <div
        className={`transition-all duration-base ${
          isTabBlurred || isLocked ? 'privacy-blur' : ''
        }`}
      >
        {children}
      </div>

      {/* Elegant Lock Screen Overlay (Section 6) */}
      {isLocked && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-bg/85 backdrop-blur-xl animate-in fade-in duration-base"
        >
          <div className="w-full max-w-sm bg-surface border border-border rounded-lg shadow-float p-8 text-center space-y-6">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-pill bg-accent-soft text-accent">
              <Lock className="h-5 w-5" />
            </div>

            <div>
              <h2 className="text-lg font-semibold text-text tracking-tight">
                Session Suspended for Confidentiality
              </h2>
              <p className="text-xs text-text-muted mt-1 leading-relaxed">
                Workplace was idle. Verify identity to resume session for{' '}
                <span className="font-semibold text-text">{userName}</span> (
                {userRole.replace('_', ' ')}).
              </p>
            </div>

            <form onSubmit={handleUnlock} className="space-y-4">
              <input
                type="password"
                maxLength={6}
                value={pinInput}
                onChange={(e) => {
                  setPinInput(e.target.value);
                  setPinError(false);
                }}
                placeholder="Enter PIN (e.g. 1234)"
                className="w-full text-center tracking-widest text-lg bg-surface-sunk border border-border rounded-md py-2.5 px-3 focus:outline-none focus:border-accent font-mono text-text"
              />
              {pinError && (
                <p className="text-xs text-status-danger">
                  Please enter your 4-digit security PIN.
                </p>
              )}

              <Button
                type="submit"
                variant="primary"
                size="md"
                className="w-full"
                rightIcon={<ArrowRight className="h-4 w-4" />}
              >
                Resume Workplace
              </Button>
            </form>

            <div className="text-[11px] text-text-faint flex items-center justify-center gap-1.5 pt-2 border-t border-border">
              <Shield className="h-3.5 w-3.5" />
              <span>Confidential Civil Infrastructure Gateway</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PrivacyShield;
