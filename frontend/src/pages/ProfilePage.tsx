import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  UserCircleIcon,
  KeyIcon,
  ShieldCheckIcon,
  CalendarIcon,
  ArrowLeftOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { Alert } from '@/components/ui/Alert';
import { Badge, RoleBadge, StatusBadge } from '@/components/ui/Badge';
import { PageHeader } from '@/components/ui/PageHeader';
import { authApi } from '@/services/auth';
import { queryKeys } from '@/lib/queryClient';
import { formatShortDate } from '@/utils/date';
import { translate as t } from '@/i18n';
import { useAuthStore } from '@/stores/authStore';


export function ProfilePage() {
  const logout = useAuthStore((state) => state.logout);
  const profileQuery = useQuery({
    queryKey: queryKeys.profile,
    queryFn: ({ signal }) => authApi.getCurrentUser(signal),
  });
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Password change form
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);

  const passwordMutation = useMutation({
    mutationFn: () => authApi.changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setSuccessMessage('Password changed successfully');
      setShowPasswordForm(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    },
    onError: (error) => {
      setPasswordError(error.message);
    },
  });

  const handleChangePassword = (event: React.FormEvent) => {
    event.preventDefault();
    setPasswordError(null);

    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match');
      return;
    }

    passwordMutation.mutate();
  };

  if (profileQuery.isPending) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loading size="lg" text={t('Loading profile...')} />
      </div>
    );
  }

  if (profileQuery.error !== null || profileQuery.data === undefined) {
    return (
      <div className="p-6 text-center text-red-700" role="alert">
        <p>{t(profileQuery.error?.message ?? 'Profile data is unavailable')}</p>
        <Button className="mt-4" onClick={() => void profileQuery.refetch()}>
          {t('Try again')}
        </Button>
      </div>
    );
  }

  const displayProfile = profileQuery.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t('Your Profile')}
        description={t('View and manage your account information')}
        actions={
          <Button
            type="button"
            variant="secondary"
            onClick={() => void logout()}
            leftIcon={<ArrowLeftOnRectangleIcon className="h-5 w-5" aria-hidden="true" />}
          >
            {t('Sign out')}
          </Button>
        }
      />

      {successMessage && <Alert variant="success">{t(successMessage)}</Alert>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <Card className="lg:col-span-1">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-full bg-primary-100 ring-4 ring-primary-50">
                <span className="text-3xl font-bold text-primary-700">
                  {displayProfile.name?.charAt(0).toUpperCase() || 'U'}
                </span>
              </div>
              <h2 className="text-xl font-semibold text-gray-900">{displayProfile.name}</h2>
              <p className="text-gray-500 mt-1">{displayProfile.email || t('No email set')}</p>
              <div className="mt-3">
                <RoleBadge role={displayProfile.role} />
              </div>
              
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                <StatusBadge status={displayProfile.is_active ? 'active' : 'inactive'} />
                <Badge variant={displayProfile.enrolled_at ? 'success' : 'warning'} dot>
                  {displayProfile.enrolled_at ? t('Face Enrolled') : t('Not Enrolled')}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Details Card */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCircleIcon className="w-5 h-5 text-gray-500" aria-hidden="true" />
              {t('Account Details')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <dt className="block text-sm font-medium text-gray-500">{t('Full Name')}</dt>
                  <dd className="mt-1 text-gray-900">{displayProfile.name}</dd>
                </div>
                <div>
                  <dt className="block text-sm font-medium text-gray-500">{t('Email Address')}</dt>
                  <dd className="mt-1 text-gray-900">{displayProfile.email || t('Not set')}</dd>
                </div>
                <div>
                  <dt className="block text-sm font-medium text-gray-500">{t('Unit')}</dt>
                  <dd className="mt-1 text-gray-900">{displayProfile.current_unit?.name || t('Not assigned')}</dd>
                </div>
                <div>
                  <dt className="block text-sm font-medium text-gray-500">{t('Shift')}</dt>
                  <dd className="mt-1 text-gray-900">{displayProfile.current_shift?.name || t('Not assigned')}</dd>
                </div>
                <div>
                  <dt className="block text-sm font-medium text-gray-500">{t('Member Since')}</dt>
                  <dd className="mt-1 text-gray-900 flex items-center gap-1">
                    <CalendarIcon className="w-4 h-4 text-gray-400" aria-hidden="true" />
                    {formatShortDate(displayProfile.created_at)}
                  </dd>
                </div>
              </dl>

              {displayProfile.enrolled_at && (
                <div className="pt-4 border-t border-gray-100">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <ShieldCheckIcon className="w-5 h-5 text-green-500" aria-hidden="true" />
                    {t('Face enrolled on {{date}}', { date: formatShortDate(displayProfile.enrolled_at) })}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Security Card */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyIcon className="w-5 h-5 text-gray-500" aria-hidden="true" />
              {t('Security')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!showPasswordForm ? (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-gray-900">{t('Password')}</p>
                  <p className="text-sm text-gray-500">{t('Change your account password')}</p>
                </div>
                <Button variant="secondary" onClick={() => setShowPasswordForm(true)}>
                  {t('Change Password')}
                </Button>
              </div>
            ) : (
              <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
                {passwordError && <Alert>{t(passwordError)}</Alert>}
                <Input
                  label={t('Current Password')}
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                />
                <Input
                  label={t('New Password')}
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  helperText={t('Must be at least 8 characters')}
                />
                <Input
                  label={t('Confirm New Password')}
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
                <div className="flex gap-3">
                  <Button type="submit" isLoading={passwordMutation.isPending}>
                    {t('Update Password')}
                  </Button>
                  <Button 
                    type="button" 
                    variant="secondary" 
                    onClick={() => {
                      setShowPasswordForm(false);
                      setPasswordError(null);
                      setCurrentPassword('');
                      setNewPassword('');
                      setConfirmPassword('');
                    }}
                  >
                    {t('Cancel')}
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default ProfilePage;
