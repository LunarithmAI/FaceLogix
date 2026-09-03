import { useState } from 'react';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { ArrowDownTrayIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { AttendanceList } from '@/components/attendance/AttendanceList';
import { Modal } from '@/components/ui/Modal';
import { Loading } from '@/components/ui/Loading';
import { reportsApi } from '@/services/reports';
import { shiftsApi } from '@/services/shifts';
import { unitsApi } from '@/services/units';
import { usersApi } from '@/services/users';
import type { AttendanceLog, CheckType } from '@/types/attendance';
import { queryClient, queryKeys } from '@/lib/queryClient';
import { formatApiDate } from '@/utils/date';
import { translate as t } from '@/i18n';

export function AttendancePage() {
  const [page, setPage] = useState(1);
  const [draftFilters, setDraftFilters] = useState(() => {
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - 7);
    return {
      from_date: formatApiDate(fromDate),
      to_date: formatApiDate(new Date()),
      type: '' as CheckType | '',
      unit_id: '',
      shift_id: '',
    };
  });
  const [appliedFilters, setAppliedFilters] = useState(draftFilters);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AttendanceLog | null>(null);
  const [correction, setCorrection] = useState({
    user_id: '',
    event_time: '',
    type: 'check_in' as CheckType,
    status: '',
    reason: '',
  });
  const unitsQuery = useQuery({
    queryKey: ['units', 'active'],
    queryFn: ({ signal }) => unitsApi.list(false, signal),
  });
  const shiftsQuery = useQuery({
    queryKey: ['shifts', 'active'],
    queryFn: ({ signal }) => shiftsApi.list(false, signal),
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'attendance-correction'],
    queryFn: ({ signal }) => usersApi.list({ page_size: 100, is_active: true }, signal),
  });

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
          unit_id: appliedFilters.unit_id || undefined,
          shift_id: appliedFilters.shift_id || undefined,
          page,
          page_size: 20,
        },
        signal
      ),
    placeholderData: keepPreviousData,
  });
  const dailyQuery = useQuery({
    queryKey: [
      'attendance',
      'daily',
      appliedFilters.to_date,
      appliedFilters.unit_id,
      appliedFilters.shift_id,
    ],
    queryFn: ({ signal }) =>
      reportsApi.getDailyAttendance(
        appliedFilters.to_date,
        appliedFilters.unit_id || undefined,
        appliedFilters.shift_id || undefined,
        signal
      ),
  });
  const correctionMutation = useMutation({
    mutationFn: () => {
      if (selectedLog === null) throw new Error('Select an attendance record');
      return reportsApi.correctAttendance(selectedLog.id, {
        user_id: correction.user_id || undefined,
        event_time: new Date(correction.event_time).toISOString(),
        type: correction.type,
        status: correction.status
          ? correction.status as 'on_time' | 'late' | 'early_departure' | 'unscheduled'
          : undefined,
        reason: correction.reason,
      });
    },
    onSuccess: async () => {
      setSelectedLog(null);
      await queryClient.invalidateQueries({ queryKey: ['attendance'] });
    },
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

  const openCorrection = (log: AttendanceLog) => {
    const localEventTime = new Date(log.timestamp);
    localEventTime.setMinutes(
      localEventTime.getMinutes() - localEventTime.getTimezoneOffset()
    );
    setCorrection({
      user_id: log.user_id,
      event_time: localEventTime.toISOString().slice(0, 16),
      type: log.check_type,
      status: ['on_time', 'late', 'early_departure', 'unscheduled'].includes(log.status)
        ? log.status
        : '',
      reason: '',
    });
    setSelectedLog(log);
  };

  return (
    <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{t('Attendance Logs')}</h1>
            <p className="text-gray-500 mt-1">{t('View and export attendance records')}</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              leftIcon={<FunnelIcon className="w-5 h-5" />}
              onClick={() => setShowFilters(!showFilters)}
            >
              {t('Filters')}
            </Button>
            <Button
              variant="secondary"
              leftIcon={<ArrowDownTrayIcon className="w-5 h-5" />}
              onClick={() => exportMutation.mutate()}
              isLoading={exportMutation.isPending}
            >
              {t('Export')}
            </Button>
          </div>
        </div>

        {exportMutation.error !== null && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700" role="alert">
            {t(exportMutation.error.message)}
          </div>
        )}

        {/* Filters */}
        {showFilters && (
          <Card>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Input
                label={t('Start Date')}
                type="date"
                value={draftFilters.from_date}
                onChange={(event) =>
                  setDraftFilters({ ...draftFilters, from_date: event.target.value })
                }
              />
              <Input
                label={t('End Date')}
                type="date"
                value={draftFilters.to_date}
                onChange={(event) =>
                  setDraftFilters({ ...draftFilters, to_date: event.target.value })
                }
              />
              <div>
                <label htmlFor="attendance-check-type" className="block text-sm font-medium text-gray-700 mb-1">
                  {t('Check Type')}
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
                  <option value="">{t('All')}</option>
                  <option value="check_in">{t('Check In')}</option>
                  <option value="check_out">{t('Check Out')}</option>
                </select>
              </div>
              <label className="text-sm font-medium text-gray-700">
                {t('Unit')}
                <select value={draftFilters.unit_id} onChange={(event) => setDraftFilters({ ...draftFilters, unit_id: event.target.value })} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-4 py-2">
                  <option value="">{t('All units')}</option>
                  {(unitsQuery.data ?? []).map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
                </select>
              </label>
              <label className="text-sm font-medium text-gray-700">
                {t('Shift')}
                <select value={draftFilters.shift_id} onChange={(event) => setDraftFilters({ ...draftFilters, shift_id: event.target.value })} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-4 py-2">
                  <option value="">{t('All shifts')}</option>
                  {(shiftsQuery.data ?? []).map((shift) => <option key={shift.id} value={shift.id}>{shift.name}</option>)}
                </select>
              </label>
              <div className="flex items-end">
                <Button onClick={handleApplyFilters} className="w-full">
                  {t('Apply Filters')}
                </Button>
              </div>
            </div>
          </Card>
        )}
        <Card>
          <div className="border-b border-gray-200 px-5 py-4">
            <h2 className="text-lg font-semibold text-gray-900">{t('Daily roster')}</h2>
            <p className="mt-1 text-sm text-gray-500">{appliedFilters.to_date}</p>
          </div>
          {dailyQuery.data && (
            <>
              <div className="grid grid-cols-3 border-b border-gray-200 text-center">
                <div className="p-4"><span className="block text-2xl font-bold text-gray-900">{dailyQuery.data.scheduled}</span><span className="text-sm text-gray-500">{t('Scheduled')}</span></div>
                <div className="border-x border-gray-200 p-4"><span className="block text-2xl font-bold text-green-700">{dailyQuery.data.present}</span><span className="text-sm text-gray-500">{t('Present')}</span></div>
                <div className="p-4"><span className="block text-2xl font-bold text-red-700">{dailyQuery.data.absent}</span><span className="text-sm text-gray-500">{t('Absent')}</span></div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 text-xs uppercase tracking-wide text-gray-500"><tr><th className="px-5 py-3">{t('User')}</th><th className="px-5 py-3">{t('Unit')}</th><th className="px-5 py-3">{t('Shift')}</th><th className="px-5 py-3">{t('Status')}</th></tr></thead>
                  <tbody className="divide-y divide-gray-100">
                    {dailyQuery.data.users.map((row) => <tr key={row.user_id}><td className="px-5 py-3 font-medium text-gray-900">{row.user_name}</td><td className="px-5 py-3 text-gray-600">{row.unit_name || t('Unassigned')}</td><td className="px-5 py-3 text-gray-600">{row.shift_name || t('No shift')}</td><td className="px-5 py-3 text-gray-600">{t(row.status)}</td></tr>)}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>


        {/* Attendance Table */}
        <Card>
          {attendanceQuery.isPending ? (
            <div className="py-12">
              <Loading size="lg" text={t('Loading attendance logs...')} />
            </div>
          ) : attendanceQuery.error !== null ? (
            <div className="p-6 text-center text-red-700" role="alert">
              <p>{t(attendanceQuery.error.message)}</p>
              <Button
                variant="secondary"
                className="mt-4"
                onClick={() => void attendanceQuery.refetch()}
              >
                {t('Try again')}
              </Button>
            </div>
          ) : (
            <>
              <AttendanceList
                logs={logs?.items || []}
                emptyMessage={t('No attendance records found for the selected period')}
                onCorrect={openCorrection}
              />

              {/* Pagination */}
              {logs && logs.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                  <p className="text-sm text-gray-500">
                    {t('Page')} {logs.page} {t('of')} {logs.pages} ({logs.total} {t('records')})
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                    >
                      {t('Previous')}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page === logs.pages}
                    >
                      {t('Next')}
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      <Modal isOpen={selectedLog !== null} onClose={() => setSelectedLog(null)} title={t('Correct attendance')} size="lg">
        <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); correctionMutation.mutate(); }}>
          <label className="block text-sm font-medium text-gray-700">
            {t('User')}
            <select value={correction.user_id} onChange={(event) => setCorrection({ ...correction, user_id: event.target.value })} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2" required>
              <option value="">{t('Select user')}</option>
              {(usersQuery.data?.items ?? []).map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}
            </select>
          </label>
          <Input label={t('Event time')} type="datetime-local" value={correction.event_time} onChange={(event) => setCorrection({ ...correction, event_time: event.target.value })} required />
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-gray-700">{t('Type')}<select value={correction.type} onChange={(event) => setCorrection({ ...correction, type: event.target.value as CheckType })} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2"><option value="check_in">{t('Check In')}</option><option value="check_out">{t('Check Out')}</option></select></label>
            <label className="text-sm font-medium text-gray-700">{t('Status')}<select value={correction.status} onChange={(event) => setCorrection({ ...correction, status: event.target.value })} className="mt-1 block w-full rounded-lg border border-gray-300 bg-white px-3 py-2"><option value="">{t('Recalculate')}</option><option value="on_time">{t('on_time')}</option><option value="late">{t('late')}</option><option value="early_departure">{t('early_departure')}</option><option value="unscheduled">{t('unscheduled')}</option></select></label>
          </div>
          <label className="block text-sm font-medium text-gray-700">{t('Reason')}<textarea value={correction.reason} onChange={(event) => setCorrection({ ...correction, reason: event.target.value })} minLength={3} required className="mt-1 min-h-24 w-full rounded-lg border border-gray-300 px-3 py-2" /></label>
          {correctionMutation.error instanceof Error && <p className="text-sm text-red-700" role="alert">{correctionMutation.error.message}</p>}
          <div className="flex justify-end gap-3"><Button type="button" variant="secondary" onClick={() => setSelectedLog(null)}>{t('Cancel')}</Button><Button type="submit" isLoading={correctionMutation.isPending}>{t('Save correction')}</Button></div>
        </form>
      </Modal>
      </div>
  );
}

export default AttendancePage;
