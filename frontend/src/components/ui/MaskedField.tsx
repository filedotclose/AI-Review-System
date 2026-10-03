'use client';

import React, { useState, useEffect } from 'react';
import { Eye, EyeOff } from 'lucide-react';

export interface MaskedFieldProps {
  value: string | number;
  maskType?: 'currency' | 'phone' | 'identifier' | 'text';
  timeoutSeconds?: number;
  className?: string;
  currencyPrefix?: string;
}

export const MaskedField: React.FC<MaskedFieldProps> = ({
  value,
  maskType = 'text',
  timeoutSeconds = 15,
  className = '',
  currencyPrefix = '₹',
}) => {
  const [isRevealed, setIsRevealed] = useState(false);
  const [timeLeft, setTimeLeft] = useState(timeoutSeconds);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    let interval: NodeJS.Timeout;

    if (isRevealed) {
      setTimeLeft(timeoutSeconds);
      interval = setInterval(() => {
        setTimeLeft((prev) => (prev > 1 ? prev - 1 : 0));
      }, 1000);

      timer = setTimeout(() => {
        setIsRevealed(false);
      }, timeoutSeconds * 1000);
    }

    return () => {
      clearTimeout(timer);
      clearInterval(interval);
    };
  }, [isRevealed, timeoutSeconds]);

  const rawString = String(value);

  const getMaskedValue = () => {
    if (maskType === 'currency') {
      return `${currencyPrefix} ••••••`;
    }
    if (maskType === 'phone') {
      return rawString.length >= 4
        ? `${rawString.slice(0, 2)}••••••${rawString.slice(-2)}`
        : '••••••••';
    }
    if (maskType === 'identifier') {
      return '••••••••';
    }
    return '••••••••';
  };

  const getFormattedValue = () => {
    if (maskType === 'currency') {
      const num = typeof value === 'number' ? value : parseFloat(rawString) || 0;
      return `${currencyPrefix}${num.toLocaleString('en-IN')}`;
    }
    return rawString;
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono text-xs select-none ${className}`}
    >
      <span className="tabular-nums transition-all duration-fast">
        {isRevealed ? getFormattedValue() : getMaskedValue()}
      </span>

      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsRevealed(!isRevealed);
        }}
        title={isRevealed ? `Masking in ${timeLeft}s (Click to re-mask)` : 'Confidential: Click to reveal'}
        className="p-0.5 text-text-faint hover:text-text rounded transition-colors"
      >
        {isRevealed ? (
          <EyeOff className="h-3.5 w-3.5 text-accent" />
        ) : (
          <Eye className="h-3.5 w-3.5" />
        )}
      </button>

      {isRevealed && (
        <span className="text-[10px] text-text-faint font-sans tabular-nums">
          ({timeLeft}s)
        </span>
      )}
    </span>
  );
};

export default MaskedField;
