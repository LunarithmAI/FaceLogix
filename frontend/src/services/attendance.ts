import api from './api';
import type { 
  CheckInResult, 
  AttendanceLog, 
  DailySummary, 
  AttendanceListParams,
  AttendanceStats 
} from '@/types/attendance';
import type { PaginatedResponse } from '@/types/api';

export const attendanceApi = {
  checkIn: async (imageData: string, deviceId?: string): Promise<CheckInResult> => {
    const response = await api.post<CheckInResult>('/attendance/check-in', {
      image: imageData,
      device_id: deviceId,
      timestamp: new Date().toISOString(),
    });
    return response.data;
  },

  checkOut: async (imageData: string, deviceId?: string): Promise<CheckInResult> => {
    const response = await api.post<CheckInResult>('/attendance/check-out', {
      image: imageData,
      device_id: deviceId,
      timestamp: new Date().toISOString(),
    });
    return response.data;
  },

  list: async (params?: AttendanceListParams): Promise<PaginatedResponse<AttendanceLog>> => {
    const response = await api.get<PaginatedResponse<AttendanceLog>>('/attendance', {
      params: {
        page: params?.page || 1,
        limit: params?.limit || 20,
        start_date: params?.start_date,
        end_date: params?.end_date,
        user_id: params?.user_id,
        check_type: params?.check_type,
      },
    });
    return response.data;
  },

  getDailySummary: async (date?: string): Promise<DailySummary> => {
    const response = await api.get<DailySummary>('/attendance/summary/daily', {
      params: { date: date || new Date().toISOString().split('T')[0] },
    });
    return response.data;
  },

  getStats: async (userId?: string): Promise<AttendanceStats> => {
    const response = await api.get<AttendanceStats>('/attendance/stats', {
      params: { user_id: userId },
    });
    return response.data;
  },

  getMyAttendance: async (params?: AttendanceListParams): Promise<PaginatedResponse<AttendanceLog>> => {
    const response = await api.get<PaginatedResponse<AttendanceLog>>('/attendance/me', {
      params,
    });
    return response.data;
  },
};

export default attendanceApi;
