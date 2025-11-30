import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/stores/authStore';
import type { ApiError } from '@/types/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { tokens } = useAuthStore.getState();
    
    if (tokens?.access_token && !config.headers['Skip-Auth']) {
      config.headers.Authorization = `Bearer ${tokens.access_token}`;
    }
    
    delete config.headers['Skip-Auth'];
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    
    // Handle 401 errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const { refreshToken, reset } = useAuthStore.getState();
      const success = await refreshToken();
      
      if (success) {
        const { tokens } = useAuthStore.getState();
        if (tokens?.access_token) {
          originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
          return api(originalRequest);
        }
      }
      
      // Refresh failed, logout user
      reset();
      window.location.href = '/login';
    }
    
    // Format error response
    const apiError: ApiError = {
      status: error.response?.status || 500,
      code: error.response?.data?.code || 'UNKNOWN_ERROR',
      message: error.response?.data?.message || error.message || 'An unexpected error occurred',
      details: error.response?.data?.details,
    };
    
    return Promise.reject(apiError);
  }
);

export default api;
