import api from './api';

// Organization settings interface
export interface OrgSettings {
  id: string;
  name: string;
  slug: string;
  timezone: string;
  is_active: boolean;
  settings: {
    work_start_time: string;
    work_end_time: string;
    late_threshold_minutes: number;
    require_liveness: boolean;
    liveness_threshold: number;
    face_match_threshold: number;
  };
  created_at: string;
  updated_at: string;
}

export interface OrgSettingsUpdate {
  name?: string;
  timezone?: string;
  settings?: {
    work_start_time?: string;
    work_end_time?: string;
    late_threshold_minutes?: number;
    require_liveness?: boolean;
    liveness_threshold?: number;
    face_match_threshold?: number;
  };
}

export interface SystemInfo {
  version: string;
  environment: string;
  face_service_status: 'online' | 'offline' | 'unknown';
  database_status: 'connected' | 'disconnected';
  total_users: number;
  total_devices: number;
  uptime_hours: number;
}

export const settingsApi = {
  // Get current organization settings
  getOrgSettings: async (signal?: AbortSignal): Promise<OrgSettings> => {
    const response = await api.get<OrgSettings>('/settings/org', { signal });
    return response.data;
  },

  // Update organization settings
  updateOrgSettings: async (data: OrgSettingsUpdate): Promise<OrgSettings> => {
    const response = await api.patch<OrgSettings>('/settings/org', data);
    return response.data;
  },

  // Get system info
  getSystemInfo: async (signal?: AbortSignal): Promise<SystemInfo> => {
    const response = await api.get<SystemInfo>('/settings/system', { signal });
    return response.data;
  },

  // Test face service connection
  testFaceService: async (): Promise<{ status: string; latency_ms: number }> => {
    const response = await api.get<{ status: string; latency_ms: number }>(
      '/settings/test-face-service'
    );
    return response.data;
  },
};

export default settingsApi;
