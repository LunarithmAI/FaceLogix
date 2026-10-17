import { useState } from 'react';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { ArrowDownTrayIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { AttendanceList } from '@/components/attendance/AttendanceList';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { Loading } from '@/components/ui/Loading';
import { Alert } from '@/components/ui/Alert';
import { AttendanceStatusBadge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { Pagination } from '@/components/ui/Pagination';
import { Select } from '@/components/ui/Select';
import { reportsApi } from '@/services/reports';
import { shiftsApi } from '@/services/shifts';
import { unitsApi } from '@/services/units';
import { usersApi } from '@/services/users';
import type { AttendanceLog, CheckType } from '@/types/attendance';
import { queryClient, queryKeys } from '@/lib/queryClient';
import { formatApiDate, formatDisplayDate } from '@/utils/date';
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
      <PageHeader
        title={t('Attendance Logs')}
        description={t('View and export attendance records')}
        actions={
          <>
            <Button
              variant="secondary"
              leftIcon={<FunnelIcon className="h-5 w-5" aria-hidden="true" />}
              onClick={() => setShowFilters(!showFilters)}
              aria-expanded={showFilters}
              aria-controls="attendance-filters"
            >
              {t('Filters')}
            </Button>
            <Button
              variant="secondary"
              leftIcon={<ArrowDownTrayIcon className="h-5 w-5" aria-hidden="true" />}
              onClick={() => exportMutation.mutate()}
              isLoading={exportMutation.isPending}
            >
              {t('Export')}
            </Button>
          </>
        }
      />

      {exportMutation.error !== null && <Alert>{t(exportMutation.error.message)}</Alert>}

      {showFilters && (
        <Card id="attendance-filters">
          <form
            className="grid grid-cols-1 items-end gap-4 sm:grid-cols-2 lg:grid-cols-3"
            onSubmit={(event) => {
              event.preventDefault();
              handleApplyFilters();
            }}
          >
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
            <Select
              label={t('Check Type')}
              value={draftFilters.type}
              onChange={(event) =>
                setDraftFilters({
                  ...draftFilters,
                  type: event.target.value as CheckType | '',
                })
              }
            >
              <option value="">{t('All')}</option>
              <option value="check_in">{t('Check In')}</option>
              <option value="check_out">{t('Check Out')}</option>
            </Select>
            <Select
              label={t('Unit')}
              value={draftFilters.unit_id}
              onChange={(event) => setDraftFilters({ ...draftFilters, unit_id: event.target.value })}
            >
              <option value="">{t('All units')}</option>
              {(unitsQuery.data ?? []).map((unit) => <option key={unit.id} value={unit.id}>{unit.name}</option>)}
            </Select>
            <Select
              label={t('Shift')}
              value={draftFilters.shift_id}
              onChange={(event) => setDraftFilters({ ...draftFilters, shift_id: event.target.value })}
            >
              <option value="">{t('All shifts')}</option>
              {(shiftsQuery.data ?? []).map((shift) => <option key={shift.id} value={shift.id}>{shift.name}</option>)}
            </Select>
            <Button type="submit" className="w-full">
              {t('Apply Filters')}
            </Button>
          </form>
        </Card>
      )}

      <Card padding="none" className="overflow-hidden">
        <div className="border-b border-gray-200 px-4 py-4 sm:px-6">
          <h2 className="text-lg font-semibold text-gray-900">{t('Daily roster')}</h2>
          <p className="mt-1 text-sm text-gray-500">{formatDisplayDate(appliedFilters.to_date)}</p>
        </div>
        {dailyQuery.isPending ? (
          <div className="py-10">
            <Loading text={t('Loading roster...')} />
          </div>
        ) : dailyQuery.error !== null ? (
          <div className="p-4 sm:px-6">
            <Alert>{t(dailyQuery.error.message)}</Alert>
          </div>
        ) : (
          <>
            <dl className="grid grid-cols-3 divide-x divide-gray-200 border-b border-gray-200 text-center">
              <div className="p-4">
                <dt className="text-sm text-gray-500">{t('Scheduled')}</dt>
                <dd className="text-2xl font-bold tabular-nums text-gray-900">{dailyQuery.data.scheduled}</dd>
              </div>
              <div className="p-4">
                <dt className="text-sm text-gray-500">{t('Present')}</dt>
                <dd className="text-2xl font-bold tabular-nums text-green-700">{dailyQuery.data.present}</dd>
              </div>
              <div className="p-4">
                <dt className="text-sm text-gray-500">{t('Absent')}</dt>
                <dd className="text-2xl font-bold tabular-nums text-red-700">{dailyQuery.data.absent}</dd>
              </div>
            </dl>
            {dailyQuery.data.users.length === 0 ? (
              <p className="py-10 text-center text-gray-500">{t('No users are scheduled for this day')}</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 [&_th]:font-medium">
                    <tr>
                      <th className="px-6 py-3">{t('User')}</th>
                      <th className="px-6 py-3">{t('Unit')}</th>
                      <th className="px-6 py-3">{t('Shift')}</th>
                      <th className="px-6 py-3">{t('Status')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {dailyQuery.data.users.map((row) => (
                      <tr key={row.user_id} className="hover:bg-gray-50">
                        <td className="px-6 py-3 font-medium text-gray-900">{row.user_name}</td>
                        <td className="px-6 py-3 text-gray-600">{row.unit_name || t('Unassigned')}</td>
                        <td className="px-6 py-3 text-gray-600">{row.shift_name || t('No shift')}</td>
                        <td className="px-6 py-3"><AttendanceStatusBadge status={row.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </Card>

      <Card padding="none" className="overflow-hidden">
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
            {logs && (
              <Pagination
                page={logs.page}
                pages={logs.pages}
                total={logs.total}
                itemLabel={t('records')}
                onPageChange={setPage}
              />
            )}
          </>
        )}
      </Card>

      <Modal isOpen={selectedLog !== null} onClose={() => setSelectedLog(null)} title={t('Correct attendance')} size="lg">
        <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); correctionMutation.mutate(); }}>
          {correctionMutation.error instanceof Error && <Alert>{t(correctionMutation.error.message)}</Alert>}
          <Select
            label={t('User')}
            value={correction.user_id}
            onChange={(event) => setCorrection({ ...correction, user_id: event.target.value })}
            required
          >
            <option value="">{t('Select user')}</option>
            {(usersQuery.data?.items ?? []).map((user) => <option key={user.id} value={user.id}>{user.name}</option>)}
          </Select>
          <Input label={t('Event time')} type="datetime-local" value={correction.event_time} onChange={(event) => setCorrection({ ...correction, event_time: event.target.value })} required />
          <div className="grid gap-4 sm:grid-cols-2">
            <Select
              label={t('Type')}
              value={correction.type}
              onChange={(event) => setCorrection({ ...correction, type: event.target.value as CheckType })}
            >
              <option value="check_in">{t('Check In')}</option>
              <option value="check_out">{t('Check Out')}</option>
            </Select>
            <Select
              label={t('Status')}
              value={correction.status}
              onChange={(event) => setCorrection({ ...correction, status: event.target.value })}
            >
              <option value="">{t('Recalculate')}</option>
              <option value="on_time">{t('on_time')}</option>
              <option value="late">{t('late')}</option>
              <option value="early_departure">{t('early_departure')}</option>
              <option value="unscheduled">{t('unscheduled')}</option>
            </Select>
          </div>
          <div>
            <label htmlFor="correction-reason" className="mb-1 block text-sm font-medium text-gray-700">
              {t('Reason')}
            </label>
            <textarea
              id="correction-reason"
              value={correction.reason}
              onChange={(event) => setCorrection({ ...correction, reason: event.target.value })}
              minLength={3}
              required
              className="block min-h-24 w-full rounded-lg border border-gray-300 px-4 py-2 placeholder-gray-400 focus:border-primary-500 focus:ring-primary-500 focus-visible:outline-none focus-visible:ring-2"
            />
          </div>
          <ModalFooter>
            <Button type="button" variant="secondary" onClick={() => setSelectedLog(null)}>{t('Cancel')}</Button>
            <Button type="submit" isLoading={correctionMutation.isPending}>{t('Save correction')}</Button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}

export default AttendancePage;
