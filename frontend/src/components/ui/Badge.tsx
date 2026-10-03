'use client';

import React from 'react';
import { Sparkles, ShieldCheck } from 'lucide-react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'ai' | 'verified';
  size?: 'sm' | 'md';
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  dot = false,
  className = '',
  ...props
}) => {
  const variantStyles = {
    neutral: 'bg-surface-sunk text-text-muted border-border',
    accent: 'bg-accent-soft text-accent border-accent/20',
    success: 'bg-status-success-soft text-status-success border-status-success/20',
    warning: 'bg-status-warning-soft text-status-warning border-status-warning/20',
    danger: 'bg-status-danger-soft text-status-danger border-status-danger/20',
    ai: 'bg-accent-soft text-accent border-accent/30 font-medium',
    verified: 'bg-status-success-soft text-status-success border-status-success/30 font-medium',
  };

  const sizeStyles = {
    sm: 'text-[10px] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
  };

  return (
    <span
      className={`inline-flex items-center font-medium rounded-pill border select-none transition-colors duration-fast ${
        variantStyles[variant]
      } ${sizeStyles[size]} ${className}`}
      {...props}
    >
      {dot && (
        <span
          className={`h-1.5 w-1.5 rounded-pill ${
            variant === 'success'
              ? 'bg-status-success'
              : variant === 'warning'
              ? 'bg-status-warning'
              : variant === 'danger'
              ? 'bg-status-danger'
              : variant === 'accent' || variant === 'ai'
              ? 'bg-accent'
              : 'bg-text-faint'
          }`}
        />
      )}
      {variant === 'ai' && <Sparkles className="h-3 w-3 shrink-0" />}
      {variant === 'verified' && <ShieldCheck className="h-3 w-3 shrink-0" />}
      <span>{children}</span>
    </span>
  );
};

export default Badge;
