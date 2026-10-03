'use client';

import React, { forwardRef } from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  padding?: 'none' | 'sm' | 'md' | 'lg';
  isInteractive?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      padding = 'md',
      isInteractive = false,
      className = '',
      ...props
    },
    ref
  ) => {
    const paddingStyles = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    };

    return (
      <div
        ref={ref}
        className={`bg-surface border border-border rounded-lg shadow-soft transition-all duration-fast ease-calm ${
          isInteractive
            ? 'hover:border-border-strong hover:shadow-float cursor-pointer'
            : ''
        } ${paddingStyles[padding]} ${className}`}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';

export const CardHeader = ({
  children,
  className = '',
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={`pb-4 border-b border-border flex items-center justify-between gap-4 ${className}`}>
    {children}
  </div>
);

export const CardTitle = ({
  children,
  className = '',
}: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={`text-base font-semibold text-text tracking-tight ${className}`}>
    {children}
  </h3>
);

export const CardDescription = ({
  children,
  className = '',
}: React.HTMLAttributes<HTMLParagraphElement>) => (
  <p className={`text-xs text-text-muted mt-0.5 leading-relaxed ${className}`}>
    {children}
  </p>
);

export const CardContent = ({
  children,
  className = '',
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={`pt-4 ${className}`}>{children}</div>
);

export const CardFooter = ({
  children,
  className = '',
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={`pt-4 mt-4 border-t border-border flex items-center justify-between gap-3 ${className}`}>
    {children}
  </div>
);

export default Card;
