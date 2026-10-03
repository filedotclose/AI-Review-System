'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth, getDefaultRouteForRole } from '@/lib/auth-context';
import { SyncStatusBadge } from '@/components/ui/SyncStatusBadge';
import apiClient from '@/lib/api-client';
import {
  FileText,
  Wallet,
  Users,
  LayoutDashboard,
  HardHat,
  LogOut,
  ShieldCheck,
  Lock,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';

const DEMO_PERSONAS = [
  { role: 'OWNER', label: 'Company Owner', name: 'Pradeep K. Sharma', phone: '9800000001', pin: '1234', defaultPath: '/brief' },
  { role: 'FINANCE_HEAD', label: 'Finance Head', name: 'Ananya Sen', phone: '9800000002', pin: '1234', defaultPath: '/petty-cash' },
  { role: 'PROJECT_MANAGER', label: 'Project Manager', name: 'Vikram Mehta', phone: '9811122233', pin: '9999', defaultPath: '/dpr' },
  { role: 'SITE_ENGINEER', label: 'Site Engineer', name: 'Rajesh Sharma', phone: '9876543210', pin: '1234', defaultPath: '/dpr' },
  { role: 'SUPERVISOR', label: 'Site Supervisor', name: 'Sunil Varma', phone: '9876543211', pin: '1234', defaultPath: '/attendance' },
];

export default function DashboardClientShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading, logout, login } = useAuth();
  const [isSwitchingRole, setIsSwitchingRole] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case 'OWNER':
        return {
          label: 'Company Owner',
          duty: 'Enterprise Strategy & Oversight',
          style: 'text-purple-700 bg-purple-50 border-purple-200',
        };
      case 'FINANCE_HEAD':
        return {
          label: 'Finance Head',
          duty: 'Commercial & Disbursements',
          style: 'text-emerald-700 bg-emerald-50 border-emerald-200',
        };
      case 'PROJECT_MANAGER':
        return {
          label: 'Project Manager',
          duty: 'Site Delivery & Quality Sign-Off',
          style: 'text-blue-700 bg-blue-50 border-blue-200',
        };
      case 'SITE_ENGINEER':
        return {
          label: 'Site Engineer',
          duty: 'Field Piling & Rig Execution',
          style: 'text-indigo-700 bg-indigo-50 border-indigo-200',
        };
      case 'SUPERVISOR':
        return {
          label: 'Site Supervisor',
          duty: 'Labour Muster & Ground Claims',
          style: 'text-amber-700 bg-amber-50 border-amber-200',
        };
      default:
        return {
          label: role?.replace('_', ' ') || 'Authorized User',
          duty: 'Site Operations',
          style: 'text-gray-700 bg-gray-50 border-gray-200',
        };
    }
  };

  const roleInfo = getRoleBadge(user?.role);

  const getNavItemsForRole = (role?: string) => {
    switch (role) {
      case 'OWNER':
        return [
          { href: '/brief', label: 'Executive Brief', icon: LayoutDashboard },
          { href: '/dpr', label: 'DPR Overview', icon: FileText },
          { href: '/petty-cash', label: 'Petty Cash', icon: Wallet },
          { href: '/attendance', label: 'Labour Muster', icon: Users },
        ];
      case 'FINANCE_HEAD':
        return [
          { href: '/petty-cash', label: 'Petty Cash & Approvals', icon: Wallet },
          { href: '/brief', label: 'Financial Brief', icon: LayoutDashboard },
        ];
      case 'PROJECT_MANAGER':
        return [
          { href: '/dpr', label: 'DPR Verification', icon: FileText },
          { href: '/brief', label: 'Operational Brief', icon: LayoutDashboard },
          { href: '/attendance', label: 'Attendance & Labour', icon: Users },
          { href: '/petty-cash', label: 'Site Petty Cash', icon: Wallet },
        ];
      case 'SITE_ENGINEER':
        return [
          { href: '/dpr', label: 'DPR Technical Entry', icon: FileText },
          { href: '/petty-cash', label: 'Emergency Spends', icon: Wallet },
        ];
      case 'SUPERVISOR':
        return [
          { href: '/attendance', label: 'Attendance & Gang Muster', icon: Users },
          { href: '/petty-cash', label: 'Petty Cash Claims', icon: Wallet },
        ];
      default:
        return [
          { href: '/brief', label: 'Executive Brief', icon: LayoutDashboard },
          { href: '/dpr', label: 'DPR Entry', icon: FileText },
          { href: '/petty-cash', label: 'Petty Cash', icon: Wallet },
          { href: '/attendance', label: 'Attendance', icon: Users },
        ];
    }
  };

  const navItems = getNavItemsForRole(user?.role);

  // Quick Persona Impersonation Switcher
  const handleQuickSwitchRole = async (targetPhone: string, targetPin: string, targetPath: string) => {
    try {
      setIsSwitchingRole(true);
      const res = await apiClient.post('/auth/login', {
        phone: targetPhone,
        pin: targetPin,
      });
      if (res.data?.access_token) {
        await login(res.data.access_token, res.data.refresh_token);
        router.push(targetPath);
      }
    } catch (err) {
      console.error('Failed to switch persona:', err);
    } finally {
      setIsSwitchingRole(false);
    }
  };

  // Route Restriction Guard
  const isBriefRestricted = pathname === '/brief' && (user?.role === 'SUPERVISOR' || user?.role === 'SITE_ENGINEER');

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex md:w-64 md:flex-col border-r border-gray-200 bg-white">
        <div className="flex flex-col flex-grow pt-5 pb-4 overflow-y-auto">
          <div className="flex items-center gap-2.5 px-4 pb-4 border-b border-gray-100">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
              <HardHat className="h-5 w-5" />
            </div>
            <div>
              <div className="font-bold text-base text-gray-900 leading-none">ODIPKS OS</div>
              <div className="text-[11px] text-gray-500 font-medium mt-0.5">Heavy Civil Pilot</div>
            </div>
          </div>

          <div className="px-3 py-3 border-b border-gray-100 bg-gray-50/50">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Active Site</div>
            <div className="text-xs font-medium text-gray-800 truncate mt-0.5" title="ADANI-ODIPKS AVRP Flyover, Vadakara">
              ADANI-ODIPKS AVRP Flyover
            </div>
          </div>

          {/* Role Status Tag */}
          <div className="px-3 pt-3">
            <div className={`p-2 rounded-lg border text-xs ${roleInfo.style}`}>
              <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-[10px]">
                <ShieldCheck className="h-3.5 w-3.5 inline shrink-0" />
                <span>{roleInfo.label}</span>
              </div>
              <p className="text-[11px] opacity-90 mt-0.5 font-medium leading-tight">{roleInfo.duty}</p>
            </div>
          </div>

          {/* Filtered Navigation */}
          <nav className="flex-1 space-y-1.5 px-3 pt-4">
            <div className="text-[10px] font-bold uppercase tracking-wider text-gray-400 px-3 pb-1">
              Role Workspaces
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`group flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 font-semibold'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  <Icon className={`h-4 w-4 shrink-0 ${isActive ? 'text-indigo-600' : 'text-gray-400 group-hover:text-gray-600'}`} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Quick Demo Role Switcher */}
          <div className="border-t border-gray-100 p-3 bg-slate-50/70">
            <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1.5">
              <span>Switch Role (RBAC Demo)</span>
              {isSwitchingRole && <RefreshCw className="h-3 w-3 animate-spin text-indigo-600" />}
            </div>
            <select
              value={user?.role || ''}
              onChange={(e) => {
                const persona = DEMO_PERSONAS.find((p) => p.role === e.target.value);
                if (persona) {
                  handleQuickSwitchRole(persona.phone, persona.pin, persona.defaultPath);
                }
              }}
              disabled={isSwitchingRole}
              aria-label="Switch Role (RBAC Demo)"
              className="w-full text-xs bg-white border border-gray-200 rounded-md py-1.5 px-2 text-gray-700 font-medium focus:outline-none focus:ring-1 focus:ring-indigo-500 cursor-pointer disabled:opacity-50"
            >
              {DEMO_PERSONAS.map((p) => (
                <option key={p.role} value={p.role}>
                  {p.label} ({p.name.split(' ')[0]})
                </option>
              ))}
            </select>
          </div>

          {/* Active User Session & Logout in Desktop Sidebar */}
          <div className="border-t border-gray-200 p-3 bg-gray-50/70">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-white text-xs font-bold shadow-xs">
                {user?.name ? user.name.split(' ').map((n: string) => n[0]).slice(0, 2).join('').toUpperCase() : 'U'}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-bold text-gray-900 truncate">
                  {user?.name || 'Authorized User'}
                </div>
                <div className="text-[10px] text-gray-500 truncate">
                  {user?.phone}
                </div>
              </div>
              <button
                onClick={logout}
                title="End device session (Sign Out)"
                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header */}
        <header className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-4 sm:px-6">
          <div className="flex items-center gap-3">
            {/* Mobile Title */}
            <div className="flex md:hidden items-center gap-2">
              <HardHat className="h-5 w-5 text-indigo-600" />
              <span className="font-bold text-gray-900">ODIPKS</span>
            </div>
            <div className="hidden sm:block text-xs font-medium text-gray-500">
              Site ID #1 • Vadakara AVRP Flyover Package
            </div>
          </div>

          <div className="flex items-center gap-3">
            <SyncStatusBadge />

            {/* Header User details & Logout Button */}
            {user && (
              <div className="hidden sm:flex items-center gap-2.5 pl-3 border-l border-gray-200">
                <div className="text-right">
                  <div className="text-xs font-semibold text-gray-900">{user.name}</div>
                  <div className={`text-[10px] font-semibold px-1 rounded border inline-block ${roleInfo.style}`}>{roleInfo.label}</div>
                </div>
                <button
                  onClick={logout}
                  title="Sign Out from this device"
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors border border-gray-200 cursor-pointer"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  <span>Logout</span>
                </button>
              </div>
            )}

            {/* Mobile Logout Button */}
            <button
              onClick={logout}
              title="Sign Out from this device"
              className="sm:hidden p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-md cursor-pointer"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>

        {/* Mobile Navigation bar (Filtered for current role) */}
        <div className="flex md:hidden overflow-x-auto border-b border-gray-200 bg-white px-3 py-2 gap-2 text-xs font-medium">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap px-2.5 py-1.5 rounded-md transition-colors ${
                  isActive ? 'bg-indigo-600 text-white font-semibold' : 'bg-gray-100 text-gray-700 hover:bg-indigo-50 hover:text-indigo-600'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>

        {/* Scrollable Page Body with Route Protection Guard */}
        <main className="flex-1 overflow-y-auto bg-gray-50 focus:outline-none">
          {isBriefRestricted ? (
            <div className="max-w-2xl mx-auto my-12 p-8 bg-white border border-amber-200 rounded-xl shadow-xs text-center">
              <div className="h-12 w-12 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center mx-auto mb-4">
                <Lock className="h-6 w-6" />
              </div>
              <h2 className="text-lg font-bold text-gray-900 mb-1">Executive Brief Access Restricted</h2>
              <p className="text-sm text-gray-600 max-w-md mx-auto mb-6">
                Executive briefs and company financial summaries are restricted to Company Owners, Finance Heads, and Project Managers. As a{' '}
                <span className="font-semibold text-gray-900">{roleInfo.label}</span>, your operational workspace is ready for your duties.
              </p>
              <button
                onClick={() => router.push(getDefaultRouteForRole(user?.role))}
                className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-lg hover:bg-indigo-700 transition-colors cursor-pointer"
              >
                <span>Go to Your Assigned Workspace</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          ) : (
            children
          )}
        </main>
      </div>
    </div>
  );
}
