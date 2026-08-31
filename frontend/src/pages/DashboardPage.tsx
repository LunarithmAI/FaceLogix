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
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-600">{error.message}</p>
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

  return (
    <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('Dashboard')}</h1>
          <p className="text-gray-500 mt-1">{t("Welcome back! Here's today's overview.")}</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Total Employees */}
          <Card>
            <div className="flex items-center">
              <div className="p-3 bg-blue-100 rounded-lg">
                <UsersIcon className="w-6 h-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{t('Total Users')}</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stats?.total_users || 0}
                </p>
              </div>
            </div>
          </Card>

          {/* Active Devices */}
          <Card>
            <div className="flex items-center">
              <div className="p-3 bg-green-100 rounded-lg">
                <DeviceTabletIcon className="w-6 h-6 text-green-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{t('Active Devices')}</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stats?.active_devices || 0}
                </p>
              </div>
            </div>
          </Card>

          {/* Today's Check-ins */}
          <Card>
            <div className="flex items-center">
              <div className="p-3 bg-purple-100 rounded-lg">
                <ClipboardDocumentCheckIcon className="w-6 h-6 text-purple-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{t("Today's Check-ins")}</p>
                <p className="text-2xl font-bold text-gray-900">
                  {today?.checked_in || 0}
                </p>
              </div>
            </div>
          </Card>

          {/* Attendance Rate */}
          <Card>
            <div className="flex items-center">
              <div
                className={`p-3 rounded-lg ${
                  attendanceRate >= 80 ? 'bg-green-100' : 'bg-yellow-100'
                }`}
              >
                {attendanceRate >= 80 ? (
                  <ArrowTrendingUpIcon className="w-6 h-6 text-green-600" />
                ) : (
                  <ArrowTrendingDownIcon className="w-6 h-6 text-yellow-600" />
                )}
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500">{t('Attendance Rate')}</p>
                <p className="text-2xl font-bold text-gray-900">{attendanceRate}%</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Today's Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily Stats */}
          <Card>
            <CardHeader>
              <CardTitle>{t("Today's Summary")}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">{t('Total Employees')}</span>
                  <span className="font-medium">{today?.total_employees || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">{t('Checked In')}</span>
                  <span className="font-medium text-green-600">
                    {today?.checked_in || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">{t('Checked Out')}</span>
                  <span className="font-medium text-blue-600">
                    {today?.checked_out || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">{t('Absent')}</span>
                  <span className="font-medium text-red-600">
                    {today?.absent || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">{t('Late Arrivals')}</span>
                  <span className="font-medium text-yellow-600">
                    {today?.late_arrivals || 0}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Pending Enrollments */}
          <Card>
            <CardHeader>
              <CardTitle>{t('Quick Stats')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">{t('Pending Face Enrollments')}</span>
                  <span className="font-medium text-orange-600">
                    {stats?.pending_enrollments || 0}
                  </span>
                </div>
                {today?.average_check_in_time && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Avg Check-in Time')}</span>
                    <span className="font-medium">{today.average_check_in_time}</span>
                  </div>
                )}
                {today?.average_check_out_time && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Avg Check-out Time')}</span>
                    <span className="font-medium">{today.average_check_out_time}</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>{t('Recent Activity')}</CardTitle>
          </CardHeader>
          <CardContent>
            <AttendanceList
              logs={stats?.recent_activity || []}
              emptyMessage={t('No recent activity')}
            />
          </CardContent>
      </Card>
    </div>
  );
}

export default DashboardPage;
