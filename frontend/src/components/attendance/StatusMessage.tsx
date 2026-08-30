import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationCircleIcon,
  FaceSmileIcon,
} from '@heroicons/react/24/solid';
import type { CheckInResult, CheckStatus } from '@/types/attendance';
import { format } from 'date-fns';

interface StatusMessageProps {
  result: CheckInResult;
  className?: string;
}

type StatusConfig = {
  icon: typeof CheckCircleIcon;
  title: string;
  bgColor: string;
  textColor: string;
  borderColor: string;
  iconColor: string;
};

const warningConfig = {
  icon: ExclamationCircleIcon,
  bgColor: 'bg-yellow-50',
  textColor: 'text-yellow-800',
  borderColor: 'border-yellow-200',
  iconColor: 'text-yellow-500',
} satisfies Omit<StatusConfig, 'title'>;

const errorConfig = {
  icon: XCircleIcon,
  bgColor: 'bg-red-50',
  textColor: 'text-red-800',
  borderColor: 'border-red-200',
  iconColor: 'text-red-500',
} satisfies Omit<StatusConfig, 'title'>;

const statusConfig: Record<CheckStatus, StatusConfig> = {
  success: {
    icon: CheckCircleIcon,
    title: 'Attendance Recorded',
    bgColor: 'bg-green-50',
    textColor: 'text-green-800',
    borderColor: 'border-green-200',
    iconColor: 'text-green-500',
  },
  failed: { ...errorConfig, title: 'Check Failed' },
  invalid_image: { ...errorConfig, title: 'Invalid Image' },
  spoof_detected: { ...errorConfig, title: 'Liveness Check Failed' },
  already_checked_in: { ...warningConfig, title: 'Already Checked In' },
  not_checked_in: { ...warningConfig, title: 'Not Checked In' },
  already_checked_out: { ...warningConfig, title: 'Already Checked Out' },
  multiple_faces: { ...warningConfig, title: 'Multiple Faces Detected' },
  low_quality: { ...warningConfig, title: 'Image Quality Too Low' },
  not_recognized: {
    icon: FaceSmileIcon,
    title: 'Face Not Recognized',
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-800',
    borderColor: 'border-orange-200',
    iconColor: 'text-orange-500',
  },
  no_face_detected: {
    icon: FaceSmileIcon,
    title: 'No Face Detected',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-800',
    borderColor: 'border-gray-200',
    iconColor: 'text-gray-500',
  },
};

export function StatusMessage({ result, className = '' }: StatusMessageProps) {
  const config = statusConfig[result.status];
  const Icon = config.icon;

  return (
    <div
      className={`
        rounded-xl border-2 p-6 motion-safe:animate-slide-up
        ${config.bgColor} ${config.borderColor}
        ${className}
      `}
      role={result.status === 'success' ? 'status' : 'alert'}
      aria-live={result.status === 'success' ? 'polite' : 'assertive'}
    >
      <div className="flex items-start gap-4">
        <Icon className={`w-10 h-10 flex-shrink-0 ${config.iconColor}`} aria-hidden="true" />
        
        <div className="flex-1 min-w-0">
          <h3 className={`text-lg font-semibold ${config.textColor}`}>
            {result.status === 'success'
              ? result.check_type === 'check_out'
                ? 'Checked Out Successfully'
                : 'Checked In Successfully'
              : config.title}
          </h3>
          
          <p className={`mt-1 ${config.textColor} opacity-90`}>
            {result.message}
          </p>

          {result.user_name && (
            <p className={`mt-2 font-medium ${config.textColor}`}>
              Welcome, {result.user_name}!
            </p>
          )}

          {result.timestamp && (
            <p className={`mt-1 text-sm ${config.textColor} opacity-75`}>
              {format(new Date(result.timestamp), 'PPpp')}
            </p>
          )}

          {result.confidence !== undefined && result.status === 'success' && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-sm">
                <span className={config.textColor}>Confidence</span>
                <span className={`font-medium ${config.textColor}`}>
                  {Math.round(result.confidence * 100)}%
                </span>
              </div>
              <div className="mt-1 h-2 bg-white/50 rounded-full overflow-hidden">
                <div
                  className={`h-full ${
                    result.confidence > 0.9 
                      ? 'bg-green-500' 
                      : result.confidence > 0.7 
                        ? 'bg-yellow-500' 
                        : 'bg-red-500'
                  }`}
                  style={{ width: `${result.confidence * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default StatusMessage;
