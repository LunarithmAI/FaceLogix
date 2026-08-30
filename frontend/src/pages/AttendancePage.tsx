import { useState } from 'react';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { ArrowDownTrayIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { AttendanceList } from '@/components/attendance/AttendanceList';
import { Loading } from '@/components/ui/Loading';
import { reportsApi } from '@/services/reports';
import type { CheckType } from '@/types/attendance';
import { queryKeys } from '@/lib/queryClient';
import { formatApiDate } from '@/utils/date';

export function AttendancePage() {
  const [page, setPage] = useState(1);
  const [draftFilters, setDraftFilters] = useState(() => {
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - 7);
    return {
      from_date: formatApiDate(fromDate),
      to_date: formatApiDate(new Date()),
      type: '' as CheckType | '',
    };
  });
  const [appliedFilters, setAppliedFilters] = useState(draftFilters);
  const [showFilters, setShowFilters] = useState(false);

  const attendanceQuery = useQuery({
    queryKey: queryKeys.attendance({
      ...appliedFilters,
      page,
      page_size: 20,
    }),
    queryFn: ({ signal }) =>
      reportsApi.getAttendanceLogs(
        {
          ...appliedFilters,
          type: appliedFilters.type || undefined,
          page,
          page_size: 20,
        },
        signal
      ),
    placeholderData: keepPreviousData,
  });
  const exportMutation = useMutation({
    mutationFn: () =>
      reportsApi.exportReport({
        from_date: appliedFilters.from_date,
        to_date: appliedFilters.to_date,
        format: 'csv',
      }),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `attendance_${appliedFilters.from_date}_${appliedFilters.to_date}.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    },
  });
  const logs = attendanceQuery.data;

  const handleApplyFilters = () => {
    setAppliedFilters(draftFilters);
    setPage(1);
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
              onClick={() => exportMutation.mutate()}
              isLoading={exportMutation.isPending}
            >
              Export
            </Button>
          </div>
        </div>

        {exportMutation.error !== null && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700" role="alert">
            {exportMutation.error.message}
          </div>
        )}

        {/* Filters */}
        {showFilters && (
          <Card>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Input
                label="Start Date"
                type="date"
                value={draftFilters.from_date}
                onChange={(event) =>
                  setDraftFilters({ ...draftFilters, from_date: event.target.value })
                }
              />
              <Input
                label="End Date"
                type="date"
                value={draftFilters.to_date}
                onChange={(event) =>
                  setDraftFilters({ ...draftFilters, to_date: event.target.value })
                }
              />
              <div>
                <label htmlFor="attendance-check-type" className="block text-sm font-medium text-gray-700 mb-1">
                  Check Type
                </label>
                <select
                  id="attendance-check-type"
                  value={draftFilters.type}
                  onChange={(event) =>
                    setDraftFilters({
                      ...draftFilters,
                      type: event.target.value as CheckType | '',
                    })
                  }
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
          {attendanceQuery.isPending ? (
            <div className="py-12">
              <Loading size="lg" text="Loading attendance logs..." />
            </div>
          ) : attendanceQuery.error !== null ? (
            <div className="p-6 text-center text-red-700" role="alert">
              <p>{attendanceQuery.error.message}</p>
              <Button
                variant="secondary"
                className="mt-4"
                onClick={() => void attendanceQuery.refetch()}
              >
                Try again
              </Button>
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
