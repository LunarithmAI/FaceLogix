export type DeviceType = 'kiosk' | 'tablet' | 'mobile' | 'web';
export type DeviceMode = 'check_in' | 'check_out';
export type CameraFacing = 'user' | 'environment';

export interface DeviceSettings {
  allow_check_in: boolean;
  allow_check_out: boolean;
  default_mode: DeviceMode;
  camera_facing: CameraFacing;
}

export interface Device {
  id: string;
  org_id: string;
  name: string;
  location: string | null;
  device_type: DeviceType;
  is_active: boolean;
  last_seen_at: string | null;
  settings: DeviceSettings;
  created_at: string;
  updated_at: string;
}

export interface DeviceCredential extends Device {
  device_secret: string;
}

export interface DeviceRegistration {
  name: string;
  device_type: DeviceType;
  location?: string;
  settings?: DeviceSettings;
}

export interface DeviceLoginCredentials {
  device_id: string;
  device_secret: string;
}

export interface DeviceLoginResponse {
  device_token: string;
  token_type: string;
  device_id: string;
  org_id: string;
  device_name: string;
  settings: DeviceSettings;
}

export interface DeviceInfo {
  device_id: string;
  user_agent: string;
  platform: string;
  screen_width: number;
  screen_height: number;
}
