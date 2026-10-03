'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  LayoutDashboard,
  FileText,
  Wallet,
  Users,
  Sun,
  Moon,
  Lock,
  ArrowRight,
} from 'lucide-react';
import { useTheme } from '@/lib/theme-context';
import { useAuth } from '@/lib/auth-context';

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSwitchRole?: (phone: string, pin: string, path: string) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onSwitchRole,
}) => {
  const router = useRouter();
  const { resolvedTheme, toggleTheme } = useTheme();
  const { logout } = useAuth();
  const [query, setQuery] = useState('');

  // Handle global Cmd/Ctrl+K keyboard listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Open handled externally or passed via state
        }
      } else if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const navigationItems = [
    { label: 'Executive Daily Brief', path: '/brief', icon: LayoutDashboard, category: 'Navigation' },
    { label: 'DPR & Technical Verification', path: '/dpr', icon: FileText, category: 'Navigation' },
    { label: 'Petty Cash & Approvals', path: '/petty-cash', icon: Wallet, category: 'Navigation' },
    { label: 'Attendance & Gang Muster', path: '/attendance', icon: Users, category: 'Navigation' },
  ];

  const filteredItems = navigationItems.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase())
  );

  const handleSelectNav = (path: string) => {
    router.push(path);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4"
    >
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/40 backdrop-blur-md transition-opacity"
      />

      <div className="relative w-full max-w-lg bg-surface border border-border rounded-lg shadow-float overflow-hidden z-10 animate-in fade-in zoom-in-95 duration-fast">
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-border gap-3 bg-surface-sunk/40">
          <Search className="h-4 w-4 text-text-faint shrink-0" />
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or jump to workspace..."
            className="w-full bg-transparent text-sm text-text placeholder:text-text-faint focus:outline-none"
          />
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-text-faint bg-surface border border-border rounded">
            ESC
          </kbd>
        </div>

        {/* Action Lists */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-1">
          <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            Workspaces & Modules
          </div>

          {filteredItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.path}
                type="button"
                onClick={() => handleSelectNav(item.path)}
                className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-surface-sunk text-xs text-text transition-colors duration-fast text-left group"
              >
                <div className="flex items-center gap-2.5">
                  <Icon className="h-4 w-4 text-text-muted group-hover:text-accent transition-colors" />
                  <span className="font-medium">{item.label}</span>
                </div>
                <ArrowRight className="h-3.5 w-3.5 text-text-faint opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            );
          })}

          {onSwitchRole && (
            <>
              <div className="px-3 pt-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted border-t border-border mt-2">
                Quick Role Impersonation
              </div>
              <button
                type="button"
                onClick={() => {
                  onSwitchRole('9800000001', '1234', '/brief');
                  onClose();
                }}
                className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-surface-sunk text-xs text-text transition-colors text-left"
              >
                <span>Switch to Company Owner</span>
                <span className="text-[10px] text-text-faint font-mono">OWNER</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  onSwitchRole('9811122233', '9999', '/dpr');
                  onClose();
                }}
                className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-surface-sunk text-xs text-text transition-colors text-left"
              >
                <span>Switch to Project Manager</span>
                <span className="text-[10px] text-text-faint font-mono">PM</span>
              </button>
            </>
          )}

          <div className="px-3 pt-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted border-t border-border mt-2">
            System & Privacy
          </div>

          <button
            type="button"
            onClick={() => {
              toggleTheme();
              onClose();
            }}
            className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-surface-sunk text-xs text-text transition-colors text-left"
          >
            <div className="flex items-center gap-2.5">
              {resolvedTheme === 'dark' ? (
                <Sun className="h-4 w-4 text-status-warning" />
              ) : (
                <Moon className="h-4 w-4 text-accent" />
              )}
              <span>Switch to {resolvedTheme === 'dark' ? 'Light Theme' : 'Dark Theme'}</span>
            </div>
            <span className="text-[10px] text-text-faint font-mono">Theme</span>
          </button>

          <button
            type="button"
            onClick={() => {
              logout();
              onClose();
            }}
            className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-status-danger-soft text-xs text-status-danger transition-colors text-left"
          >
            <div className="flex items-center gap-2.5">
              <Lock className="h-4 w-4 text-status-danger" />
              <span>Sign Out & Terminate Device Session</span>
            </div>
            <span className="text-[10px] font-mono">Logout</span>
          </button>
        </div>

        {/* Footer shortcuts helper */}
        <div className="px-4 py-2 bg-surface-sunk/60 border-t border-border flex items-center justify-between text-[11px] text-text-faint">
          <span>Use ⌘K / Ctrl+K anywhere to open</span>
          <span className="font-mono">ODIPKS Precision OS</span>
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
