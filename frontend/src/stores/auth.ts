import { defineStore } from 'pinia';
import { api } from '@/api';
import type { User } from '@/api/types';

const STORAGE_KEY = 'proxyops.session';

interface State {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
}

export const useAuthStore = defineStore('auth', {
  state: (): State => ({
    accessToken: null,
    refreshToken: null,
    user: null,
  }),

  getters: {
    isAuthenticated: (s) => !!s.accessToken,
    canEdit: (s) => s.user?.role === 'admin' || s.user?.role === 'operator',
    isAdmin: (s) => s.user?.role === 'admin',
  },

  actions: {
    hydrate() {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      try {
        const parsed = JSON.parse(raw);
        this.accessToken = parsed.accessToken ?? null;
        this.refreshToken = parsed.refreshToken ?? null;
        this.user = parsed.user ?? null;
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    },

    persist() {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          accessToken: this.accessToken,
          refreshToken: this.refreshToken,
          user: this.user,
        }),
      );
    },

    async login(email: string, password: string) {
      const { access_token, refresh_token } = await api.login(email, password);
      this.accessToken = access_token;
      this.refreshToken = refresh_token;
      this.user = await api.me();
      this.persist();
    },

    async refresh(): Promise<string | null> {
      if (!this.refreshToken) return null;
      try {
        const { access_token, refresh_token } = await api.refresh(this.refreshToken);
        this.accessToken = access_token;
        this.refreshToken = refresh_token;
        this.persist();
        return access_token;
      } catch {
        this.logout();
        return null;
      }
    },

    async fetchMe() {
      this.user = await api.me();
      this.persist();
    },

    logout() {
      this.accessToken = null;
      this.refreshToken = null;
      this.user = null;
      localStorage.removeItem(STORAGE_KEY);
    },
  },
});
