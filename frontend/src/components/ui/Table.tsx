'use client';

import React from 'react';

export const Table = ({
  children,
  className = '',
  ...props
}: React.TableHTMLAttributes<HTMLTableElement>) => (
  <div className="w-full overflow-x-auto rounded-lg border border-border bg-surface">
    <table
      className={`w-full text-left text-xs sm:text-sm border-collapse ${className}`}
      {...props}
    >
      {children}
    </table>
  </div>
);

export const TableHeader = ({
  children,
  className = '',
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) => (
  <thead
    className={`bg-surface-sunk/70 border-b border-border text-[11px] font-semibold uppercase tracking-wider text-text-muted select-none ${className}`}
    {...props}
  >
    {children}
  </thead>
);

export const TableBody = ({
  children,
  className = '',
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) => (
  <tbody className={`divide-y divide-border ${className}`} {...props}>
    {children}
  </tbody>
);

export const TableRow = ({
  children,
  isClickable = false,
  className = '',
  ...props
}: React.HTMLAttributes<HTMLTableRowElement> & { isClickable?: boolean }) => (
  <tr
    className={`transition-colors duration-fast ${
      isClickable ? 'cursor-pointer hover:bg-surface-sunk/60' : 'hover:bg-surface-sunk/30'
    } ${className}`}
    {...props}
  >
    {children}
  </tr>
);

export const TableHead = ({
  children,
  align = 'left',
  className = '',
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement> & { align?: 'left' | 'center' | 'right' }) => (
  <th
    className={`py-3 px-4 font-semibold ${
      align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
    } ${className}`}
    {...props}
  >
    {children}
  </th>
);

export const TableCell = ({
  children,
  align = 'left',
  isNumeric = false,
  className = '',
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement> & {
  align?: 'left' | 'center' | 'right';
  isNumeric?: boolean;
}) => (
  <td
    className={`py-3.5 px-4 text-text ${
      isNumeric ? 'tabular-nums font-mono text-xs' : ''
    } ${align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'} ${className}`}
    {...props}
  >
    {children}
  </td>
);

export default Table;
