import Link from 'next/link';
import { SyncStatusBadge } from '@/components/ui/SyncStatusBadge';
import { FileText, Wallet, Users, LayoutDashboard, HardHat } from 'lucide-react';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
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
