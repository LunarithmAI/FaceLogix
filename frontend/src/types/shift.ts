export interface ShiftSummary {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
  late_grace_minutes: number;
  early_departure_grace_minutes: number;
  scheduled_weekdays: number[];
  is_active: boolean;
}

export interface Shift extends ShiftSummary {
  org_id: string;
  created_at: string;
  updated_at: string;
}

export interface CreateShiftRequest {
  name: string;
  start_time: string;
  end_time: string;
  late_grace_minutes: number;
  early_departure_grace_minutes: number;
  scheduled_weekdays: number[];
}

export interface UpdateShiftRequest extends Partial<CreateShiftRequest> {
  is_active?: boolean;
}
