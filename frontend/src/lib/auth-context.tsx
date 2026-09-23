'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import apiClient from './api-client';

export interface UserSession {
  id: number;
  name: string;
  email: string | null;
  phone: string;
  role: string;
  is_active: boolean;
}

interface AuthContextType {
  user: UserSession | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (accessToken: string, refreshToken?: string) => Promise<void>;
  logout: () => void;
  refreshUserProfile: () => Promise<UserSession | null>;
}

export function setAuthCookie(token: string) {
  if (typeof document !== 'undefined') {
    document.cookie = `auth_token=${token}; path=/; max-age=604800; SameSite=Lax`;
  }
}

export function clearAuthCookie() {
  if (typeof document !== 'undefined') {
    document.cookie = 'auth_token=; path=/; max-age=0; SameSite=Lax';
  }
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isLoading: true,
  isAuthenticated: false,
  login: async () => {},
  logout: () => {},
  refreshUserProfile: async () => null,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<UserSession | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      clearAuthCookie();
    }
    setToken(null);
    setUser(null);
    router.push('/login');
  }, [router]);

  const refreshUserProfile = useCallback(async (): Promise<UserSession | null> => {
    try {
      const res = await apiClient.get('/auth/me');
      if (res.data) {
        setUser(res.data);
        if (typeof window !== 'undefined') {
          localStorage.setItem('user', JSON.stringify(res.data));
        }
        return res.data;
      }
      return null;
    } catch (err: unknown) {
      console.warn('Failed to fetch user profile:', err);
      return null;
    }
  }, []);

  const login = useCallback(async (accessToken: string, refreshToken?: string) => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', accessToken);
      if (refreshToken) {
        localStorage.setItem('refreshToken', refreshToken);
      }
      setAuthCookie(accessToken);
    }
    setToken(accessToken);
    await refreshUserProfile();
  }, [refreshUserProfile]);

  useEffect(() => {
    const initAuth = async () => {
      if (typeof window === 'undefined') return;
      const storedToken = localStorage.getItem('token');
      const storedUser = localStorage.getItem('user');

      // If no token exists on this device, user is unauthenticated
      if (!storedToken) {
        clearAuthCookie();
        setToken(null);
        setUser(null);
        setIsLoading(false);
        return;
      }

      setToken(storedToken);
      setAuthCookie(storedToken);

      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch {
          // ignore corrupted JSON
        }
      }

      // Validate session with the backend server
      try {
        const res = await apiClient.get('/auth/me');
        if (res.data) {
          setUser(res.data);
          localStorage.setItem('user', JSON.stringify(res.data));
        }
      } catch (err: unknown) {
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          // Try refresh token if available on this device
          const storedRefreshToken = localStorage.getItem('refreshToken');
          if (storedRefreshToken) {
            try {
              const refreshRes = await apiClient.post('/auth/refresh', {
                refresh_token: storedRefreshToken,
              });
              if (refreshRes.data?.access_token) {
                const newToken = refreshRes.data.access_token;
                localStorage.setItem('token', newToken);
                setAuthCookie(newToken);
                setToken(newToken);
                const userRes = await apiClient.get('/auth/me');
                if (userRes.data) {
                  setUser(userRes.data);
                  localStorage.setItem('user', JSON.stringify(userRes.data));
                }
                setIsLoading(false);
                return;
              }
            } catch {
              // Refresh failed
            }
          }
          // Invalidate session on this device
          if (typeof window !== 'undefined') {
            localStorage.removeItem('token');
            localStorage.removeItem('refreshToken');
            localStorage.removeItem('user');
            clearAuthCookie();
          }
          setToken(null);
          setUser(null);
        }
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!token && !!user,
        login,
        logout,
        refreshUserProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
