import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User, AuthTokens, LoginCredentials, LoginResponse } from '@/types/auth';
import { authApi } from '@/services/auth';

interface AuthStore {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<boolean>;
  setTokens: (tokens: AuthTokens) => void;
  setUser: (user: User) => void;
  clearError: () => void;
  reset: () => void;
}

const initialState = {
  user: null,
  tokens: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
};

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      login: async (credentials: LoginCredentials) => {
        set({ isLoading: true, error: null });
        try {
          const response: LoginResponse = await authApi.login(credentials);
          
          // Build user and tokens from flat response
          const user: User = {
            id: response.user_id,
            name: response.name,
            role: response.role,
            org_id: response.org_id,
          };
          
          const tokens: AuthTokens = {
            access_token: response.access_token,
            refresh_token: response.refresh_token,
            token_type: response.token_type,
          };
          
          set({
            user,
            tokens,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Login failed';
          set({ isLoading: false, error: message });
          throw error;
        }
      },

      logout: async () => {
        const { tokens } = get();
        set({ isLoading: true });
        try {
          if (tokens?.refresh_token) {
            await authApi.logout(tokens.refresh_token);
          }
        } catch {
          // Ignore logout errors
        } finally {
          set({ ...initialState });
        }
      },

      refreshToken: async () => {
        const { tokens } = get();
        if (!tokens?.refresh_token) {
          set({ ...initialState });
          return false;
        }

        try {
          const response = await authApi.refresh(tokens.refresh_token);
          set({
            tokens: {
              ...tokens,
              access_token: response.access_token,
            },
          });
          return true;
        } catch {
          set({ ...initialState });
          return false;
        }
      },

      setTokens: (tokens: AuthTokens) => {
        set({ tokens, isAuthenticated: true });
      },

      setUser: (user: User) => {
        set({ user });
      },

      clearError: () => {
        set({ error: null });
      },

      reset: () => {
        set({ ...initialState });
      },
    }),
    {
      name: 'facelogix-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
