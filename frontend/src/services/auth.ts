import api from './api';
import type { 
  LoginCredentials, 
  LoginResponse, 
  RefreshTokenResponse 
} from '@/types/auth';

export const authApi = {
  login: async (credentials: LoginCredentials): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/login', credentials, {
      headers: { 'Skip-Auth': 'true' },
    });
    return response.data;
  },

  refresh: async (refreshToken: string): Promise<RefreshTokenResponse> => {
    const response = await api.post<RefreshTokenResponse>(
      '/auth/refresh',
      { refresh_token: refreshToken },
      { headers: { 'Skip-Auth': 'true' } }
    );
    return response.data;
  },

  logout: async (refreshToken: string): Promise<void> => {
    await api.post('/auth/logout', { refresh_token: refreshToken });
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
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
