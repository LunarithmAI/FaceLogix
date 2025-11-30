import api from './api';
import type { AttendanceLog, AttendanceListParams, DailySummary, AttendanceStats } from '@/types/attendance';

const REPORTS_BASE = '/reports';
const ATTENDANCE_BASE = '/attendance';

export interface AttendanceListResponse {
  items: AttendanceLog[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface DashboardStats {
  today: DailySummary;
  total_users: number;
  active_devices: number;
  pending_enrollments: number;
  recent_activity: AttendanceLog[];
}

export interface ExportParams {
  start_date: string;
  end_date: string;
  user_id?: string;
  format?: 'csv' | 'xlsx' | 'pdf';
}

export const reportsApi = {
  /**
   * Get dashboard statistics
   */
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await api.get<DashboardStats>(`${REPORTS_BASE}/dashboard`);
    return response.data;
  },

  /**
   * Get attendance logs with filtering
   */
  async getAttendanceLogs(params: AttendanceListParams = {}): Promise<AttendanceListResponse> {
    const response = await api.get<AttendanceListResponse>(ATTENDANCE_BASE, { params });
    return response.data;
  },

  /**
   * Get attendance statistics for a user
   */
  async getUserStats(userId: string): Promise<AttendanceStats> {
    const response = await api.get<AttendanceStats>(`${REPORTS_BASE}/users/${userId}/stats`);
    return response.data;
  },

  /**
   * Get daily summary for a date range
   */
  async getDailySummaries(startDate: string, endDate: string): Promise<DailySummary[]> {
    const response = await api.get<DailySummary[]>(`${REPORTS_BASE}/daily-summaries`, {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },

  /**
   * Export attendance report
   */
  async exportReport(params: ExportParams): Promise<Blob> {
    const response = await api.get<Blob>(`${REPORTS_BASE}/export`, {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Get weekly attendance trend
   */
  async getWeeklyTrend(): Promise<{ date: string; check_ins: number; check_outs: number }[]> {
    const response = await api.get<{ date: string; check_ins: number; check_outs: number }[]>(
      `${REPORTS_BASE}/weekly-trend`
    );
    return response.data;
  },

  /**
   * Get department-wise attendance summary
   */
  async getDepartmentSummary(): Promise<{ department: string; present: number; absent: number }[]> {
    const response = await api.get<{ department: string; present: number; absent: number }[]>(
      `${REPORTS_BASE}/department-summary`
    );
    return response.data;
  },
};

export default reportsApi;
