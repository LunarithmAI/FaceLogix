import type { UserRole } from '@/types/roles';

export interface User {
  id: string;
  email?: string;
  name: string;
  role: UserRole;
  org_id: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface LoginCredentials {
  organization: string;
  email: string;
  password: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Backend returns flat response with user info and tokens together
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  org_id: string;
  role: UserRole;
  name: string;
}

export interface UserProfile {
  id: string;
  org_id: string;
  email: string | null;
  name: string;
  role: UserRole;
  department: string | null;
  is_active: boolean;
  enrolled_at: string | null;
  created_at: string;
}

export interface RefreshTokenRequest {
  refresh_token: string;
}

export interface RefreshTokenResponse {
  access_token: string;
  token_type: string;
}
