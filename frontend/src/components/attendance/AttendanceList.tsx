import {
  ArrowRightOnRectangleIcon,
  ArrowLeftOnRectangleIcon,
} from '@heroicons/react/24/outline';
import type { AttendanceLog } from '@/types/attendance';
import { formatTime, formatShortDate } from '@/utils/date';
import { Badge } from '@/components/ui/Badge';

interface AttendanceListProps {
  logs: AttendanceLog[];
  isLoading?: boolean;
  emptyMessage?: string;
  showUser?: boolean;
  showDevice?: boolean;
}

export function AttendanceList({
  logs,
  isLoading = false,
  emptyMessage = 'No attendance records found',
  showUser = true,
  showDevice = true,
}: AttendanceListProps) {
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-gray-100 rounded-lg" />
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
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            {showUser && (
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                User
              </th>
            )}
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Date
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Time
            </th>
            {showDevice && (
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Device
              </th>
            )}
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Confidence
            </th>
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
                      <Badge variant="success">Check In</Badge>
                    </span>
                  ) : (
                    <span className="flex items-center text-blue-600">
                      <ArrowLeftOnRectangleIcon className="w-5 h-5 mr-2" />
                      <Badge variant="info">Check Out</Badge>
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
                    <span className="text-sm text-gray-400">N/A</span>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default AttendanceList;
