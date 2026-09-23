import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import DashboardClientShell from './DashboardClientShell';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = cookies();
  const token = cookieStore.get('auth_token')?.value;

  // If this device lacks a validated session cookie, reject and redirect to login immediately
  if (!token) {
    redirect('/login');
  }

  return <DashboardClientShell>{children}</DashboardClientShell>;
}
