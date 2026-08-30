import api from './api';
import type { Device, DeviceCredential, DeviceRegistration, DeviceType } from '@/types/device';

const DEVICES_BASE = '/devices';

export interface DeviceListParams {
  page?: number;
  page_size?: number;
  is_active?: boolean;
  device_type?: DeviceType;
  search?: string;
}

export interface DeviceListResponse {
  items: Device[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export const devicesApi = {
  async list(params: DeviceListParams = {}, signal?: AbortSignal): Promise<DeviceListResponse> {
    const response = await api.get<DeviceListResponse>(DEVICES_BASE, { params, signal });
    return response.data;
  },

  async register(data: DeviceRegistration): Promise<DeviceCredential> {
    const response = await api.post<DeviceCredential>(DEVICES_BASE, data);
    return response.data;
  },

  async update(deviceId: string, data: Partial<DeviceRegistration>): Promise<Device> {
    const response = await api.patch<Device>(`${DEVICES_BASE}/${deviceId}`, data);
    return response.data;
  },

  async delete(deviceId: string): Promise<void> {
    await api.delete(`${DEVICES_BASE}/${deviceId}`);
  },

  async activate(deviceId: string): Promise<Device> {
    const response = await api.post<Device>(`${DEVICES_BASE}/${deviceId}/activate`);
    return response.data;
  },

  async deactivate(deviceId: string): Promise<Device> {
    const response = await api.post<Device>(`${DEVICES_BASE}/${deviceId}/deactivate`);
    return response.data;
  },
};

export default devicesApi;
