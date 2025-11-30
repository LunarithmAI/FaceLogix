import { useState, useEffect, useCallback } from 'react';
import { ArrowDownTrayIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { AttendanceList } from '@/components/attendance/AttendanceList';
import { Loading } from '@/components/ui/Loading';
import { reportsApi, type AttendanceListResponse } from '@/services/reports';
import type { AttendanceListParams, CheckType } from '@/types/attendance';
import { formatApiDate } from '@/utils/date';

export function AttendancePage() {
  const [logs, setLogs] = useState<AttendanceListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [page, setPage] = useState(1);

  // Filters
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 7);
    return formatApiDate(date);
  });
  const [endDate, setEndDate] = useState(() => formatApiDate(new Date()));
  const [checkType, setCheckType] = useState<CheckType | ''>('');
  const [showFilters, setShowFilters] = useState(false);

  const loadLogs = useCallback(async () => {
    try {
      setIsLoading(true);
      const params: AttendanceListParams = {
        page,
        limit: 20,
        start_date: startDate,
        end_date: endDate,
      };
      if (checkType) {
        params.check_type = checkType;
      }
      const data = await reportsApi.getAttendanceLogs(params);
      setLogs(data);
    } catch (error) {
      console.error('Failed to load attendance logs:', error);
    } finally {
      setIsLoading(false);
    }
  }, [page, startDate, endDate, checkType]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const handleExport = async () => {
    try {
      setIsExporting(true);
      const blob = await reportsApi.exportReport({
        start_date: startDate,
        end_date: endDate,
        format: 'csv',
      });

      // Download file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `attendance_${startDate}_${endDate}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const handleApplyFilters = () => {
    setPage(1);
    loadLogs();
  };

  return (
    <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Attendance Logs</h1>
            <p className="text-gray-500 mt-1">View and export attendance records</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              leftIcon={<FunnelIcon className="w-5 h-5" />}
              onClick={() => setShowFilters(!showFilters)}
            >
              Filters
            </Button>
            <Button
              variant="secondary"
              leftIcon={<ArrowDownTrayIcon className="w-5 h-5" />}
              onClick={handleExport}
              isLoading={isExporting}
            >
              Export
            </Button>
          </div>
        </div>

        {/* Filters */}
        {showFilters && (
          <Card>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Input
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <Input
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Check Type
                </label>
                <select
                  value={checkType}
                  onChange={(e) => setCheckType(e.target.value as CheckType | '')}
                  className="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                >
                  <option value="">All</option>
                  <option value="check_in">Check In</option>
                  <option value="check_out">Check Out</option>
                </select>
              </div>
              <div className="flex items-end">
                <Button onClick={handleApplyFilters} className="w-full">
                  Apply Filters
                </Button>
              </div>
            </div>
          </Card>
        )}

        {/* Attendance Table */}
        <Card>
          {isLoading ? (
            <div className="py-12">
              <Loading size="lg" text="Loading attendance logs..." />
            </div>
          ) : (
            <>
              <AttendanceList
                logs={logs?.items || []}
                emptyMessage="No attendance records found for the selected period"
              />

              {/* Pagination */}
              {logs && logs.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                  <p className="text-sm text-gray-500">
                    Page {logs.page} of {logs.pages} ({logs.total} records)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page === logs.pages}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      </div>
  );
}

export default AttendancePage;
