import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/authStore';
import type { RefreshTokenResponse } from '@/types/auth';
import { normalizeApiError } from '@/services/apiError';

const API_BASE_URL = '/api/v1';

type RetryableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
});

let refreshPromise: Promise<string | null> | null = null;

function isSessionEndpoint(url: string | undefined): boolean {
  return url?.includes('/auth/login') === true || url?.includes('/auth/refresh') === true;
}

async function refreshAccessToken(): Promise<string | null> {
  const { tokens, setTokens } = useAuthStore.getState();
  if (!tokens?.refresh_token) {
    return null;
  }
  try {
    const response = await axios.post<RefreshTokenResponse>(
      `${API_BASE_URL}/auth/refresh`,
      { refresh_token: tokens.refresh_token },
      { timeout: 30_000 }
    );
    setTokens({ ...tokens, access_token: response.data.access_token });
    return response.data.access_token;
  } catch {
    return null;
  }
}

api.interceptors.request.use(
  (config) => {
    const { tokens } = useAuthStore.getState();
    if (tokens?.access_token && !isSessionEndpoint(config.url)) {
      config.headers.Authorization = `Bearer ${tokens.access_token}`;
    }
    return config;
  },
  (error: unknown) => Promise.reject(normalizeApiError(error))
);

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<unknown>) => {
    const originalRequest = error.config as RetryableRequestConfig | undefined;
    const isUnauthorized = error.response?.status === 401;
    if (
      isUnauthorized &&
      originalRequest !== undefined &&
      !originalRequest._retry &&
      !isSessionEndpoint(originalRequest.url)
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
      useAuthStore.getState().reset();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    } else if (isUnauthorized && originalRequest?._retry === true) {
      useAuthStore.getState().reset();
    }
    throw normalizeApiError(error);
  }
);

export default api;
