import api from './api';

export type CalendarExceptionKind = 'holiday' | 'working_day';

export interface CalendarException {
  id: string;
  org_id: string;
  unit_id: string | null;
  exception_date: string;
  kind: CalendarExceptionKind;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface CalendarExceptionPayload {
  unit_id: string | null;
  exception_date: string;
  kind: CalendarExceptionKind;
  name: string;
}

export const calendarApi = {
  async list(fromDate?: string, toDate?: string, signal?: AbortSignal): Promise<CalendarException[]> {
    const response = await api.get<CalendarException[]>('/calendar-exceptions', {
      params: { from_date: fromDate, to_date: toDate },
      signal,
    });
    return response.data;
  },
  async create(payload: CalendarExceptionPayload): Promise<CalendarException> {
    const response = await api.post<CalendarException>('/calendar-exceptions', payload);
    return response.data;
  },
  async update(id: string, payload: Partial<CalendarExceptionPayload>): Promise<CalendarException> {
    const response = await api.patch<CalendarException>(`/calendar-exceptions/${id}`, payload);
    return response.data;
  },
  async remove(id: string): Promise<void> {
    await api.delete(`/calendar-exceptions/${id}`);
  },
};
