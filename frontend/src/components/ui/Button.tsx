'use client';

import React, { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive' | 'accent-soft';
  size?: 'sm' | 'md' | 'lg' | 'icon';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'secondary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      className = '',
      disabled,
      ...props
    },
    ref
  ) => {
    // Base styles: calm transitions, focus ring, font-medium, rounded-pill
    const baseStyles =
      'inline-flex items-center justify-center font-medium transition-all duration-fast ease-calm focus-ring select-none active:scale-[0.99] disabled:opacity-50 disabled:pointer-events-none disabled:active:scale-100 rounded-pill cursor-pointer';

    const variantStyles = {
      primary:
        'bg-accent text-accent-contrast shadow-soft hover:bg-accent-hover',
      secondary:
        'bg-surface border border-border text-text hover:bg-surface-sunk shadow-soft',
      ghost:
        'text-text-muted hover:text-text hover:bg-surface-sunk',
      destructive:
        'bg-status-danger-soft text-status-danger border border-status-danger/20 hover:bg-status-danger/20',
      'accent-soft':
        'bg-accent-soft text-accent hover:bg-accent/20 border border-accent/20',
    };

    const sizeStyles = {
      sm: 'text-xs px-3 py-1.5 gap-1.5 h-8',
      md: 'text-xs sm:text-sm px-4 py-2 gap-2 h-9.5',
      lg: 'text-sm sm:text-base px-6 py-2.5 gap-2.5 h-11',
      icon: 'p-2 h-9 w-9 rounded-pill',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-current" />
        ) : (
          leftIcon
        )}
        {children && <span>{children}</span>}
        {!isLoading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';
export default Button;
