import { useState } from 'react';
import type { FormEvent } from 'react';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import { useLocation, useNavigate } from 'react-router';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useAuthStore } from '@/stores/authStore';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { translate as t } from '@/i18n';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isLoading, error, clearError } = useAuthStore();
  const [organization, setOrganization] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const locationState: unknown = location.state;
  const returnLocation =
    typeof locationState === 'object' &&
    locationState !== null &&
    'from' in locationState &&
    typeof locationState.from === 'object' &&
    locationState.from !== null &&
    'pathname' in locationState.from &&
    typeof locationState.from.pathname === 'string'
      ? locationState.from.pathname
      : '/';

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    clearError();
    try {
      await login({ organization, email, password });
      void navigate(returnLocation, { replace: true });
    } catch {
      // The auth store exposes the normalized error below the form heading.
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-primary-700 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-4 flex justify-end">
          <LanguageSwitcher compact inverted />
        </div>
        <div className="mb-8 text-center">
          <h1 className="mb-2 text-4xl font-bold text-white">FaceLogix</h1>
          <p className="text-primary-100">{t('Face Recognition Attendance System')}</p>
        </div>

        <Card className="motion-safe:animate-fade-in">
          <h2 className="mb-6 text-2xl font-semibold text-gray-900">{t('Sign in to your account')}</h2>

          {error !== null && (
            <div
              className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"
              role="alert"
            >
              {t(error)}
            </div>
          )}

          <form onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
            <Input
              label={t('Organization')}
              type="text"
              value={organization}
              onChange={(event) => setOrganization(event.target.value)}
              placeholder="your-workspace"
              required
              autoComplete="organization"
              autoFocus
            />
            <Input
              label={t('Email address')}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
              autoComplete="email"
            />

            <div className="relative">
              <Input
                label={t('Password')}
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="pr-12"
                placeholder={t('Enter your password')}
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                className="absolute bottom-0 right-0 flex min-h-11 min-w-11 items-center justify-center rounded-lg text-gray-500 hover:text-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                aria-label={showPassword ? t('Hide password') : t('Show password')}
              >
                {showPassword ? (
                  <EyeSlashIcon className="h-5 w-5" aria-hidden="true" />
                ) : (
                  <EyeIcon className="h-5 w-5" aria-hidden="true" />
                )}
              </button>
            </div>

            <Button
              type="submit"
              className="w-full"
              size="lg"
              isLoading={isLoading}
              loadingText={t('Signing in')}
            >
              {t('Sign in')}
            </Button>
          </form>
        </Card>
      </div>
    </main>
  );
}

export default LoginPage;
