import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Cog6ToothIcon,
  BuildingOfficeIcon,
  ShieldCheckIcon,
  ServerIcon,
  CheckCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { Alert } from '@/components/ui/Alert';
import { Badge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { Select } from '@/components/ui/Select';
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
      <PageHeader
        title={t('Settings')}
        description={t('Manage organization and system settings')}
        actions={
          isAdmin ? (
            <Button onClick={handleSave} isLoading={saveMutation.isPending}>
              {t('Save Changes')}
            </Button>
          ) : undefined
        }
      />

      {error && <Alert>{t(error)}</Alert>}
      {successMessage && (
        <Alert variant="success">{t(successMessage.key, successMessage.options)}</Alert>
      )}

      {!isAdmin && (
        <Alert variant="warning">
          {t('You have read-only access. Contact an administrator to make changes.')}
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Organization Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BuildingOfficeIcon className="w-5 h-5 text-gray-500" aria-hidden="true" />
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
              <Select
                id="organization-timezone"
                label={t('Timezone')}
                value={formData.timezone}
                onChange={(e) => handleInputChange('timezone', e.target.value)}
                disabled={!isAdmin}
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz.value} value={tz.value}>
                    {t(tz.label)}
                  </option>
                ))}
              </Select>
              {orgSettings && (
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 border-t border-gray-100 pt-4 text-sm">
                  <dt className="text-gray-500">{t('Slug')}</dt>
                  <dd className="font-mono text-gray-900">{orgSettings.slug}</dd>
                  <dt className="text-gray-500">{t('Created')}</dt>
                  <dd className="text-gray-900">{formatShortDate(orgSettings.created_at)}</dd>
                </dl>
              )}
            </div>
          </CardContent>
        </Card>


        {/* Security Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheckIcon className="w-5 h-5 text-gray-500" aria-hidden="true" />
              {t('Security & Verification')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  checked={formData.settings?.require_liveness ?? true}
                  onChange={(e) => handleSettingsChange('require_liveness', e.target.checked)}
                  disabled={!isAdmin}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 accent-primary-600"
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
                  className="w-full cursor-pointer accent-primary-600 disabled:cursor-not-allowed"
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
                  className="w-full cursor-pointer accent-primary-600 disabled:cursor-not-allowed"
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
              <ServerIcon className="w-5 h-5 text-gray-500" aria-hidden="true" />
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
                    <Badge>{systemInfo.environment}</Badge>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Database')}</span>
                    <span className={`flex items-center gap-1 ${
                      systemInfo.database_status === 'connected' ? 'text-green-700' : 'text-red-700'
                    }`}>
                      {systemInfo.database_status === 'connected' ? (
                        <CheckCircleIcon className="w-4 h-4" aria-hidden="true" />
                      ) : (
                        <XCircleIcon className="w-4 h-4" aria-hidden="true" />
                      )}
                      {t(systemInfo.database_status)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">{t('Face Service')}</span>
                    <span className={`flex items-center gap-1 ${
                      systemInfo.face_service_status === 'online' ? 'text-green-700' : 
                      systemInfo.face_service_status === 'offline' ? 'text-red-700' : 'text-gray-600'
                    }`}>
                      {systemInfo.face_service_status === 'online' ? (
                        <CheckCircleIcon className="w-4 h-4" aria-hidden="true" />
                      ) : systemInfo.face_service_status === 'offline' ? (
                        <XCircleIcon className="w-4 h-4" aria-hidden="true" />
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
              <Cog6ToothIcon className="w-6 h-6 text-primary-600" aria-hidden="true" />
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
