'use client';

import React from 'react';
import { useTheme } from '@/lib/theme-context';
import { Sun, Moon } from 'lucide-react';

interface ThemeSegmentedControlProps {
  className?: string;
  size?: 'sm' | 'md';
}

export const ThemeSegmentedControl: React.FC<ThemeSegmentedControlProps> = ({
  className = '',
  size = 'md',
}) => {
  const { resolvedTheme, setTheme } = useTheme();

  const isSmall = size === 'sm';

  return (
    <div
      role="radiogroup"
      aria-label="Color theme selection"
      className={`inline-flex items-center p-0.5 rounded-pill glass-pill border border-border/80 select-none shadow-inner ${className}`}
    >
      <button
        type="button"
        role="radio"
        aria-checked={resolvedTheme === 'light'}
        onClick={() => setTheme('light')}
        className={`flex items-center gap-1.5 rounded-pill transition-all duration-fast cursor-pointer ${
          isSmall ? 'px-2.5 py-0.5 text-[11px]' : 'px-3 py-1 text-xs'
        } ${
          resolvedTheme === 'light'
            ? 'bg-surface/95 text-text shadow-soft font-semibold border border-white/50'
            : 'text-text-muted hover:text-text font-medium'
        }`}
        title="Switch to Light Theme (Mineral Alabaster)"
      >
        <Sun className={`${isSmall ? 'h-3 w-3' : 'h-3.5 w-3.5'} text-status-warning shrink-0`} />
        <span>Light</span>
      </button>

      <button
        type="button"
        role="radio"
        aria-checked={resolvedTheme === 'dark'}
        onClick={() => setTheme('dark')}
        className={`flex items-center gap-1.5 rounded-pill transition-all duration-fast cursor-pointer ${
          isSmall ? 'px-2.5 py-0.5 text-[11px]' : 'px-3 py-1 text-xs'
        } ${
          resolvedTheme === 'dark'
            ? 'bg-surface/90 text-text shadow-soft font-semibold border border-white/15'
            : 'text-text-muted hover:text-text font-medium'
        }`}
        title="Switch to Dark Theme (Obsidian Slate)"
      >
        <Moon className={`${isSmall ? 'h-3 w-3' : 'h-3.5 w-3.5'} text-accent shrink-0`} />
        <span>Dark</span>
      </button>
    </div>
  );
};
