import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "../types";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  login: (tokens: { access_token: string; refresh_token: string }, user: User) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      login: (tokens, user) =>
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          user,
        }),
      logout: () =>
        set({ accessToken: null, refreshToken: null, user: null }),
      isAuthenticated: () => !!get().accessToken,
    }),
    { name: "haofang-auth" }
  )
);
