import { create } from "zustand";
import { api, ApiError } from "@/lib/api";

export interface AuthUser {
  id: string;
  email: string;
  displayName: string;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => void;
}

interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  user: AuthUser;
}

interface RegisterResponse {
  access_token: string;
  refresh_token?: string;
  user: AuthUser;
}

export const useAuthStore = create<AuthState & AuthActions>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.post<LoginResponse>("/api/v1/auth/login", {
        email,
        password,
      });

      localStorage.setItem("token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("refresh_token", data.refresh_token);
      }
      localStorage.setItem("user", JSON.stringify(data.user));

      set({
        user: data.user,
        token: data.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? (err.data as { detail?: string })?.detail || err.statusText
          : "Wystąpił nieoczekiwany błąd";
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  register: async (email: string, password: string, displayName: string) => {
    set({ isLoading: true, error: null });
    try {
      const data = await api.post<RegisterResponse>("/api/v1/auth/register", {
        email,
        password,
        display_name: displayName,
      });

      localStorage.setItem("token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("refresh_token", data.refresh_token);
      }
      localStorage.setItem("user", JSON.stringify(data.user));

      set({
        user: data.user,
        token: data.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      const message =
        err instanceof ApiError
          ? (err.data as { detail?: string })?.detail || err.statusText
          : "Wystąpił nieoczekiwany błąd";
      set({ isLoading: false, error: message });
      throw err;
    }
  },

  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      error: null,
    });
  },

  loadFromStorage: () => {
    if (typeof window === "undefined") return;

    const token = localStorage.getItem("token");
    const userJson = localStorage.getItem("user");

    if (token && userJson) {
      try {
        const user = JSON.parse(userJson) as AuthUser;
        set({
          user,
          token,
          isAuthenticated: true,
        });
      } catch {
        localStorage.removeItem("token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
      }
    }
  },
}));
