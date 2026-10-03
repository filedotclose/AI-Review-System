'use client';

import React, { forwardRef, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  helperText?: string;
  error?: string;
  leftIcon?: React.ReactNode;
  rightElement?: React.ReactNode;
  isPassword?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label,
      helperText,
      error,
      leftIcon,
      rightElement,
      isPassword = false,
      type = 'text',
      className = '',
      id,
      ...props
    },
    ref
  ) => {
    const [showPassword, setShowPassword] = useState(false);
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
    const effectiveType = isPassword ? (showPassword ? 'text' : 'password') : type;

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-medium uppercase tracking-wider text-text-muted"
          >
            {label}
          </label>
        )}

        <div className="relative flex items-center">
          {leftIcon && (
            <span className="absolute left-3 flex items-center pointer-events-none text-text-faint">
              {leftIcon}
            </span>
          )}

          <input
            ref={ref}
            id={inputId}
            type={effectiveType}
            className={`w-full bg-surface-sunk border rounded-md text-sm text-text placeholder:text-text-faint transition-all duration-fast ease-calm py-2 px-3 ${
              leftIcon ? 'pl-9' : ''
            } ${
              isPassword || rightElement ? 'pr-10' : ''
            } ${
              error
                ? 'border-status-danger/60 focus:border-status-danger focus:ring-2 focus:ring-status-danger/20'
                : 'border-border focus:border-accent focus:ring-2 focus:ring-accent/15'
            } focus:outline-none focus:bg-surface disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
            {...props}
          />

          {isPassword && (
            <button
              type="button"
              tabIndex={-1}
              onClick={() => setShowPassword(!showPassword)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="absolute right-3 p-1 text-text-faint hover:text-text transition-colors cursor-pointer rounded"
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          )}

          {!isPassword && rightElement && (
            <div className="absolute right-3 flex items-center">
              {rightElement}
            </div>
          )}
        </div>

        {error ? (
          <p className="text-xs text-status-danger font-medium leading-tight">
            {error}
          </p>
        ) : helperText ? (
          <p className="text-xs text-text-faint leading-tight">
            {helperText}
          </p>
        ) : null}
      </div>
    );
  }
);

Input.displayName = 'Input';
export default Input;
