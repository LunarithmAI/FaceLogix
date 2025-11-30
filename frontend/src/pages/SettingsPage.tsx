import { useState, useEffect } from 'react';
import {
  Cog6ToothIcon,
  BuildingOfficeIcon,
  ClockIcon,
  ShieldCheckIcon,
  ServerIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { useAuthStore } from '@/stores/authStore';
import { settingsApi, type OrgSettings, type OrgSettingsUpdate, type SystemInfo } from '@/services/settings';

// Timezone options
const TIMEZONES = [
  { value: 'UTC', label: 'UTC' },
  { value: 'America/New_York', label: 'Eastern Time (ET)' },
  { value: 'America/Chicago', label: 'Central Time (CT)' },
  { value: 'America/Denver', label: 'Mountain Time (MT)' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
  { value: 'Europe/London', label: 'London (GMT)' },
  { value: 'Europe/Paris', label: 'Paris (CET)' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
  { value: 'Asia/Shanghai', label: 'Shanghai (CST)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEDT)' },
];

export function SettingsPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.role === 'admin';

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [orgSettings, setOrgSettings] = useState<OrgSettings | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);

  // Form state
  const [formData, setFormData] = useState<OrgSettingsUpdate>({
    name: '',
    timezone: 'UTC',
    settings: {
      work_start_time: '09:00',
      work_end_time: '17:00',
      late_threshold_minutes: 15,
      require_liveness: true,
      allow_remote_checkin: false,
      face_match_threshold: 0.6,
    },
  });

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const [org, system] = await Promise.all([
        settingsApi.getOrgSettings().catch(() => null),
        settingsApi.getSystemInfo().catch(() => null),
      ]);

      if (org) {
        setOrgSettings(org);
        setFormData({
          name: org.name,
          timezone: org.timezone,
          settings: {
            work_start_time: org.settings?.work_start_time || '09:00',
            work_end_time: org.settings?.work_end_time || '17:00',
            late_threshold_minutes: org.settings?.late_threshold_minutes || 15,
            require_liveness: org.settings?.require_liveness ?? true,
            allow_remote_checkin: org.settings?.allow_remote_checkin ?? false,
            face_match_threshold: org.settings?.face_match_threshold || 0.6,
          },
        });
      }

      setSystemInfo(system);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!isAdmin) {
      setError('Only administrators can modify settings');
      return;
    }

    try {
      setIsSaving(true);
      setError(null);
      setSuccessMessage(null);

      const updated = await settingsApi.updateOrgSettings(formData);
      setOrgSettings(updated);
      setSuccessMessage('Settings saved successfully');

      // Clear success message after 3 seconds
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handleInputChange = (field: keyof OrgSettingsUpdate, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSettingsChange = (field: string, value: string | number | boolean) => {
    setFormData((prev) => ({
      ...prev,
      settings: { ...prev.settings, [field]: value },
    }));
  };

  const testFaceService = async () => {
    try {
      const result = await settingsApi.testFaceService();
      setSuccessMessage(`Face service is online (latency: ${result.latency_ms}ms)`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch {
      setError('Face service is not responding');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text="Loading settings..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 mt-1">Manage organization and system settings</p>
        </div>
        {isAdmin && (
          <Button onClick={handleSave} isLoading={isSaving}>
            Save Changes
          </Button>
        )}
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <ExclamationTriangleIcon className="w-5 h-5" />
          {error}
        </div>
      )}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <CheckCircleIcon className="w-5 h-5" />
          {successMessage}
        </div>
      )}

      {!isAdmin && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <ExclamationTriangleIcon className="w-5 h-5" />
          You have read-only access. Contact an administrator to make changes.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Organization Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BuildingOfficeIcon className="w-5 h-5 text-gray-500" />
              Organization
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Input
                label="Organization Name"
                value={formData.name || ''}
                onChange={(e) => handleInputChange('name', e.target.value)}
                disabled={!isAdmin}
              />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Timezone
                </label>
                <select
                  value={formData.timezone}
                  onChange={(e) => handleInputChange('timezone', e.target.value)}
                  disabled={!isAdmin}
                  className="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  {TIMEZONES.map((tz) => (
                    <option key={tz.value} value={tz.value}>
                      {tz.label}
                    </option>
                  ))}
                </select>
              </div>
              {orgSettings && (
                <div className="pt-2 text-sm text-gray-500">
                  <p>Slug: {orgSettings.slug}</p>
                  <p>Created: {new Date(orgSettings.created_at).toLocaleDateString()}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Work Hours */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ClockIcon className="w-5 h-5 text-gray-500" />
              Work Hours
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Input
                  label="Start Time"
                  type="time"
                  value={formData.settings?.work_start_time || '09:00'}
                  onChange={(e) => handleSettingsChange('work_start_time', e.target.value)}
                  disabled={!isAdmin}
                />
                <Input
                  label="End Time"
                  type="time"
                  value={formData.settings?.work_end_time || '17:00'}
                  onChange={(e) => handleSettingsChange('work_end_time', e.target.value)}
                  disabled={!isAdmin}
                />
              </div>
              <Input
                label="Late Threshold (minutes)"
                type="number"
                min={0}
                max={60}
                value={formData.settings?.late_threshold_minutes || 15}
                onChange={(e) => handleSettingsChange('late_threshold_minutes', parseInt(e.target.value))}
                disabled={!isAdmin}
              />
              <p className="text-sm text-gray-500">
                Employees arriving more than {formData.settings?.late_threshold_minutes || 15} minutes after start time will be marked as late.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Security Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheckIcon className="w-5 h-5 text-gray-500" />
              Security & Verification
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.settings?.require_liveness ?? true}
                  onChange={(e) => handleSettingsChange('require_liveness', e.target.checked)}
                  disabled={!isAdmin}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <div>
                  <span className="text-sm font-medium text-gray-700">Require Liveness Detection</span>
                  <p className="text-xs text-gray-500">Prevents photo/video spoofing attacks</p>
                </div>
              </label>

              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.settings?.allow_remote_checkin ?? false}
                  onChange={(e) => handleSettingsChange('allow_remote_checkin', e.target.checked)}
                  disabled={!isAdmin}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <div>
                  <span className="text-sm font-medium text-gray-700">Allow Remote Check-in</span>
                  <p className="text-xs text-gray-500">Allow employees to check in from any device</p>
                </div>
              </label>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Face Match Threshold ({((formData.settings?.face_match_threshold || 0.6) * 100).toFixed(0)}%)
                </label>
                <input
                  type="range"
                  min="0.4"
                  max="0.9"
                  step="0.05"
                  value={formData.settings?.face_match_threshold || 0.6}
                  onChange={(e) => handleSettingsChange('face_match_threshold', parseFloat(e.target.value))}
                  disabled={!isAdmin}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>More lenient</span>
                  <span>More strict</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* System Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ServerIcon className="w-5 h-5 text-gray-500" />
              System Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {systemInfo ? (
                <>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Version</span>
                    <span className="font-medium">{systemInfo.version}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Environment</span>
                    <span className="px-2 py-1 bg-gray-100 rounded text-sm font-medium">
                      {systemInfo.environment}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Database</span>
                    <span className={`flex items-center gap-1 ${
                      systemInfo.database_status === 'connected' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {systemInfo.database_status === 'connected' ? (
                        <CheckCircleIcon className="w-4 h-4" />
                      ) : (
                        <XCircleIcon className="w-4 h-4" />
                      )}
                      {systemInfo.database_status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Face Service</span>
                    <span className={`flex items-center gap-1 ${
                      systemInfo.face_service_status === 'online' ? 'text-green-600' : 
                      systemInfo.face_service_status === 'offline' ? 'text-red-600' : 'text-gray-600'
                    }`}>
                      {systemInfo.face_service_status === 'online' ? (
                        <CheckCircleIcon className="w-4 h-4" />
                      ) : systemInfo.face_service_status === 'offline' ? (
                        <XCircleIcon className="w-4 h-4" />
                      ) : null}
                      {systemInfo.face_service_status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Total Users</span>
                    <span className="font-medium">{systemInfo.total_users}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Total Devices</span>
                    <span className="font-medium">{systemInfo.total_devices}</span>
                  </div>
                  {isAdmin && (
                    <Button variant="secondary" onClick={testFaceService} className="w-full mt-2">
                      Test Face Service
                    </Button>
                  )}
                </>
              ) : (
                <div className="text-center py-4">
                  <p className="text-gray-500">System info not available</p>
                  <p className="text-sm text-gray-400 mt-1">
                    Settings endpoints may not be configured
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Feature Info */}
      <Card>
        <CardContent>
          <div className="flex items-start gap-4 py-2">
            <div className="p-2 bg-primary-100 rounded-lg">
              <Cog6ToothIcon className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <h3 className="font-medium text-gray-900">About Settings</h3>
              <p className="text-sm text-gray-500 mt-1">
                These settings affect how FaceLogix operates for your organization. 
                Changes to work hours and thresholds will apply to all future attendance records.
                Security settings affect the face recognition verification process.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default SettingsPage;
