import api from './api';
import type { CreateUnitRequest, Unit, UpdateUnitRequest } from '@/types/unit';

export const unitsApi = {
  async list(includeInactive = false, signal?: AbortSignal): Promise<Unit[]> {
    const response = await api.get<Unit[]>('/units', {
      params: { include_inactive: includeInactive },
      signal,
    });
    return response.data;
  },
  async create(payload: CreateUnitRequest): Promise<Unit> {
    const response = await api.post<Unit>('/units', payload);
    return response.data;
  },
  async update(unitId: string, payload: UpdateUnitRequest): Promise<Unit> {
    const response = await api.patch<Unit>(`/units/${unitId}`, payload);
    return response.data;
  },
};
