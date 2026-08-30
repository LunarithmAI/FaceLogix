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
  | 'already_checked_in'
  | 'not_checked_in'
  | 'already_checked_out';

export type BackendCheckStatus =
  | 'on_time'
  | 'late'
  | 'unknown_user'
  | 'invalid_image'
  | 'spoof_detected'
  | 'multiple_faces'
  | 'low_quality'
  | 'no_face_detected'
  | 'already_checked_in'
  | 'not_checked_in'
  | 'already_checked_out';

// Raw response from backend
export interface BackendCheckInResponse {
  success: boolean;
  status: BackendCheckStatus;
  message: string;
  user_id?: string;
  user_name?: string;
  check_in_time?: string;
  confidence_score?: number;
}

// Transformed result for frontend display
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
  device_id: string;
  device_name: string;
  confidence: number;
  location?: {
    latitude: number;
    longitude: number;
  };
  photo_url?: string;
}

export interface DailySummary {
  date: string;
  total_users: number;
  checked_in: number;
  on_time: number;
  late: number;
  absent: number;
  unknown_attempts: number;
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
  period: {
    from_date: string;
    to_date: string;
    working_days: number;
  };
  summary: {
    on_time: number;
    late: number;
    absent: number;
    total_check_ins: number;
  };
  rates: {
    attendance_rate: number;
    punctuality_rate: number;
  };
  average_check_in_time: string | null;
}


export interface AttendanceListParams {
  page?: number;
  page_size?: number;
  from_date?: string;
  to_date?: string;
  user_id?: string;
  device_id?: string;
  status?: string;
  type?: CheckType;
}
