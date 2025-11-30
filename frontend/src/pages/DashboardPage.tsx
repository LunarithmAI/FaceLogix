import { useEffect, useState } from 'react';
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
import { reportsApi, type DashboardStats } from '@/services/reports';

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setIsLoading(true);
      const data = await reportsApi.getDashboardStats();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text="Loading dashboard..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-600">{error}</p>
        <button
          onClick={loadStats}
          className="mt-4 text-primary-600 hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  const today = stats?.today;
  const attendanceRate = today
    ? Math.round((today.checked_in / today.total_employees) * 100)
    : 0;

  return (
    <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Welcome back! Here's today's overview.</p>
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
                <p className="text-sm font-medium text-gray-500">Total Users</p>
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
                <p className="text-sm font-medium text-gray-500">Active Devices</p>
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
                <p className="text-sm font-medium text-gray-500">Today's Check-ins</p>
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
                <p className="text-sm font-medium text-gray-500">Attendance Rate</p>
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
              <CardTitle>Today's Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Total Employees</span>
                  <span className="font-medium">{today?.total_employees || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Checked In</span>
                  <span className="font-medium text-green-600">
                    {today?.checked_in || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Checked Out</span>
                  <span className="font-medium text-blue-600">
                    {today?.checked_out || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Absent</span>
                  <span className="font-medium text-red-600">
                    {today?.absent || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Late Arrivals</span>
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
              <CardTitle>Quick Stats</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600">Pending Face Enrollments</span>
                  <span className="font-medium text-orange-600">
                    {stats?.pending_enrollments || 0}
                  </span>
                </div>
                {today?.average_check_in_time && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Avg Check-in Time</span>
                    <span className="font-medium">{today.average_check_in_time}</span>
                  </div>
                )}
                {today?.average_check_out_time && (
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Avg Check-out Time</span>
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
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <AttendanceList
              logs={stats?.recent_activity || []}
              emptyMessage="No recent activity"
            />
          </CardContent>
      </Card>
    </div>
  );
}

export default DashboardPage;
