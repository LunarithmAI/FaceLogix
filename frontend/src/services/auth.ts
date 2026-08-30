import api from './api';
import type { LoginCredentials, LoginResponse, UserProfile } from '@/types/auth';

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/login', credentials);
    return response.data;
  },

  logout: async (refreshToken: string): Promise<void> => {
    await api.post('/auth/logout', { refresh_token: refreshToken });
  },

  getCurrentUser: async (signal?: AbortSignal): Promise<UserProfile> => {
    const response = await api.get<UserProfile>('/auth/me', { signal });
    return response.data;
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  },
};

export default authApi;
