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
import { reportsApi } from '@/services/reports';
import { formatApiDate, formatDisplayDate } from '@/utils/date';
import { queryKeys } from '@/lib/queryClient';
import { translate as t } from '@/i18n';


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
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('Reports')}</h1>
          <p className="text-gray-500 mt-1">{t('Attendance analytics and export')}</p>
        </div>
      </div>

      {exportMutation.error !== null && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700" role="alert">
          {t(exportMutation.error.message)}
        </div>
      )}

      {/* Date Range & Export */}
      <Card>
        <div className="p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">{t('Generate Report')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
            <div className="flex items-end">
              <p className="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-600">
                {t('Export format: CSV')}
              </p>
            </div>
            <div className="flex items-end">
              <Button
                onClick={() => setAppliedRange(draftRange)}
                variant="secondary"
                className="w-full"
              >
                {t('Refresh')}
              </Button>
            </div>
            <div className="flex items-end">
              <Button
                onClick={() => exportMutation.mutate()}
                isLoading={exportMutation.isPending}
                leftIcon={<ArrowDownTrayIcon className="w-5 h-5" />}
                className="w-full"
              >
                {t('Export')}
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <div className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <CalendarIcon className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">{t('Days Analyzed')}</p>
                <p className="text-2xl font-bold text-gray-900">{dailySummaries.length}</p>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <UserGroupIcon className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">{t('Total Check-Ins')}</p>
                <p className="text-2xl font-bold text-gray-900">{totalCheckIns}</p>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <ChartBarIcon className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">{t('Total Check-Outs')}</p>
                <p className="text-2xl font-bold text-gray-900">{totalCheckOuts}</p>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <div className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <ClockIcon className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">{t('Avg On-Time Rate')}</p>
                <p className="text-2xl font-bold text-gray-900">{avgOnTime}%</p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Weekly Trend */}
      <Card>
        <div className="p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">{t('Weekly Attendance Trend')}</h2>
          {weeklyTrend.length === 0 ? (
            <p className="text-gray-500 text-center py-8">{t('No trend data available')}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-600">{t('Date')}</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">{t('Check-Ins')}</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">{t('Check-Outs')}</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">{t('Trend')}</th>
                  </tr>
                </thead>
                <tbody>
                  {weeklyTrend.map((day, index) => {
                    const prevDay = weeklyTrend[index - 1];
                    const trend = prevDay
                      ? day.check_ins - prevDay.check_ins
                      : 0;
                    return (
                      <tr key={day.date} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4 text-gray-900">
                          {formatDisplayDate(day.date)}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-900">
                          {day.check_ins}
                        </td>
                        <td className="py-3 px-4 text-right text-gray-900">
                          {day.check_outs}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className={`font-medium ${
                            trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-gray-500'
                          }`}>
                            {trend > 0 ? `+${trend}` : trend === 0 ? '-' : trend}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      {/* Unit Summary */}
      <Card>
        <div className="p-4">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('Unit Attendance Summary')}</h2>
          {unitSummary.length === 0 ? (
            <p className="py-8 text-center text-gray-500">{t('No unit data available')}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-4 py-3 text-left font-medium text-gray-600">{t('Unit')}</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600">{t('Scheduled')}</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600">{t('Present')}</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600">{t('Absent')}</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-600">{t('Rate')}</th>
                  </tr>
                </thead>
                <tbody>
                  {unitSummary.map((summary) => (
                    <tr key={summary.unit.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{summary.unit.name}</td>
                      <td className="px-4 py-3 text-right text-gray-700">{summary.scheduled_person_days}</td>
                      <td className="px-4 py-3 text-right font-medium text-green-700">{summary.present_person_days}</td>
                      <td className="px-4 py-3 text-right font-medium text-red-700">{summary.absent_person_days}</td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-900">{Math.round(summary.attendance_rate)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </Card>

      {/* Daily Breakdown */}
      <Card>
        <div className="p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">{t('Daily Breakdown')}</h2>
          {dailySummaries.length === 0 ? (
            <p className="text-gray-500 text-center py-8">{t('No data available for selected period')}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-600">{t('Date')}</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">{t('Check-Ins')}</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">{t('Check-Outs')}</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">{t('On-Time')}</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">{t('Late')}</th>
                  </tr>
                </thead>
                <tbody>
                  {dailySummaries.slice(0, 14).map((day) => (
                    <tr key={day.date} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-900">
                        {formatDisplayDate(day.date)}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-900">
                        {day.check_ins}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-900">
                        {day.check_outs}
                      </td>
                      <td className="py-3 px-4 text-right text-green-600">
                        {day.on_time}
                      </td>
                      <td className="py-3 px-4 text-right text-orange-600">
                        {day.late}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {dailySummaries.length > 14 && (
                <p className="text-center text-gray-500 mt-4 text-sm">
                  {t('Showing first 14 days. Export for full data.')}
                </p>
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

export default ReportsPage;
