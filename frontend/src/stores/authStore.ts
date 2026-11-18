import { create } from 'zustand';
import { User } from '../types';
import { api } from '../api/endpoints';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, refreshToken: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('codesage_access_token'),
  isLoading: true,

  login: async (accessToken: string, refreshToken: string) => {
    localStorage.setItem('codesage_access_token', accessToken);
    localStorage.setItem('codesage_refresh_token', refreshToken);
    set({ token: accessToken });
    try {
      const res = await api.auth.getMe();
      set({ user: res.data, isLoading: false });
    } catch {
      set({ user: null, isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem('codesage_access_token');
    localStorage.removeItem('codesage_refresh_token');
    set({ user: null, token: null, isLoading: false });
  },

  loadUser: async () => {
    const token = localStorage.getItem('codesage_access_token');
    if (!token) {
      set({ user: null, token: null, isLoading: false });
      return;
    }
    try {
      const res = await api.auth.getMe();
      set({ user: res.data, isLoading: false });
    } catch {
      localStorage.removeItem('codesage_access_token');
      localStorage.removeItem('codesage_refresh_token');
      set({ user: null, token: null, isLoading: false });
    }
  },
}));
