import api from './api';
import type {
  AttendanceListParams,
  AttendanceLog,
  CheckType,
  ReportDailySummary,
  UserAttendanceStats,
} from '@/types/attendance';

const REPORTS_BASE = '/reports';
const ATTENDANCE_BASE = '/attendance';

export interface AttendanceListResponse {
  items: AttendanceLog[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface BackendAttendanceLog {
  id: string;
  user_id: string | null;
  user_name: string | null;
  device_id: string | null;
  device_name: string | null;
  ts: string;
  type: CheckType;
  status: string;
  confidence_score: number | null;
}

interface BackendAttendanceListResponse {
  items: BackendAttendanceLog[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

interface BackendRecentActivity {
  id: string;
  timestamp: string;
  type: CheckType;
  status: string;
  confidence_score: number | null;
  user_id: string | null;
  user_name: string | null;
  device_id: string | null;
  device_name: string | null;
}

export interface DashboardToday {
  date: string;
  total_employees: number;
  checked_in: number;
  checked_out: number;
  on_time: number;
  late_arrivals: number;
  absent: number;
  average_check_in_time: string | null;
  average_check_out_time: string | null;
}

interface BackendDashboardStats {
  today: DashboardToday;
  total_users: number;
  active_devices: number;
  pending_enrollments: number;
  recent_activity: BackendRecentActivity[];
}

export interface DashboardStats {
  today: DashboardToday;
  total_users: number;
  active_devices: number;
  pending_enrollments: number;
  recent_activity: AttendanceLog[];
}

export interface ExportParams {
  from_date: string;
  to_date: string;
  user_id?: string;
  format?: 'csv';
}

function transformAttendanceLog(log: BackendAttendanceLog): AttendanceLog {
  return {
    id: log.id,
    user_id: log.user_id ?? '',
    user_name: log.user_name ?? 'Unknown',
    check_type: log.type,
    timestamp: log.ts,
    device_id: log.device_id ?? '',
    device_name: log.device_name ?? '',
    confidence: log.confidence_score ?? 0,
  };
}

function transformRecentActivity(activity: BackendRecentActivity): AttendanceLog {
  return transformAttendanceLog({
    ...activity,
    ts: activity.timestamp,
  });
}

export const reportsApi = {
  async getDashboardStats(signal?: AbortSignal): Promise<DashboardStats> {
    const response = await api.get<BackendDashboardStats>(`${REPORTS_BASE}/dashboard`, { signal });
    return {
      ...response.data,
      recent_activity: response.data.recent_activity.map(transformRecentActivity),
    };
  },

  async getAttendanceLogs(
    params: AttendanceListParams = {},
    signal?: AbortSignal
  ): Promise<AttendanceListResponse> {
    const response = await api.get<BackendAttendanceListResponse>(ATTENDANCE_BASE, {
      params,
      signal,
    });
    return {
      ...response.data,
      items: response.data.items.map(transformAttendanceLog),
    };
  },

  async getUserStats(userId: string, signal?: AbortSignal): Promise<UserAttendanceStats> {
    const response = await api.get<UserAttendanceStats>(`${REPORTS_BASE}/users/${userId}/stats`, {
      signal,
    });
    return response.data;
  },

  async getDailySummaries(
    fromDate: string,
    toDate: string,
    signal?: AbortSignal
  ): Promise<ReportDailySummary[]> {
    const response = await api.get<ReportDailySummary[]>(`${REPORTS_BASE}/daily-summaries`, {
      params: { from_date: fromDate, to_date: toDate },
      signal,
    });
    return response.data;
  },

  async exportReport(params: ExportParams): Promise<Blob> {
    const response = await api.get<Blob>(`${REPORTS_BASE}/export`, {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  async getWeeklyTrend(
    signal?: AbortSignal
  ): Promise<{ date: string; check_ins: number; check_outs: number }[]> {
    const response = await api.get<{ date: string; check_ins: number; check_outs: number }[]>(
      `${REPORTS_BASE}/weekly-trend`,
      { signal }
    );
    return response.data;
  },

  async getDepartmentSummary(
    signal?: AbortSignal
  ): Promise<{ department: string; present: number; absent: number }[]> {
    const response = await api.get<{ department: string; present: number; absent: number }[]>(
      `${REPORTS_BASE}/department-summary`,
      { signal }
    );
    return response.data;
  },
};

export default reportsApi;
