import { QueryClient } from '@tanstack/react-query';
import { ApiClientError } from '@/services/apiError';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (error instanceof ApiClientError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 1;
      },
    },
    mutations: {
      retry: false,
    },
  },
});

export const queryKeys = {
  dashboard: ['dashboard'] as const,
  users: (params: object) => ['users', params] as const,
  devices: (params: object) => ['devices', params] as const,
  attendance: (params: object) => ['attendance', params] as const,
  reports: (params: object) => ['reports', params] as const,
  settings: ['settings'] as const,
  system: ['system'] as const,
  profile: ['profile'] as const,
};
