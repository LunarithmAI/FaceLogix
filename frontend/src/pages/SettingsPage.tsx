import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Cog6ToothIcon,
  BuildingOfficeIcon,
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
import { settingsApi, type OrgSettingsUpdate } from '@/services/settings';
import { queryKeys } from '@/lib/queryClient';
import { ADMIN_ROLES } from '@/types/roles';
import { formatShortDate } from '@/utils/date';
import { translate as t } from '@/i18n';

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
  { value: 'Asia/Ho_Chi_Minh', label: 'Ho Chi Minh City (ICT)' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEDT)' },
];
interface LocalizedMessage {
  key: string;
  options?: Parameters<typeof t>[1];
}


export function SettingsPage() {
  const session = useAuthStore((state) => state.session);
  const queryClient = useQueryClient();
  const isAdmin =
    session?.kind === 'user' && ADMIN_ROLES.includes(session.user.role);
  const [actionError, setActionError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<LocalizedMessage | null>(null);
  const [isFormInitialized, setIsFormInitialized] = useState(false);

  // Form state
  const [formData, setFormData] = useState<OrgSettingsUpdate>({
    name: '',
    timezone: 'UTC',
    settings: {
      require_liveness: true,
      liveness_threshold: 0.8,
      face_match_threshold: 0.75,
    },
  });

  const orgQuery = useQuery({
    queryKey: queryKeys.settings,
    queryFn: ({ signal }) => settingsApi.getOrgSettings(signal),
  });
  const systemQuery = useQuery({
    queryKey: queryKeys.system,
    queryFn: ({ signal }) => settingsApi.getSystemInfo(signal),
  });
  const saveMutation = useMutation({
    mutationFn: settingsApi.updateOrgSettings,
    onMutate: () => {
      setActionError(null);
      setSuccessMessage(null);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(queryKeys.settings, updated);
      setSuccessMessage({ key: 'Settings saved successfully' });
    },
    onError: (error) => {
      setActionError(error.message);
    },
  });
  const testMutation = useMutation({
    mutationFn: settingsApi.testFaceService,
    onMutate: () => {
      setActionError(null);
      setSuccessMessage(null);
    },
    onSuccess: (result) => {
      setSuccessMessage({ key: 'Face service is online (latency: {{latency}}ms)', options: { latency: result.latency_ms } });
    },
    onError: () => {
      setActionError('Face service is not responding');
    },
  });
  const orgSettings = orgQuery.data ?? null;
  const systemInfo = systemQuery.data ?? null;
  const queryError = orgQuery.error ?? systemQuery.error;
  const error = actionError ?? queryError?.message ?? null;

  useEffect(() => {
    if (orgSettings === null) {
      return;
    }
    setFormData({
      name: orgSettings.name,
      timezone: orgSettings.timezone,
      settings: { ...orgSettings.settings },
    });
    setIsFormInitialized(true);
  }, [orgSettings]);

  const handleSave = () => {
    if (isAdmin) {
      saveMutation.mutate(formData);
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

  const testFaceService = () => {
    if (isAdmin) {
      testMutation.mutate();
    }
  };

  if (orgQuery.error !== null || (!orgQuery.isPending && orgSettings === null)) {
    return (
      <div className="p-6 text-center text-red-700" role="alert">
        <p>{t(orgQuery.error?.message ?? 'Organization settings are unavailable')}</p>
        <Button className="mt-4" onClick={() => void orgQuery.refetch()}>
          {t('Try again')}
        </Button>
      </div>
    );
  }

  if (orgQuery.isPending || systemQuery.isPending || !isFormInitialized) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text={t('Loading settings...')} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t('Settings')}</h1>
          <p className="text-gray-500 mt-1">{t('Manage organization and system settings')}</p>
        </div>
        {isAdmin && (
          <Button onClick={handleSave} isLoading={saveMutation.isPending}>
            {t('Save Changes')}
          </Button>
        )}
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <ExclamationTriangleIcon className="w-5 h-5" />
          {t(error)}
        </div>
      )}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <CheckCircleIcon className="w-5 h-5" />
          {t(successMessage.key, successMessage.options)}
        </div>
      )}

      {!isAdmin && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <ExclamationTriangleIcon className="w-5 h-5" />
          {t('You have read-only access. Contact an administrator to make changes.')}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Organization Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BuildingOfficeIcon className="w-5 h-5 text-gray-500" />
              {t('Organization')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Input
                label={t('Organization Name')}
                value={formData.name || ''}
                onChange={(e) => handleInputChange('name', e.target.value)}
                disabled={!isAdmin}
              />
              <div>
                <label htmlFor="organization-timezone" className="block text-sm font-medium text-gray-700 mb-1">
                  {t('Timezone')}
                </label>
                <select
                  id="organization-timezone"
                  value={formData.timezone}
                  onChange={(e) => handleInputChange('timezone', e.target.value)}
                  disabled={!isAdmin}
                  className="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  {TIMEZONES.map((tz) => (
                    <option key={tz.value} value={tz.value}>
                      {t(tz.label)}
                    </option>
                  ))}
                </select>
              </div>
              {orgSettings && (
                <div className="pt-2 text-sm text-gray-500">
                  <p>{t('Slug')}: {orgSettings.slug}</p>
                  <p>{t('Created')}: {formatShortDate(orgSettings.created_at)}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>


        {/* Security Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheckIcon className="w-5 h-5 text-gray-500" />
              {t('Security & Verification')}
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
                  <span className="text-sm font-medium text-gray-700">{t('Require Liveness Detection')}</span>
                  <p className="text-xs text-gray-500">{t('Prevents photo/video spoofing attacks')}</p>
                </div>
              </label>

              <div>
                <label
                  htmlFor="liveness-threshold"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  {t('Liveness Threshold ({{percent}}%)', { percent: ((formData.settings?.liveness_threshold ?? 0.8) * 100).toFixed(0) })}
                </label>
                <input
                  id="liveness-threshold"
                  type="range"
                  min="0.5"
                  max="0.99"
                  step="0.01"
                  value={formData.settings?.liveness_threshold ?? 0.8}
                  onChange={(e) => handleSettingsChange('liveness_threshold', parseFloat(e.target.value))}
                  disabled={!isAdmin}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>

              <div>
                <label
                  htmlFor="face-match-threshold"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  {t('Face Match Threshold ({{percent}}%)', { percent: ((formData.settings?.face_match_threshold ?? 0.75) * 100).toFixed(0) })}
                </label>
                <input
                  id="face-match-threshold"
                  type="range"
                  min="0.3"
                  max="0.95"
                  step="0.05"
                  value={formData.settings?.face_match_threshold ?? 0.75}
                  onChange={(e) => handleSettingsChange('face_match_threshold', parseFloat(e.target.value))}
                  disabled={!isAdmin}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>{t('More lenient')}</span>
                  <span>{t('More strict')}</span>
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
              {t('System Status')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {systemInfo ? (
                <>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Version')}</span>
                    <span className="font-medium">{systemInfo.version}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Environment')}</span>
                    <span className="px-2 py-1 bg-gray-100 rounded text-sm font-medium">
                      {systemInfo.environment}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Database')}</span>
                    <span className={`flex items-center gap-1 ${
                      systemInfo.database_status === 'connected' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {systemInfo.database_status === 'connected' ? (
                        <CheckCircleIcon className="w-4 h-4" />
                      ) : (
                        <XCircleIcon className="w-4 h-4" />
                      )}
                      {t(systemInfo.database_status)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Face Service')}</span>
                    <span className={`flex items-center gap-1 ${
                      systemInfo.face_service_status === 'online' ? 'text-green-600' : 
                      systemInfo.face_service_status === 'offline' ? 'text-red-600' : 'text-gray-600'
                    }`}>
                      {systemInfo.face_service_status === 'online' ? (
                        <CheckCircleIcon className="w-4 h-4" />
                      ) : systemInfo.face_service_status === 'offline' ? (
                        <XCircleIcon className="w-4 h-4" />
                      ) : null}
                      {t(systemInfo.face_service_status)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Total Users')}</span>
                    <span className="font-medium">{systemInfo.total_users}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Total Devices')}</span>
                    <span className="font-medium">{systemInfo.total_devices}</span>
                  </div>
                  {isAdmin && (
                    <Button
                      variant="secondary"
                      onClick={testFaceService}
                      isLoading={testMutation.isPending}
                      className="w-full mt-2"
                    >
                      {t('Test Face Service')}
                    </Button>
                  )}
                </>
              ) : (
                <div className="text-center py-4">
                  <p className="text-gray-500">{t('System info not available')}</p>
                  <p className="text-sm text-gray-400 mt-1">
                    {t('Settings endpoints may not be configured')}
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
              <h3 className="font-medium text-gray-900">{t('About Settings')}</h3>
              <p className="text-sm text-gray-500 mt-1">
                {t('These settings affect how FaceLogix operates for your organization. Changes to work hours and thresholds will apply to all future attendance records. Security settings affect the face recognition verification process.')}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

export default SettingsPage;
