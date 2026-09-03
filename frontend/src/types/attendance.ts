export type CheckType = 'check_in' | 'check_out';

export type CheckStatus =
  | 'success'
  | 'failed'
  | 'not_recognized'
  | 'invalid_image'
  | 'spoof_detected'
  | 'multiple_faces'
  | 'low_quality'
  | 'no_face_detected'
  | 'ambiguous_face'
  | 'already_checked_in'
  | 'not_checked_in'
  | 'already_checked_out';

export type BackendCheckStatus =
  | 'on_time'
  | 'late'
  | 'early_departure'
  | 'unscheduled'
  | 'unknown_user'
  | 'ambiguous_face'
  | 'invalid_image'
  | 'spoof_detected'
  | 'multiple_faces'
  | 'low_quality'
  | 'no_face_detected'
  | 'already_checked_in'
  | 'not_checked_in'
  | 'already_checked_out';

export interface BackendCheckInResponse {
  success: boolean;
  status: BackendCheckStatus;
  message: string;
  user_id?: string;
  user_name?: string;
  event_time?: string;
  schedule_date?: string;
  unit_id?: string;
  shift_id?: string;
  confidence_score?: number;
}

export interface CheckInResult {
  status: CheckStatus;
  message: string;
  user_name?: string;
  check_type?: CheckType;
  timestamp?: string;
  confidence?: number;
}

export interface AttendanceLog {
  id: string;
  user_id: string;
  user_name: string;
  check_type: CheckType;
  timestamp: string;
  schedule_date: string | null;
  status: string;
  source: 'face' | 'manual';
  unit_id: string;
  unit_name: string;
  shift_id: string;
  shift_name: string;
  device_id: string;
  device_name: string;
  confidence: number;
  supersedes_id: string | null;
  correction_reason: string | null;
}

export interface DailySummary {
  date: string;
  scheduled: number;
  checked_in: number;
  on_time: number;
  late: number;
  absent: number;
  unknown_attempts: number;
  ambiguous_attempts: number;
}

export interface ReportDailySummary {
  date: string;
  total_users: number;
  check_ins: number;
  check_outs: number;
  on_time: number;
  late: number;
  absent: number;
  unknown_attempts: number;
  on_time_percentage: number;
}

export interface UserAttendanceStats {
  user_id: string;
  user_name: string;
  period: { from_date: string; to_date: string; working_days: number };
  summary: { on_time: number; late: number; absent: number; total_check_ins: number };
  rates: { attendance_rate: number; punctuality_rate: number };
  average_check_in_time: string | null;
}

export interface AttendanceListParams {
  page?: number;
  page_size?: number;
  from_date?: string;
  to_date?: string;
  user_id?: string;
  device_id?: string;
  unit_id?: string;
  shift_id?: string;
  status?: string;
  type?: CheckType;
}

export interface AttendanceCorrectionRequest {
  user_id?: string;
  event_time: string;
  type: CheckType;
  status?: 'on_time' | 'late' | 'early_departure' | 'unscheduled';
  reason: string;
}

export interface UnitAttendanceSummary {
  unit: { id: string; name: string; kind: 'department' | 'class'; is_active: boolean };
  scheduled_person_days: number;
  present_person_days: number;
  absent_person_days: number;
  on_time: number;
  late: number;
  attendance_rate: number;
}

export interface BackendAttendanceLog {
  id: string;
  user_id: string | null;
  user_name: string | null;
  device_id: string | null;
  device_name: string | null;
  unit_id: string | null;
  unit_name: string | null;
  shift_id: string | null;
  shift_name: string | null;
  schedule_date: string | null;
  event_time: string;
  type: CheckType;
  status: string;
  source: 'face' | 'manual';
  confidence_score: number | null;
  supersedes_id: string | null;
  correction_reason: string | null;
  created_by_id: string | null;
}

export interface DailyAttendanceUser {
  user_id: string;
  user_name: string;
  unit_id: string | null;
  unit_name: string | null;
  shift_id: string | null;
  shift_name: string | null;
  scheduled: boolean;
  check_in: BackendAttendanceLog | null;
  check_out: BackendAttendanceLog | null;
  status: string;
}

export interface DailyAttendance {
  date: string;
  scheduled: number;
  present: number;
  absent: number;
  users: DailyAttendanceUser[];
  unknown_attempts: number;
  ambiguous_attempts: number;
}
