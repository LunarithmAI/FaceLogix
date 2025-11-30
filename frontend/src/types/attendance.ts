export type CheckType = 'check_in' | 'check_out';

export type CheckStatus = 'success' | 'failed' | 'already_checked' | 'not_recognized' | 'no_face_detected';

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
  total_employees: number;
  total_users?: number;
  checked_in: number;
  checked_out?: number;
  absent: number;
  late_arrivals?: number;
  on_time?: number;
  late?: number;
  early_departures?: number;
  average_check_in_time?: string;
  average_check_out_time?: string;
  unknown_attempts?: number;
  // Computed/display fields
  total_check_ins?: number;
  total_check_outs?: number;
  on_time_count?: number;
  late_count?: number;
  on_time_percentage?: number;
}

export interface AttendanceStats {
  today: DailySummary;
  weekly: {
    present_days: number;
    absent_days: number;
    total_hours: number;
    average_hours_per_day: number;
  };
  monthly: {
    present_days: number;
    absent_days: number;
    total_hours: number;
    on_time_percentage: number;
  };
}

export interface AttendanceListParams {
  page?: number;
  limit?: number;
  start_date?: string;
  end_date?: string;
  user_id?: string;
  check_type?: CheckType;
}
