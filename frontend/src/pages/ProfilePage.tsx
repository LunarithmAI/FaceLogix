import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  UserCircleIcon,
  KeyIcon,
  ShieldCheckIcon,
  CheckCircleIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Loading } from '@/components/ui/Loading';
import { RoleBadge } from '@/components/ui/Badge';
import { authApi } from '@/services/auth';
import { queryKeys } from '@/lib/queryClient';
import { formatShortDate } from '@/utils/date';
import { translate as t } from '@/i18n';


export function ProfilePage() {
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
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{t('Your Profile')}</h1>
        <p className="text-gray-500 mt-1">{t('View and manage your account information')}</p>
      </div>

      {/* Messages */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2">
          <CheckCircleIcon className="w-5 h-5" />
          {t(successMessage)}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <Card className="lg:col-span-1">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="w-24 h-24 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl font-bold text-primary-700">
                  {displayProfile.name?.charAt(0) || 'U'}
                </span>
              </div>
              <h2 className="text-xl font-semibold text-gray-900">{displayProfile.name}</h2>
              <p className="text-gray-500 mt-1">{displayProfile.email || t('No email set')}</p>
              <div className="mt-3">
                <RoleBadge role={displayProfile.role} />
              </div>
              
              {/* Status badges */}
              <div className="flex justify-center gap-2 mt-4">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  displayProfile.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {displayProfile.is_active ? t('Active') : t('Inactive')}
                </span>
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  displayProfile.enrolled_at ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                  {displayProfile.enrolled_at ? t('Face Enrolled') : t('Not Enrolled')}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Details Card */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCircleIcon className="w-5 h-5 text-gray-500" />
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
                  <dt className="block text-sm font-medium text-gray-500">{t('Department')}</dt>
                  <dd className="mt-1 text-gray-900">{displayProfile.department || t('Not assigned')}</dd>
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
              <KeyIcon className="w-5 h-5 text-gray-500" />
              {t('Security')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!showPasswordForm ? (
              <div className="flex items-center justify-between">
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
                {passwordError && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-sm">
                    {t(passwordError)}
                  </div>
                )}
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
