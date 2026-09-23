import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';

export default function Home() {
  const cookieStore = cookies();
  const token = cookieStore.get('auth_token')?.value;

  if (token) {
    redirect('/brief');
  }

  // Any unauthenticated device reaching the site must be directed to login
  redirect('/login');
}
