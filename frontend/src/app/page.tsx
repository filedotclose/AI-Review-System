'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import { HardHat } from 'lucide-react';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (isAuthenticated) {
        router.replace('/brief');
      } else {
        router.replace('/login');
      }
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center gap-4 text-center p-6 bg-white rounded-2xl shadow-sm border border-gray-200">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-sm">
          <HardHat className="h-6 w-6 animate-pulse" />
        </div>
        <div>
          <h1 className="text-base font-bold text-gray-900">ODIPKS Construction OS</h1>
          <p className="text-xs text-gray-500 mt-1">Verifying device authorization...</p>
        </div>
        <div className="h-1.5 w-32 bg-gray-100 rounded-full overflow-hidden">
          <div className="h-full bg-indigo-600 rounded-full animate-pulse w-2/3"></div>
        </div>
      </div>
    </div>
  );
}
