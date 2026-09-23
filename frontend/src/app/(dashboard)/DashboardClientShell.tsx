'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { SyncStatusBadge } from '@/components/ui/SyncStatusBadge';
import { FileText, Wallet, Users, LayoutDashboard, HardHat, LogOut, ShieldCheck, User } from 'lucide-react';

export default function DashboardClientShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/login');
    }
  }, [isLoading, isAuthenticated, router]);

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

          <nav className="flex-1 space-y-1.5 px-3 pt-4">
            <Link
              href="/brief"
              className="group flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
            >
              <LayoutDashboard className="h-4 w-4 text-gray-400 group-hover:text-indigo-600" />
              Executive Brief
            </Link>
            <Link
              href="/dpr"
              className="group flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
            >
              <FileText className="h-4 w-4 text-gray-400 group-hover:text-indigo-600" />
              DPR Entry
            </Link>
            <Link
              href="/petty-cash"
              className="group flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
            >
              <Wallet className="h-4 w-4 text-gray-400 group-hover:text-indigo-600" />
              Petty Cash
            </Link>
            <Link
              href="/attendance"
              className="group flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
            >
              <Users className="h-4 w-4 text-gray-400 group-hover:text-indigo-600" />
              Attendance & Labour
            </Link>
          </nav>

          {/* Active User Session & Logout in Desktop Sidebar */}
          <div className="border-t border-gray-200 p-3 bg-gray-50/70">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-700">
                <User className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs font-bold text-gray-900 truncate">
                  {user?.name || 'Authorized User'}
                </div>
                <div className="flex items-center gap-1 text-[10px] font-semibold text-indigo-600 truncate uppercase">
                  <ShieldCheck className="h-3 w-3 inline text-indigo-500" />
                  {user?.role?.replace('_', ' ') || 'ENGINEER'}
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
                  <div className="text-[10px] text-gray-500">{user.phone || user.email}</div>
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

        {/* Mobile Navigation bar */}
        <div className="flex md:hidden overflow-x-auto border-b border-gray-200 bg-white px-3 py-2 gap-2 text-xs font-medium">
          <Link href="/brief" className="whitespace-nowrap px-2.5 py-1.5 rounded-md bg-gray-100 text-gray-700 hover:bg-indigo-50 hover:text-indigo-600">
            Brief
          </Link>
          <Link href="/dpr" className="whitespace-nowrap px-2.5 py-1.5 rounded-md bg-gray-100 text-gray-700 hover:bg-indigo-50 hover:text-indigo-600">
            DPR
          </Link>
          <Link href="/petty-cash" className="whitespace-nowrap px-2.5 py-1.5 rounded-md bg-gray-100 text-gray-700 hover:bg-indigo-50 hover:text-indigo-600">
            Petty Cash
          </Link>
          <Link href="/attendance" className="whitespace-nowrap px-2.5 py-1.5 rounded-md bg-gray-100 text-gray-700 hover:bg-indigo-50 hover:text-indigo-600">
            Attendance
          </Link>
        </div>

        {/* Scrollable Page Body */}
        <main className="flex-1 overflow-y-auto bg-gray-50 focus:outline-none">
          {children}
        </main>
      </div>
    </div>
  );
}
