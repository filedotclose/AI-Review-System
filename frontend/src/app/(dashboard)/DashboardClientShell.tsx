'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth, getDefaultRouteForRole } from '@/lib/auth-context';
import { SyncStatusBadge } from '@/components/ui/SyncStatusBadge';
import { SecurityTrustIndicator } from '@/components/ui/SecurityTrustIndicator';
import { PrivacyShield } from '@/components/ui/PrivacyShield';
import { CommandPalette } from '@/components/ui/CommandPalette';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ThemeSegmentedControl } from '@/components/ui/ThemeSegmentedControl';
import apiClient from '@/lib/api-client';
import {
  FileText,
  Wallet,
  Users,
  LayoutDashboard,
  LogOut,
  Lock,
  ArrowRight,
  RefreshCw,
  Search,
  Compass,
} from 'lucide-react';

export default function DashboardClientShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  // Global shortcut: ⌘K or Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const getRoleDetails = (role?: string) => {
    switch (role) {
      case 'OWNER':
        return {
          label: 'Company Owner',
          duty: 'Enterprise Strategy & Oversight',
          variant: 'accent' as const,
        };
      case 'FINANCE_HEAD':
        return {
          label: 'Finance Head',
          duty: 'Commercial & Disbursements',
          variant: 'success' as const,
        };
      case 'PROJECT_MANAGER':
        return {
          label: 'Project Manager',
          duty: 'Site Delivery & Quality Sign-Off',
          variant: 'accent' as const,
        };
      case 'SITE_ENGINEER':
        return {
          label: 'Site Engineer',
          duty: 'Field Piling & Rig Execution',
          variant: 'neutral' as const,
        };
      case 'SUPERVISOR':
        return {
          label: 'Site Supervisor',
          duty: 'Labour Muster & Ground Claims',
          variant: 'warning' as const,
        };
      default:
        return {
          label: role?.replace('_', ' ') || 'Authorized User',
          duty: 'Site Operations',
          variant: 'neutral' as const,
        };
    }
  };

  const roleInfo = getRoleDetails(user?.role);

  const getNavItemsForRole = (role?: string) => {
    switch (role) {
      case 'OWNER':
        return [
          { href: '/brief', label: 'Executive Brief', icon: LayoutDashboard },
          { href: '/dpr', label: 'DPR Review & Queue', icon: FileText },
          { href: '/petty-cash', label: 'Petty Cash Ledger', icon: Wallet },
          { href: '/attendance', label: 'Labour Muster', icon: Users },
        ];
      case 'FINANCE_HEAD':
        return [
          { href: '/petty-cash', label: 'Petty Cash & Approvals', icon: Wallet },
          { href: '/brief', label: 'Financial Brief', icon: LayoutDashboard },
        ];
      case 'PROJECT_MANAGER':
        return [
          { href: '/dpr', label: 'DPR Verification Queue', icon: FileText },
          { href: '/brief', label: 'Operational Brief', icon: LayoutDashboard },
          { href: '/attendance', label: 'Attendance & Labour', icon: Users },
          { href: '/petty-cash', label: 'Site Petty Cash', icon: Wallet },
        ];
      case 'SITE_ENGINEER':
        return [
          { href: '/dpr', label: 'DPR Upload & Entry', icon: FileText },
          { href: '/petty-cash', label: 'Emergency Spends', icon: Wallet },
        ];
      case 'SUPERVISOR':
        return [
          { href: '/attendance', label: 'Attendance & Muster', icon: Users },
          { href: '/petty-cash', label: 'Petty Cash Claims', icon: Wallet },
        ];
      default:
        return [
          { href: '/brief', label: 'Executive Brief', icon: LayoutDashboard },
          { href: '/dpr', label: 'DPR Review Queue', icon: FileText },
          { href: '/petty-cash', label: 'Petty Cash', icon: Wallet },
          { href: '/attendance', label: 'Attendance', icon: Users },
        ];
    }
  };

  const navItems = getNavItemsForRole(user?.role);

  const isBriefRestricted =
    pathname === '/brief' && (user?.role === 'SUPERVISOR' || user?.role === 'SITE_ENGINEER');

  return (
    <PrivacyShield
      userRole={user?.role}
      userName={user?.name}
      idleTimeoutSeconds={300}
      enableBlurOnTabSwitch={true}
    >
      <div className="flex h-screen bg-bg text-text overflow-hidden font-sans">
        {/* Command Palette Keyboard Shortcut Modal */}
        <CommandPalette
          isOpen={isCommandPaletteOpen}
          onClose={() => setIsCommandPaletteOpen(false)}
        />

        {/* Minimal Quiet Desktop Sidebar */}
        <aside className="hidden md:flex md:w-64 md:flex-col border-r border-border bg-surface select-none">
          <div className="flex flex-col flex-grow pt-4 pb-4 overflow-y-auto">
            {/* Branding / Header */}
            <div className="flex items-center gap-3 px-5 pb-4 border-b border-border">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent-soft text-accent border border-accent/20">
                <Compass className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <div className="font-semibold text-sm tracking-tight text-text">
                  ODIPKS
                </div>
                <div className="text-[11px] text-text-faint truncate">
                  Precision Review OS
                </div>
              </div>
            </div>

            {/* Site Context Badge */}
            <div className="px-5 py-3 border-b border-border bg-surface-sunk/40">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                Active Site
              </div>
              <div
                className="text-xs font-medium text-text truncate mt-0.5"
                title="ADANI-ODIPKS AVRP Flyover, Vadakara"
              >
                ADANI-ODIPKS AVRP Flyover
              </div>
            </div>

            {/* Role Chip */}
            <div className="px-4 pt-3 pb-1">
              <div className="p-2.5 rounded-md bg-surface-sunk/60 border border-border space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                    Active Identity
                  </span>
                  <Badge variant={roleInfo.variant} size="sm">
                    {roleInfo.label}
                  </Badge>
                </div>
                <p className="text-[11px] text-text-muted leading-tight">
                  {roleInfo.duty}
                </p>
              </div>
            </div>

            {/* Navigation Rail */}
            <nav className="flex-1 space-y-1 px-3 pt-3">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted px-3 pb-1">
                Workspaces
              </div>
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2 text-xs font-medium rounded-pill transition-all duration-fast ${
                      isActive
                        ? 'bg-accent-soft text-accent border border-accent/20 font-semibold shadow-soft'
                        : 'text-text-muted hover:text-text hover:bg-surface-sunk'
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>

            {/* User Session Footer */}
            <div className="border-t border-border p-3 bg-surface">
              <div className="flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-pill bg-accent-soft text-accent text-xs font-semibold border border-accent/20">
                  {user?.name
                    ? user.name
                        .split(' ')
                        .map((n: string) => n[0])
                        .slice(0, 2)
                        .join('')
                        .toUpperCase()
                    : 'U'}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-xs font-medium text-text truncate">
                    {user?.name || 'Authorized User'}
                  </div>
                  <div className="text-[10px] text-text-faint font-mono truncate">
                    {user?.phone ? `${user.phone.slice(0, 3)}••••${user.phone.slice(-3)}` : ''}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={logout}
                  title="Sign Out (Terminate Session)"
                  className="p-1.5 text-text-faint hover:text-status-danger hover:bg-status-danger-soft rounded-pill transition-colors cursor-pointer"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Workspace Frame */}
        <div className="flex flex-1 flex-col overflow-hidden relative">
          {/* Subtle atmospheric ambient glow orbs for glass refraction */}
          <div className="absolute -top-32 right-1/4 w-[450px] h-[450px] bg-accent/8 rounded-pill filter blur-[140px] pointer-events-none" />
          <div className="absolute bottom-10 right-10 w-80 h-80 bg-status-warning/6 rounded-pill filter blur-[120px] pointer-events-none" />

          {/* Frosted Glass Top Navigation Bar (Section 5 & 7) */}
          <header className="glass-surface sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border px-4 sm:px-6">
            <div className="flex items-center gap-3">
              {/* Mobile Title */}
              <div className="flex md:hidden items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-md bg-accent-soft text-accent border border-accent/20">
                  <Compass className="h-4 w-4" />
                </div>
                <span className="font-semibold text-sm text-text">ODIPKS</span>
              </div>

              {/* Breadcrumbs / Project Scope */}
              <div className="hidden sm:flex items-center gap-2 text-xs text-text-muted">
                <span className="font-medium text-text">Vadakara AVRP Flyover</span>
                <span className="text-text-faint">/</span>
                <span className="text-text-faint">Site Package #1</span>
              </div>
            </div>

            {/* Action Bar Right */}
            <div className="flex items-center gap-2.5">
              {/* Command Palette Trigger */}
              <button
                type="button"
                onClick={() => setIsCommandPaletteOpen(true)}
                className="hidden sm:inline-flex items-center gap-2 px-2.5 py-1 text-xs text-text-muted bg-surface-sunk/60 hover:bg-surface-sunk border border-border rounded-pill transition-colors cursor-pointer"
              >
                <Search className="h-3 w-3 text-text-faint" />
                <span>Search</span>
                <kbd className="text-[10px] font-mono text-text-faint bg-surface border border-border px-1 rounded">
                  ⌘K
                </kbd>
              </button>

              {/* Offline / Online Sync Indicator */}
              <SyncStatusBadge />

              {/* Security & Confidentiality Trust Indicator */}
              <SecurityTrustIndicator userRole={user?.role} userName={user?.name} />

              {/* Prominent Theme Segmented Control (Light / Dark) */}
              <ThemeSegmentedControl size="sm" />

              {/* Mobile Logout */}
              <button
                type="button"
                onClick={logout}
                title="End device session"
                className="md:hidden p-1.5 text-text-muted hover:text-status-danger rounded-pill cursor-pointer"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </header>

          {/* Mobile Secondary Navigation Ribbon */}
          <div className="flex md:hidden overflow-x-auto border-b border-border bg-surface px-3 py-2 gap-1.5 text-xs font-medium">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`whitespace-nowrap px-3 py-1 rounded-pill transition-colors ${
                    isActive
                      ? 'bg-accent-soft text-accent border border-accent/20 font-semibold'
                      : 'bg-surface-sunk text-text-muted hover:text-text'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>

          {/* Main Scrollable Viewport */}
          <main className="flex-1 overflow-y-auto bg-bg focus:outline-none">
            {isBriefRestricted ? (
              <div className="max-w-md mx-auto my-16 p-8 bg-surface border border-status-warning/20 rounded-lg shadow-soft text-center space-y-4">
                <div className="h-10 w-10 rounded-pill bg-status-warning-soft text-status-warning flex items-center justify-center mx-auto">
                  <Lock className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-text">
                    Executive Brief Access Restricted
                  </h2>
                  <p className="text-xs text-text-muted mt-1 leading-relaxed">
                    Executive briefs and company financial summaries are restricted to
                    Company Owners, Finance Heads, and Project Managers.
                  </p>
                </div>
                <Button
                  variant="primary"
                  size="md"
                  onClick={() => router.push(getDefaultRouteForRole(user?.role))}
                  rightIcon={<ArrowRight className="h-4 w-4" />}
                >
                  Go to Assigned Workspace
                </Button>
              </div>
            ) : (
              children
            )}
          </main>
        </div>
      </div>
    </PrivacyShield>
  );
}
