import api from './api';
import type { 
  CheckInResult, 
  BackendCheckInResponse,
  CheckStatus,
  AttendanceLog, 
  DailySummary, 
  AttendanceListParams,
  AttendanceStats 
} from '@/types/attendance';
import type { PaginatedResponse } from '@/types/api';

/**
 * Transform backend check-in response to frontend format
 */
function transformCheckInResponse(
  response: BackendCheckInResponse, 
  checkType: 'check_in' | 'check_out'
): CheckInResult {
  // Map backend status to frontend display status
  let status: CheckStatus;
  
  if (response.success) {
    status = 'success';
  } else {
    switch (response.status) {
      case 'unknown_user':
        status = 'not_recognized';
        break;
      case 'already_checked_in':
        status = 'already_checked';
        break;
      case 'no_face_detected':
        status = 'no_face_detected';
        break;
      default:
        status = 'failed';
    }
  }

  return {
    status,
    message: response.message,
    user_name: response.user_name,
    check_type: checkType,
    timestamp: response.check_in_time,
    confidence: response.confidence_score,
  };
}

export const attendanceApi = {
  checkIn: async (imageData: string, deviceId?: string): Promise<CheckInResult> => {
    const response = await api.post<BackendCheckInResponse>('/attendance/check-in', {
      image: imageData,
      device_id: deviceId,
      timestamp: new Date().toISOString(),
    });
    return transformCheckInResponse(response.data, 'check_in');
  },

  checkOut: async (imageData: string, deviceId?: string): Promise<CheckInResult> => {
    const response = await api.post<BackendCheckInResponse>('/attendance/check-out', {
      image: imageData,
      device_id: deviceId,
      timestamp: new Date().toISOString(),
    });
    return transformCheckInResponse(response.data, 'check_out');
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
