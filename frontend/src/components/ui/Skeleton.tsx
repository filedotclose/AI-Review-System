'use client';

import React from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'rect' | 'circle' | 'text' | 'card';
}

export const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'rect',
  className = '',
  ...props
}) => {
  const variantStyles = {
    rect: 'rounded-md',
    circle: 'rounded-pill',
    text: 'h-4 w-3/4 rounded-sm',
    card: 'h-32 w-full rounded-lg',
  };

  return (
    <div
      className={`bg-surface-sunk animate-shimmer ${variantStyles[variant]} ${className}`}
      {...props}
    />
  );
};

export default Skeleton;
