import api from './api';
import type { CreateShiftRequest, Shift, UpdateShiftRequest } from '@/types/shift';

export const shiftsApi = {
  async list(includeInactive = false, signal?: AbortSignal): Promise<Shift[]> {
    const response = await api.get<Shift[]>('/shifts', {
      params: { include_inactive: includeInactive },
      signal,
    });
    return response.data;
  },
  async create(payload: CreateShiftRequest): Promise<Shift> {
    const response = await api.post<Shift>('/shifts', payload);
    return response.data;
  },
  async update(shiftId: string, payload: UpdateShiftRequest): Promise<Shift> {
    const response = await api.patch<Shift>(`/shifts/${shiftId}`, payload);
    return response.data;
  },
  async assignUnit(unitId: string, shiftId: string | null, effectiveFrom: string): Promise<void> {
    await api.put(`/units/${unitId}/shift-assignment`, {
      shift_id: shiftId,
      effective_from: effectiveFrom,
    });
  },
};
