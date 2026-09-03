import type { DeviceSettings } from '@/types/device';
import type { ShiftSummary } from '@/types/shift';
import type { UnitSummary } from '@/types/unit';
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

export interface LoginResponse extends AuthTokens {
  user_id: string;
  org_id: string;
  role: UserRole;
  name: string;
}

export interface HumanSession {
  kind: 'user';
  user: User;
  tokens: AuthTokens;
}

export interface DevicePrincipal {
  id: string;
  org_id: string;
  name: string;
  settings: DeviceSettings;
}

export interface DeviceSession {
  kind: 'device';
  device: DevicePrincipal;
  access_token: string;
  token_type: string;
}

export type AuthSession = HumanSession | DeviceSession;

export interface UserProfile {
  id: string;
  org_id: string;
  email: string | null;
  name: string;
  role: UserRole;
  current_unit: UnitSummary | null;
  current_shift: ShiftSummary | null;
  managed_units: UnitSummary[];
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
