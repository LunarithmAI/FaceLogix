export type DeviceStatus = 'active' | 'inactive' | 'pending';

export type DeviceType = 'kiosk' | 'mobile' | 'web';

export interface Device {
  id: string;
  name: string;
  type: DeviceType;
  status: DeviceStatus;
  organization_id: string;
  location?: string;
  last_active_at?: string;
  registered_at: string;
  ip_address?: string;
  user_agent?: string;
  settings?: DeviceSettings;
}

export interface DeviceSettings {
  camera_facing?: 'user' | 'environment';
  auto_capture?: boolean;
  capture_delay_ms?: number;
  require_liveness?: boolean;
  allow_check_in?: boolean;
  allow_check_out?: boolean;
}

export interface DeviceRegistration {
  name: string;
  type: DeviceType;
  location?: string;
}

export interface DeviceInfo {
  device_id: string;
  user_agent: string;
  platform: string;
  screen_width: number;
  screen_height: number;
}
