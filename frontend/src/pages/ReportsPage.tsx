import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  ChartBarIcon,
  ArrowDownTrayIcon,
  CalendarIcon,
  UserGroupIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { Alert } from '@/components/ui/Alert';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatCard } from '@/components/ui/StatCard';
import { reportsApi } from '@/services/reports';
import { formatApiDate, formatDisplayDate } from '@/utils/date';
import { queryKeys } from '@/lib/queryClient';
import { translate as t } from '@/i18n';

const sectionTitleClass = 'border-b border-gray-200 px-4 py-4 text-lg font-semibold text-gray-900 sm:px-6';
const theadClass = 'bg-gray-50 text-xs uppercase tracking-wider text-gray-500 [&_th]:font-medium';

export function ReportsPage() {
  const [draftRange, setDraftRange] = useState(() => {
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - 30);
    return {
      from_date: formatApiDate(fromDate),
      to_date: formatApiDate(new Date()),
    };
  });
  const [appliedRange, setAppliedRange] = useState(draftRange);
  const reportsQuery = useQuery({
    queryKey: queryKeys.reports(appliedRange),
    queryFn: async ({ signal }) => {
      const [dailySummaries, weeklyTrend, unitSummary] = await Promise.all([
        reportsApi.getDailySummaries(
          appliedRange.from_date,
          appliedRange.to_date,
          signal
        ),
        reportsApi.getWeeklyTrend(signal),
        reportsApi.getUnitSummary(
          appliedRange.from_date,
          appliedRange.to_date,
          signal
        ),
      ]);
      return { dailySummaries, weeklyTrend, unitSummary };
    },
  });
  const exportMutation = useMutation({
    mutationFn: () =>
      reportsApi.exportReport({
        ...appliedRange,
        format: 'csv',
      }),
    onSuccess: (blob) => {
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `attendance_report_${appliedRange.from_date}_${appliedRange.to_date}.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    },
  });
  const {
    dailySummaries = [],
    weeklyTrend = [],
    unitSummary = [],
  } = reportsQuery.data ?? {};

  // Calculate summary stats
  const totalCheckIns = dailySummaries.reduce((sum, day) => sum + day.check_ins, 0);
  const totalCheckOuts = dailySummaries.reduce((sum, day) => sum + day.check_outs, 0);
  const avgOnTime = dailySummaries.length > 0
    ? Math.round(dailySummaries.reduce((sum, day) => sum + day.on_time_percentage, 0) / dailySummaries.length)
    : 0;

  if (reportsQuery.isPending) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text={t('Loading reports...')} />
      </div>
    );
  }

  if (reportsQuery.error !== null) {
    return (
      <div className="p-6 text-center text-red-700" role="alert">
        <p>{t(reportsQuery.error.message)}</p>
        <Button className="mt-4" onClick={() => void reportsQuery.refetch()}>
          {t('Try again')}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('Reports')}
        description={t('Attendance analytics and export')}
        actions={
          <Button
            onClick={() => exportMutation.mutate()}
            isLoading={exportMutation.isPending}
            leftIcon={<ArrowDownTrayIcon className="h-5 w-5" aria-hidden="true" />}
          >
            {t('Export')}
          </Button>
        }
      />

      {exportMutation.error !== null && <Alert>{t(exportMutation.error.message)}</Alert>}

      <Card>
        <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('Generate Report')}</h2>
        <form
          className="grid grid-cols-1 items-end gap-4 sm:grid-cols-[1fr_1fr_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            setAppliedRange(draftRange);
          }}
        >
          <Input
            label={t('Start Date')}
            type="date"
            value={draftRange.from_date}
            onChange={(event) =>
              setDraftRange({ ...draftRange, from_date: event.target.value })
            }
          />
          <Input
            label={t('End Date')}
            type="date"
            value={draftRange.to_date}
            onChange={(event) =>
              setDraftRange({ ...draftRange, to_date: event.target.value })
            }
          />
          <Button type="submit" variant="secondary" isLoading={reportsQuery.isFetching}>
            {t('Refresh')}
          </Button>
        </form>
        <p className="mt-3 text-sm text-gray-500">{t('Export format: CSV')}</p>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t('Days Analyzed')} value={dailySummaries.length} icon={CalendarIcon} tone="neutral" />
        <StatCard label={t('Total Check-Ins')} value={totalCheckIns} icon={UserGroupIcon} tone="success" />
        <StatCard label={t('Total Check-Outs')} value={totalCheckOuts} icon={ChartBarIcon} />
        <StatCard
          label={t('Avg On-Time Rate')}
          value={`${avgOnTime}%`}
          icon={ClockIcon}
          tone={avgOnTime >= 80 ? 'success' : 'warning'}
        />
      </div>

      <Card padding="none" className="overflow-hidden">
        <h2 className={sectionTitleClass}>{t('Weekly Attendance Trend')}</h2>
        {weeklyTrend.length === 0 ? (
          <p className="py-10 text-center text-gray-500">{t('No trend data available')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className={theadClass}>
                <tr>
                  <th className="px-6 py-3 text-left">{t('Date')}</th>
                  <th className="px-6 py-3 text-right">{t('Check-Ins')}</th>
                  <th className="px-6 py-3 text-right">{t('Check-Outs')}</th>
                  <th className="px-6 py-3 text-right">{t('Trend')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 tabular-nums">
                {weeklyTrend.map((day, index) => {
                  const prevDay = weeklyTrend[index - 1];
                  const trend = prevDay
                    ? day.check_ins - prevDay.check_ins
                    : 0;
                  return (
                    <tr key={day.date} className="hover:bg-gray-50">
                      <td className="px-6 py-3 text-gray-900">{formatDisplayDate(day.date)}</td>
                      <td className="px-6 py-3 text-right text-gray-900">{day.check_ins}</td>
                      <td className="px-6 py-3 text-right text-gray-900">{day.check_outs}</td>
                      <td className="px-6 py-3 text-right">
                        <span className={`font-medium ${
                          trend > 0 ? 'text-green-700' : trend < 0 ? 'text-red-700' : 'text-gray-400'
                        }`}>
                          {trend > 0 ? `+${trend}` : trend === 0 ? '–' : trend}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card padding="none" className="overflow-hidden">
        <h2 className={sectionTitleClass}>{t('Unit Attendance Summary')}</h2>
        {unitSummary.length === 0 ? (
          <p className="py-10 text-center text-gray-500">{t('No unit data available')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className={theadClass}>
                <tr>
                  <th className="px-6 py-3 text-left">{t('Unit')}</th>
                  <th className="px-6 py-3 text-right">{t('Scheduled')}</th>
                  <th className="px-6 py-3 text-right">{t('Present')}</th>
                  <th className="px-6 py-3 text-right">{t('Absent')}</th>
                  <th className="px-6 py-3 text-right">{t('Rate')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 tabular-nums">
                {unitSummary.map((summary) => (
                  <tr key={summary.unit.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3 font-medium text-gray-900">{summary.unit.name}</td>
                    <td className="px-6 py-3 text-right text-gray-700">{summary.scheduled_person_days}</td>
                    <td className="px-6 py-3 text-right font-medium text-green-700">{summary.present_person_days}</td>
                    <td className="px-6 py-3 text-right font-medium text-red-700">{summary.absent_person_days}</td>
                    <td className="px-6 py-3 text-right font-semibold text-gray-900">{Math.round(summary.attendance_rate)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card padding="none" className="overflow-hidden">
        <h2 className={sectionTitleClass}>{t('Daily Breakdown')}</h2>
        {dailySummaries.length === 0 ? (
          <p className="py-10 text-center text-gray-500">{t('No data available for selected period')}</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className={theadClass}>
                  <tr>
                    <th className="px-6 py-3 text-left">{t('Date')}</th>
                    <th className="px-6 py-3 text-right">{t('Check-Ins')}</th>
                    <th className="px-6 py-3 text-right">{t('Check-Outs')}</th>
                    <th className="px-6 py-3 text-right">{t('On-Time')}</th>
                    <th className="px-6 py-3 text-right">{t('Late')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 tabular-nums">
                  {dailySummaries.slice(0, 14).map((day) => (
                    <tr key={day.date} className="hover:bg-gray-50">
                      <td className="px-6 py-3 text-gray-900">{formatDisplayDate(day.date)}</td>
                      <td className="px-6 py-3 text-right text-gray-900">{day.check_ins}</td>
                      <td className="px-6 py-3 text-right text-gray-900">{day.check_outs}</td>
                      <td className="px-6 py-3 text-right text-green-700">{day.on_time}</td>
                      <td className="px-6 py-3 text-right text-yellow-700">{day.late}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {dailySummaries.length > 14 && (
              <p className="border-t border-gray-200 px-6 py-3 text-center text-sm text-gray-500">
                {t('Showing first 14 days. Export for full data.')}
              </p>
            )}
          </>
        )}
      </Card>
    </div>
  );
}

export default ReportsPage;
