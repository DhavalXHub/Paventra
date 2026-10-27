import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { User, AuthTokens } from '../../types';
import api from '../../lib/api';
interface AuthState {
  user: User | null;
  token: string | null;
  role: string | null;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (payload: string | { credential: string; link_existing?: boolean; password_for_linking?: string }) => Promise<User>;
  logout: () => void;
  isAuthenticated: boolean;
  isCoordinator: boolean;
  isRepairTeam: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(() => ({
    token: localStorage.getItem('access_token'),
    role: localStorage.getItem('user_role'),
    user: null,
  }));

  const login = useCallback(async (email: string, password: string) => {
    const res = await api.post<AuthTokens>('/auth/login', { email, password });
    const { access_token, refresh_token, role } = res.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    localStorage.setItem('user_role', role);

    const meRes = await api.get<User>('/auth/me', {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    setState({ token: access_token, role, user: meRes.data });
  }, []);

  const loginWithGoogle = useCallback(
    async (payload: string | { credential: string; link_existing?: boolean; password_for_linking?: string }): Promise<User> => {
      const body = typeof payload === 'string' ? { credential: payload } : payload;
      const res = await api.post<AuthTokens>('/auth/google', body);
      const { access_token, refresh_token, role } = res.data;
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      localStorage.setItem('user_role', role);

      const meRes = await api.get<User>('/auth/me', {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      setState({ token: access_token, role, user: meRes.data });
      return meRes.data;
    },
    []
  );

  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_role');
    setState({ token: null, role: null, user: null });
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    api.get<User>('/auth/me')
      .then((res) => {
        setState((prev) => ({
          ...prev,
          user: res.data,
          role: res.data.role,
          token,
        }));
        localStorage.setItem('user_role', res.data.role);
      })
      .catch(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_role');
        setState({ token: null, role: null, user: null });
      });
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        loginWithGoogle,
        logout,
        isAuthenticated: !!state.token,
        isCoordinator: state.role === 'coordinator' || state.role === 'admin',
        isRepairTeam: state.role === 'repair_team',
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
