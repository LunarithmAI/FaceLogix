import {
  ArrowRightOnRectangleIcon,
  ArrowLeftOnRectangleIcon,
} from '@heroicons/react/24/outline';
import type { AttendanceLog } from '@/types/attendance';
import { formatTime, formatShortDate } from '@/utils/date';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { translate as t } from '@/i18n';

interface AttendanceListProps {
  logs: AttendanceLog[];
  isLoading?: boolean;
  emptyMessage?: string;
  showUser?: boolean;
  showDevice?: boolean;
  onCorrect?: (log: AttendanceLog) => void;
}

export function AttendanceList({
  logs,
  isLoading = false,
  emptyMessage = t('No attendance records found'),
  showUser = true,
  showDevice = true,
  onCorrect,
}: AttendanceListProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className="h-16 bg-gray-100 rounded-lg" />
        ))}
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500" role="region" aria-label={t('Attendance records table')} tabIndex={0}>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Type')}
            </th>
            {showUser && (
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('User')}
              </th>
            )}
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t('Unit / Shift')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t('Status')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Date')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Time')}
            </th>
            {showDevice && (
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {t('Device')}
              </th>
            )}
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Confidence')}
            </th>
            {onCorrect && (
              <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                {t('Actions')}
              </th>
            )}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {logs.map((log) => (
            <tr key={log.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  {log.check_type === 'check_in' ? (
                    <span className="flex items-center text-green-600">
                      <ArrowRightOnRectangleIcon className="w-5 h-5 mr-2" />
                      <Badge variant="success">{t('Check In')}</Badge>
                    </span>
                  ) : (
                    <span className="flex items-center text-blue-600">
                      <ArrowLeftOnRectangleIcon className="w-5 h-5 mr-2" />
                      <Badge variant="info">{t('Check Out')}</Badge>
                    </span>
                  )}
                </div>
              </td>
              {showUser && (
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">
                    {log.user_name}
                  </div>
                </td>
              )}
              <td className="px-6 py-4 text-sm text-gray-600">
                <span className="block font-medium text-gray-900">{log.unit_name || t('Unassigned')}</span>
                <span>{log.shift_name || t('No shift')}</span>
              </td>
              <td className="px-6 py-4 text-sm text-gray-600">
                <span className="block">{t(log.status)}</span>
                <span className="text-xs uppercase tracking-wide text-gray-400">{t(log.source)}</span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-900">
                  {formatShortDate(log.timestamp)}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-900">
                  {formatTime(log.timestamp)}
                </div>
              </td>
              {showDevice && (
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-500">{log.device_name}</div>
                </td>
              )}
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  {typeof log.confidence === 'number' && log.confidence > 0 ? (
                    <>
                      <div className="w-16 h-2 bg-gray-200 rounded-full mr-2">
                        <div
                          className={`h-2 rounded-full ${
                            log.confidence > 0.9
                              ? 'bg-green-500'
                              : log.confidence > 0.7
                                ? 'bg-yellow-500'
                                : 'bg-red-500'
                          }`}
                          style={{ width: `${log.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-600">
                        {Math.round(log.confidence * 100)}%
                      </span>
                    </>
                  ) : (
                    <span className="text-sm text-gray-400">{t('N/A')}</span>
                  )}
                </div>
              </td>
              {onCorrect && (
                <td className="px-6 py-4 text-right">
                  <Button type="button" size="sm" variant="secondary" onClick={() => onCorrect(log)}>
                    {t('Correct')}
                  </Button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default AttendanceList;
