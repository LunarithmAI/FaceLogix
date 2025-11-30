import api from './api';
import type { Device, DeviceRegistration, DeviceSettings, DeviceStatus } from '@/types/device';

const DEVICES_BASE = '/devices';

export interface DeviceListParams {
  page?: number;
  limit?: number;
  status?: DeviceStatus;
  type?: string;
  search?: string;
}

export interface DeviceListResponse {
  items: Device[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export const devicesApi = {
  /**
   * Get paginated list of devices
   */
  async list(params: DeviceListParams = {}): Promise<DeviceListResponse> {
    const response = await api.get<DeviceListResponse>(DEVICES_BASE, { params });
    return response.data;
  },

  /**
   * Get a single device by ID
   */
  async get(deviceId: string): Promise<Device> {
    const response = await api.get<Device>(`${DEVICES_BASE}/${deviceId}`);
    return response.data;
  },

  /**
   * Register a new device
   */
  async register(data: DeviceRegistration): Promise<Device> {
    const response = await api.post<Device>(DEVICES_BASE, data);
    return response.data;
  },

  /**
   * Update device details
   */
  async update(deviceId: string, data: Partial<DeviceRegistration>): Promise<Device> {
    const response = await api.patch<Device>(`${DEVICES_BASE}/${deviceId}`, data);
    return response.data;
  },

  /**
   * Delete a device
   */
  async delete(deviceId: string): Promise<void> {
    await api.delete(`${DEVICES_BASE}/${deviceId}`);
  },

  /**
   * Activate a device
   */
  async activate(deviceId: string): Promise<Device> {
    const response = await api.post<Device>(`${DEVICES_BASE}/${deviceId}/activate`);
    return response.data;
  },

  /**
   * Deactivate a device
   */
  async deactivate(deviceId: string): Promise<Device> {
    const response = await api.post<Device>(`${DEVICES_BASE}/${deviceId}/deactivate`);
    return response.data;
  },

  /**
   * Update device settings
   */
  async updateSettings(deviceId: string, settings: DeviceSettings): Promise<Device> {
    const response = await api.patch<Device>(`${DEVICES_BASE}/${deviceId}/settings`, settings);
    return response.data;
  },

  /**
   * Get device heartbeat/status
   */
  async heartbeat(deviceId: string): Promise<{ status: string; last_active_at: string }> {
    const response = await api.post<{ status: string; last_active_at: string }>(
      `${DEVICES_BASE}/${deviceId}/heartbeat`
    );
    return response.data;
  },
};

export default devicesApi;
