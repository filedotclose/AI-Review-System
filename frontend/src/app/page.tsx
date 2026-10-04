import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export default async function Home() {
  const cookieStore = await cookies();
  const token = cookieStore.get('auth_token')?.value;
  const role = cookieStore.get('user_role')?.value;

  if (token) {
    switch (role) {
      case 'OWNER':
        return redirect('/brief');
      case 'FINANCE_HEAD':
        return redirect('/petty-cash');
      case 'PROJECT_MANAGER':
      case 'SITE_ENGINEER':
        return redirect('/dpr');
      case 'SUPERVISOR':
        return redirect('/attendance');
      default:
        return redirect('/brief');
    }
  }

  // Any unauthenticated device reaching the site must be directed to login
  return redirect('/login');
}
