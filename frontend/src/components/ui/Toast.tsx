'use client';

import React, { useEffect } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export interface ToastProps {
  message: string;
  type?: 'success' | 'warning' | 'error' | 'info';
  onDismiss: () => void;
  durationMs?: number;
}

export const Toast: React.FC<ToastProps> = ({
  message,
  type = 'info',
  onDismiss,
  durationMs = 4000,
}) => {
  useEffect(() => {
    if (durationMs > 0) {
      const timer = setTimeout(onDismiss, durationMs);
      return () => clearTimeout(timer);
    }
  }, [durationMs, onDismiss]);

  const typeConfig = {
    success: {
      icon: <CheckCircle2 className="h-4 w-4 text-status-success shrink-0" />,
      border: 'border-status-success/30',
      bg: 'bg-surface',
    },
    warning: {
      icon: <AlertCircle className="h-4 w-4 text-status-warning shrink-0" />,
      border: 'border-status-warning/30',
      bg: 'bg-surface',
    },
    error: {
      icon: <AlertCircle className="h-4 w-4 text-status-danger shrink-0" />,
      border: 'border-status-danger/30',
      bg: 'bg-surface',
    },
    info: {
      icon: <Info className="h-4 w-4 text-accent shrink-0" />,
      border: 'border-border-strong',
      bg: 'bg-surface',
    },
  };

  const { icon, border, bg } = typeConfig[type];

  return (
    <div
      role="status"
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg border ${border} ${bg} shadow-float animate-in fade-in slide-in-from-bottom-2 duration-fast max-w-md`}
    >
      {icon}
      <span className="text-xs sm:text-sm font-medium text-text leading-tight">
        {message}
      </span>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss toast"
        className="ml-auto p-1 text-text-faint hover:text-text rounded transition-colors"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
};

export default Toast;
