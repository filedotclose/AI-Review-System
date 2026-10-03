import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export default function Home() {
  const cookieStore = cookies();
  const token = cookieStore.get('auth_token')?.value;
  const role = cookieStore.get('user_role')?.value;

  if (token) {
    switch (role) {
      case 'OWNER':
        redirect('/brief');
      case 'FINANCE_HEAD':
        redirect('/petty-cash');
      case 'PROJECT_MANAGER':
      case 'SITE_ENGINEER':
        redirect('/dpr');
      case 'SUPERVISOR':
        redirect('/attendance');
      default:
        redirect('/brief');
    }
  }

  // Any unauthenticated device reaching the site must be directed to login
  redirect('/login');
}
