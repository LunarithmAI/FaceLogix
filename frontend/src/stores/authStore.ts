import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { clearPrivateClientState } from '@/lib/session';
import { authApi } from '@/services/auth';
import type {
  AuthSession,
  AuthTokens,
  LoginCredentials,
  LoginResponse,
  User,
} from '@/types/auth';
import type { DeviceLoginCredentials } from '@/types/device';

interface AuthStore {
  session: AuthSession | null;
  isLoading: boolean;
  error: string | null;
  loginUser: (credentials: LoginCredentials) => Promise<void>;
  loginDevice: (credentials: DeviceLoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  setAccessToken: (accessToken: string) => void;
  setUser: (user: User) => void;
  clearError: () => void;
  reset: () => void;
}

const initialState = {
  session: null,
  isLoading: false,
  error: null,
};

export function sessionAccessToken(session: AuthSession | null): string | null {
  if (session === null) return null;
  return session.kind === 'user' ? session.tokens.access_token : session.access_token;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      loginUser: async (credentials) => {
        set({ isLoading: true, error: null });
        try {
          clearPrivateClientState();
          const response: LoginResponse = await authApi.login(credentials);
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
          set({ session: { kind: 'user', user, tokens }, isLoading: false, error: null });
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Login failed';
          set({ isLoading: false, error: message });
          throw error;
        }
      },

      loginDevice: async (credentials) => {
        set({ isLoading: true, error: null });
        try {
          clearPrivateClientState();
          const response = await authApi.deviceLogin(credentials);
          set({
            session: {
              kind: 'device',
              device: {
                id: response.device_id,
                org_id: response.org_id,
                name: response.device_name,
                settings: response.settings,
              },
              access_token: response.device_token,
              token_type: response.token_type,
            },
            isLoading: false,
            error: null,
          });
        } catch (error) {
          const message = error instanceof Error ? error.message : 'Device login failed';
          set({ isLoading: false, error: message });
          throw error;
        }
      },

      logout: async () => {
        const { session } = get();
        set({ isLoading: true });
        try {
          if (session?.kind === 'user') {
            await authApi.logout(session.tokens.refresh_token);
          }
        } catch {
          // Local session invalidation must still complete when revocation is unavailable.
        } finally {
          clearPrivateClientState();
          set({ ...initialState });
        }
      },

      setAccessToken: (accessToken) => {
        set((state) => {
          if (state.session?.kind !== 'user') return state;
          return {
            session: {
              ...state.session,
              tokens: { ...state.session.tokens, access_token: accessToken },
            },
          };
        });
      },

      setUser: (user) => {
        set((state) => {
          if (state.session?.kind !== 'user') return state;
          return { session: { ...state.session, user } };
        });
      },

      clearError: () => set({ error: null }),
      reset: () => {
        set({ ...initialState });
        clearPrivateClientState();
      },
    }),
    {
      name: 'facelogix-auth',
      version: 2,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ session: state.session }),
      migrate: () => ({ ...initialState }),
    }
  )
);
