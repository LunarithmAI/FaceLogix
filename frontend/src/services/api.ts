import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { normalizeApiError } from '@/services/apiError';
import { sessionAccessToken, useAuthStore } from '@/stores/authStore';
import type { RefreshTokenResponse } from '@/types/auth';

const API_BASE_URL = '/api/v1';

type RetryableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

let refreshPromise: Promise<string | null> | null = null;

function isSessionEndpoint(url: string | undefined): boolean {
  return url?.includes('/auth/login') === true ||
    url?.includes('/auth/devices/login') === true ||
    url?.includes('/auth/refresh') === true;
}

async function refreshAccessToken(): Promise<string | null> {
  const { session, setAccessToken } = useAuthStore.getState();
  if (session?.kind !== 'user') return null;
  try {
    const response = await axios.post<RefreshTokenResponse>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: session.tokens.refresh_token },
      { timeout: 30_000 }
    );
    setAccessToken(response.data.access_token);
    return response.data.access_token;
  } catch {
    return null;
  }
}

api.interceptors.request.use(
  (config) => {
    const token = sessionAccessToken(useAuthStore.getState().session);
    if (token && !isSessionEndpoint(config.url)) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: unknown) => Promise.reject(normalizeApiError(error))
);

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<unknown>) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;
    const session = useAuthStore.getState().session;
    const canRefresh = session?.kind === 'user';
    if (
      error.response?.status === 401 &&
      originalRequest !== undefined &&
      !originalRequest._retry &&
      !isSessionEndpoint(originalRequest.url) &&
      canRefresh
    ) {
      originalRequest._retry = true;
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
      const accessToken = await refreshPromise;
      if (accessToken !== null) {
        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return api(originalRequest);
      }
    }
    if (error.response?.status === 401 && !isSessionEndpoint(originalRequest?.url)) {
      useAuthStore.getState().reset();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }
    throw normalizeApiError(error);
  }
);

export default api;
