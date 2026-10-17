import { useState } from 'react';
import type { FormEvent } from 'react';
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline';
import { useNavigate } from 'react-router';
import { Alert } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { useAuthStore } from '@/stores/authStore';
import { translate as t } from '@/i18n';

type LoginMode = 'user' | 'device';

export function LoginPage() {
  const navigate = useNavigate();
  const { loginUser, loginDevice, isLoading, error, clearError } = useAuthStore();
  const [mode, setMode] = useState<LoginMode>('user');
  const [organization, setOrganization] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [deviceSecret, setDeviceSecret] = useState('');
  const [showSecret, setShowSecret] = useState(false);

  const selectMode = (nextMode: LoginMode) => {
    setMode(nextMode);
    clearError();
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    clearError();
    try {
      if (mode === 'user') {
        await loginUser({ organization, email, password });
        void navigate('/admin', { replace: true });
      } else {
        await loginDevice({ device_id: deviceId, device_secret: deviceSecret });
        void navigate('/kiosk', { replace: true });
      }
    } catch {
      // The store exposes the normalized error in the form.
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-primary-700 via-primary-800 to-primary-950 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center justify-between text-white">
          <div className="flex items-center gap-3">
            <img src="/favicon.svg" alt="" className="h-11 w-11 rounded-full ring-2 ring-white/20" />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-primary-200">
                {t('Attendance operations')}
              </p>
              <h1 className="text-3xl font-bold tracking-tight">FaceLogix</h1>
            </div>
          </div>
          <LanguageSwitcher compact inverted />
        </div>

        <Card padding="lg" className="shadow-xl">
          <div className="mb-6 grid grid-cols-2 border-b border-gray-200" role="tablist" aria-label={t('Sign in')}>
            <button
              type="button"
              role="tab"
              id="login-tab-user"
              aria-selected={mode === 'user'}
              aria-controls="login-panel"
              onClick={() => selectMode('user')}
              className={`-mb-px min-h-11 border-b-2 px-3 py-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500 motion-reduce:transition-none ${
                mode === 'user'
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              {t('Staff sign in')}
            </button>
            <button
              type="button"
              role="tab"
              id="login-tab-device"
              aria-selected={mode === 'device'}
              aria-controls="login-panel"
              onClick={() => selectMode('device')}
              className={`-mb-px min-h-11 border-b-2 px-3 py-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500 motion-reduce:transition-none ${
                mode === 'device'
                  ? 'border-primary-600 text-primary-700'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              {t('Kiosk sign in')}
            </button>
          </div>

          <div id="login-panel" role="tabpanel" aria-labelledby={`login-tab-${mode}`}>
            <div className="mb-6">
              <h2 className="text-xl font-bold text-gray-900">
                {mode === 'user' ? t('Welcome back') : t('Activate this kiosk')}
              </h2>
              <p className="mt-1 text-sm text-gray-600">
                {mode === 'user'
                  ? t('Use your organization account to continue.')
                  : t('Use the one-time credentials issued by an administrator.')}
              </p>
            </div>

            {error && <Alert className="mb-4">{t(error)}</Alert>}

            <form onSubmit={(event) => void handleSubmit(event)} className="space-y-4">
              {mode === 'user' ? (
                <>
                  <Input
                    label={t('Organization')}
                    value={organization}
                    onChange={(event) => setOrganization(event.target.value)}
                    autoComplete="organization"
                    required
                  />
                  <Input
                    label={t('Email')}
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    autoComplete="email"
                    required
                  />
                </>
              ) : (
                <Input
                  label={t('Device ID')}
                  value={deviceId}
                  onChange={(event) => setDeviceId(event.target.value)}
                  autoComplete="username"
                  required
                />
              )}

              <div className="relative">
                <Input
                  label={mode === 'user' ? t('Password') : t('Device secret')}
                  type={showSecret ? 'text' : 'password'}
                  value={mode === 'user' ? password : deviceSecret}
                  onChange={(event) =>
                    mode === 'user'
                      ? setPassword(event.target.value)
                      : setDeviceSecret(event.target.value)
                  }
                  autoComplete={mode === 'user' ? 'current-password' : 'off'}
                  className="pr-12"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowSecret((visible) => !visible)}
                  className="absolute right-1 top-6 flex min-h-11 min-w-11 items-center justify-center rounded-lg text-gray-500 hover:text-gray-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                  aria-label={showSecret ? t('Hide secret') : t('Show secret')}
                  aria-pressed={showSecret}
                >
                  {showSecret ? (
                    <EyeSlashIcon className="h-5 w-5" aria-hidden="true" />
                  ) : (
                    <EyeIcon className="h-5 w-5" aria-hidden="true" />
                  )}
                </button>
              </div>

              <Button type="submit" className="w-full" isLoading={isLoading}>
                {mode === 'user' ? t('Sign in') : t('Open kiosk')}
              </Button>
            </form>
          </div>
        </Card>
      </div>
    </main>
  );
}

export default LoginPage;
