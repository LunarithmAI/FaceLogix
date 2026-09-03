import api from './api';
import type {
  AttendanceListParams,
  AttendanceCorrectionRequest,
  AttendanceLog,
  CheckType,
  DailyAttendance,
  ReportDailySummary,
  UserAttendanceStats,
  UnitAttendanceSummary,
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
  unit_id?: string | null;
  unit_name?: string | null;
  shift_id?: string | null;
  shift_name?: string | null;
  schedule_date?: string | null;
  event_time: string;
  type: CheckType;
  status: string;
  source?: 'face' | 'manual';
  confidence_score: number | null;
  supersedes_id?: string | null;
  correction_reason?: string | null;
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
    timestamp: log.event_time,
    schedule_date: log.schedule_date ?? null,
    status: log.status,
    source: log.source ?? 'face',
    unit_id: log.unit_id ?? '',
    unit_name: log.unit_name ?? '',
    shift_id: log.shift_id ?? '',
    shift_name: log.shift_name ?? '',
    device_id: log.device_id ?? '',
    device_name: log.device_name ?? '',
    confidence: log.confidence_score ?? 0,
    supersedes_id: log.supersedes_id ?? null,
    correction_reason: log.correction_reason ?? null,
  };
}

function transformRecentActivity(activity: BackendRecentActivity): AttendanceLog {
  return transformAttendanceLog({
    ...activity,
    event_time: activity.timestamp,
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

  async correctAttendance(
    logId: string,
    payload: AttendanceCorrectionRequest
  ): Promise<AttendanceLog> {
    const response = await api.post<BackendAttendanceLog>(
      `${ATTENDANCE_BASE}/${logId}/corrections`,
      payload
    );
    return transformAttendanceLog(response.data);
  },


  async getDailyAttendance(
    date: string,
    unitId?: string,
    shiftId?: string,
    signal?: AbortSignal
  ): Promise<DailyAttendance> {
    const response = await api.get<DailyAttendance>(`${ATTENDANCE_BASE}/daily`, {
      params: { date, unit_id: unitId, shift_id: shiftId },
      signal,
    });
    return response.data;
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

  async getUnitSummary(
    fromDate: string,
    toDate: string,
    signal?: AbortSignal
  ): Promise<UnitAttendanceSummary[]> {
    const response = await api.get<UnitAttendanceSummary[]>(`${REPORTS_BASE}/unit-summary`, {
      params: { from_date: fromDate, to_date: toDate },
      signal,
    });
    return response.data;
  },
};

export default reportsApi;
