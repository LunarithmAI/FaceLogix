import { useQuery } from '@tanstack/react-query';
import {
  UsersIcon,
  DeviceTabletIcon,
  ClipboardDocumentCheckIcon,
  ExclamationTriangleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
} from '@heroicons/react/24/outline';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { AttendanceList } from '@/components/attendance/AttendanceList';
import { Loading } from '@/components/ui/Loading';
import { Button } from '@/components/ui/Button';
import { PageHeader } from '@/components/ui/PageHeader';
import { StatCard } from '@/components/ui/StatCard';
import { reportsApi } from '@/services/reports';
import { queryKeys } from '@/lib/queryClient';
import { translate as t } from '@/i18n';

export function DashboardPage() {
  const {
    data: stats,
    isPending,
    error,
    refetch,
  } = useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: ({ signal }) => reportsApi.getDashboardStats(signal),
  });

  if (isPending) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text={t('Loading dashboard...')} />
      </div>
    );
  }

  if (error !== null) {
    return (
      <div className="py-12 text-center" role="alert">
        <ExclamationTriangleIcon className="mx-auto mb-4 h-12 w-12 text-red-500" aria-hidden="true" />
        <p className="text-red-700">{t(error.message)}</p>
        <Button
          type="button"
          variant="secondary"
          className="mt-4"
          onClick={() => void refetch()}
        >
          {t('Try again')}
        </Button>
      </div>
    );
  }

  const today = stats.today;
  const attendanceRate =
    today.total_employees > 0
      ? Math.round((today.checked_in / today.total_employees) * 100)
      : 0;

  const summaryRows = [
    { label: t('Total Employees'), value: today.total_employees, className: 'text-gray-900' },
    { label: t('Checked In'), value: today.checked_in, className: 'text-green-700' },
    { label: t('Checked Out'), value: today.checked_out, className: 'text-primary-700' },
    { label: t('Absent'), value: today.absent, className: 'text-red-700' },
    { label: t('Late Arrivals'), value: today.late_arrivals, className: 'text-yellow-700' },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('Dashboard')}
        description={t("Welcome back! Here's today's overview.")}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-6">
        <StatCard label={t('Total Users')} value={stats.total_users} icon={UsersIcon} />
        <StatCard
          label={t('Active Devices')}
          value={stats.active_devices}
          icon={DeviceTabletIcon}
          tone="neutral"
        />
        <StatCard
          label={t("Today's Check-ins")}
          value={today.checked_in}
          icon={ClipboardDocumentCheckIcon}
          tone="success"
        />
        <StatCard
          label={t('Attendance Rate')}
          value={`${attendanceRate}%`}
          icon={attendanceRate >= 80 ? ArrowTrendingUpIcon : ArrowTrendingDownIcon}
          tone={attendanceRate >= 80 ? 'success' : 'warning'}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>{t("Today's Summary")}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="divide-y divide-gray-100">
              {summaryRows.map((row) => (
                <div key={row.label} className="flex items-center justify-between py-2.5">
                  <dt className="text-gray-600">{row.label}</dt>
                  <dd className={`font-semibold tabular-nums ${row.className}`}>{row.value}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t('Quick Stats')}</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="divide-y divide-gray-100">
              <div className="flex items-center justify-between py-2.5">
                <dt className="text-gray-600">{t('Pending Face Enrollments')}</dt>
                <dd className="font-semibold tabular-nums text-yellow-700">
                  {stats.pending_enrollments}
                </dd>
              </div>
              {today.average_check_in_time && (
                <div className="flex items-center justify-between py-2.5">
                  <dt className="text-gray-600">{t('Avg Check-in Time')}</dt>
                  <dd className="font-semibold tabular-nums text-gray-900">
                    {today.average_check_in_time}
                  </dd>
                </div>
              )}
              {today.average_check_out_time && (
                <div className="flex items-center justify-between py-2.5">
                  <dt className="text-gray-600">{t('Avg Check-out Time')}</dt>
                  <dd className="font-semibold tabular-nums text-gray-900">
                    {today.average_check_out_time}
                  </dd>
                </div>
              )}
            </dl>
          </CardContent>
        </Card>
      </div>

      <Card padding="none" className="overflow-hidden">
        <CardHeader className="px-4 pt-4 sm:px-6 sm:pt-6">
          <CardTitle>{t('Recent Activity')}</CardTitle>
        </CardHeader>
        <AttendanceList logs={stats.recent_activity} emptyMessage={t('No recent activity')} />
      </Card>
    </div>
  );
}

export default DashboardPage;
