import { useState, useEffect } from 'react';
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
import { reportsApi, type ExportParams } from '@/services/reports';
import type { DailySummary } from '@/types/attendance';
import { formatApiDate, formatDisplayDate } from '@/utils/date';

interface WeeklyTrend {
  date: string;
  check_ins: number;
  check_outs: number;
}

interface DepartmentSummary {
  department: string;
  present: number;
  absent: number;
}

export function ReportsPage() {
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [dailySummaries, setDailySummaries] = useState<DailySummary[]>([]);
  const [weeklyTrend, setWeeklyTrend] = useState<WeeklyTrend[]>([]);
  const [departmentSummary, setDepartmentSummary] = useState<DepartmentSummary[]>([]);

  // Date range for reports
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return formatApiDate(date);
  });
  const [endDate, setEndDate] = useState(() => formatApiDate(new Date()));
  const [exportFormat, setExportFormat] = useState<'csv' | 'xlsx' | 'pdf'>('csv');

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      setIsLoading(true);
      const [summaries, trend, departments] = await Promise.all([
        reportsApi.getDailySummaries(startDate, endDate),
        reportsApi.getWeeklyTrend(),
        reportsApi.getDepartmentSummary(),
      ]);
      setDailySummaries(summaries);
      setWeeklyTrend(trend);
      setDepartmentSummary(departments);
    } catch (error) {
      console.error('Failed to load reports:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      setIsExporting(true);
      const params: ExportParams = {
        start_date: startDate,
        end_date: endDate,
        format: exportFormat,
      };
      const blob = await reportsApi.exportReport(params);

      // Download file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `attendance_report_${startDate}_${endDate}.${exportFormat}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to export report:', error);
    } finally {
      setIsExporting(false);
    }
  };

  // Calculate summary stats
  const totalCheckIns = dailySummaries.reduce((sum, d) => sum + (d.total_check_ins || 0), 0);
  const totalCheckOuts = dailySummaries.reduce((sum, d) => sum + (d.total_check_outs || 0), 0);
  const avgOnTime = dailySummaries.length > 0
    ? Math.round(dailySummaries.reduce((sum, d) => sum + (d.on_time_percentage || 0), 0) / dailySummaries.length)
    : 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text="Loading reports..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Reports</h1>
          <p className="text-gray-500 mt-1">Attendance analytics and export</p>
        </div>
      </div>

      {/* Date Range & Export */}
      <Card>
        <div className="p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Generate Report</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
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
                Export Format
              </label>
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as 'csv' | 'xlsx' | 'pdf')}
                className="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="csv">CSV</option>
                <option value="xlsx">Excel (XLSX)</option>
                <option value="pdf">PDF</option>
              </select>
            </div>
            <div className="flex items-end">
              <Button onClick={loadReports} variant="secondary" className="w-full">
                Refresh
              </Button>
            </div>
            <div className="flex items-end">
              <Button
                onClick={handleExport}
                isLoading={isExporting}
                leftIcon={<ArrowDownTrayIcon className="w-5 h-5" />}
                className="w-full"
              >
                Export
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
                <p className="text-sm text-gray-500">Days Analyzed</p>
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
                <p className="text-sm text-gray-500">Total Check-Ins</p>
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
                <p className="text-sm text-gray-500">Total Check-Outs</p>
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
                <p className="text-sm text-gray-500">Avg On-Time Rate</p>
                <p className="text-2xl font-bold text-gray-900">{avgOnTime}%</p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Weekly Trend */}
      <Card>
        <div className="p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Weekly Attendance Trend</h2>
          {weeklyTrend.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No trend data available</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Date</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Check-Ins</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Check-Outs</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Trend</th>
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

      {/* Department Summary */}
      <Card>
        <div className="p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Department Attendance Summary</h2>
          {departmentSummary.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No department data available</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Department</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Present</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Absent</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {departmentSummary.map((dept) => {
                    const total = dept.present + dept.absent;
                    const rate = total > 0 ? Math.round((dept.present / total) * 100) : 0;
                    return (
                      <tr key={dept.department} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4 text-gray-900 font-medium">
                          {dept.department || 'Unassigned'}
                        </td>
                        <td className="py-3 px-4 text-right text-green-600 font-medium">
                          {dept.present}
                        </td>
                        <td className="py-3 px-4 text-right text-red-600 font-medium">
                          {dept.absent}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            rate >= 90 ? 'bg-green-100 text-green-800' :
                            rate >= 70 ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {rate}%
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

      {/* Daily Breakdown */}
      <Card>
        <div className="p-4">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Daily Breakdown</h2>
          {dailySummaries.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No data available for selected period</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-600">Date</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Check-Ins</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Check-Outs</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">On-Time</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-600">Late</th>
                  </tr>
                </thead>
                <tbody>
                  {dailySummaries.slice(0, 14).map((day) => (
                    <tr key={day.date} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-900">
                        {formatDisplayDate(day.date)}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-900">
                        {day.total_check_ins || 0}
                      </td>
                      <td className="py-3 px-4 text-right text-gray-900">
                        {day.total_check_outs || 0}
                      </td>
                      <td className="py-3 px-4 text-right text-green-600">
                        {day.on_time_count || 0}
                      </td>
                      <td className="py-3 px-4 text-right text-orange-600">
                        {day.late_count || 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {dailySummaries.length > 14 && (
                <p className="text-center text-gray-500 mt-4 text-sm">
                  Showing first 14 days. Export for full data.
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
