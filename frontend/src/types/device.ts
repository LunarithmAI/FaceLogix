export type DeviceType = 'kiosk' | 'tablet' | 'mobile' | 'web';

export interface DeviceSettings {
  camera_facing?: 'user' | 'environment';
  auto_capture?: boolean;
  capture_delay_ms?: number;
  require_liveness?: boolean;
  allow_check_in?: boolean;
  allow_check_out?: boolean;
  [key: string]: unknown;
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

export interface DeviceInfo {
  device_id: string;
  user_agent: string;
  platform: string;
  screen_width: number;
  screen_height: number;
}
