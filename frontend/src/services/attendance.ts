import api from './api';
import type {
  BackendCheckInResponse,
  CheckInResult,
  CheckStatus,
  CheckType,
} from '@/types/attendance';

function transformCheckInResponse(
  response: BackendCheckInResponse,
  checkType: CheckType
): CheckInResult {
  let status: CheckStatus;
  if (response.success) {
    status = 'success';
  } else {
    switch (response.status) {
      case 'unknown_user':
      case 'ambiguous_face':
        status = 'not_recognized';
        break;
      case 'invalid_image':
      case 'spoof_detected':
      case 'multiple_faces':
      case 'low_quality':
      case 'already_checked_in':
      case 'not_checked_in':
      case 'already_checked_out':
      case 'no_face_detected':
        status = response.status;
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
    timestamp: response.event_time,
    confidence: response.confidence_score,
  };
}

export const attendanceApi = {
  async checkIn(imageData: string): Promise<CheckInResult> {
    const response = await api.post<BackendCheckInResponse>('/attendance/check-in', {
      image: imageData,
    });
    return transformCheckInResponse(response.data, 'check_in');
  },

  async checkOut(imageData: string): Promise<CheckInResult> {
    const response = await api.post<BackendCheckInResponse>('/attendance/check-out', {
      image: imageData,
    });
    return transformCheckInResponse(response.data, 'check_out');
  },
};

export default attendanceApi;
