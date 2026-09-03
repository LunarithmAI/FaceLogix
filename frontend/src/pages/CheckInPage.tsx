import { useEffect, useRef, useState } from 'react';
import {
  ArrowLeftOnRectangleIcon,
  ArrowPathIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/solid';
import { StatusMessage } from '@/components/attendance/StatusMessage';
import { CameraView } from '@/components/camera/CameraView';
import type { CameraViewHandle } from '@/components/camera/CameraView';
import { Button } from '@/components/ui/Button';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { useCheckIn } from '@/hooks/useCheckIn';
import { devicesApi } from '@/services/devices';
import { useAuthStore } from '@/stores/authStore';
import type { CheckType } from '@/types/attendance';
import { translate as t } from '@/i18n';

export function CheckInPage() {
  const session = useAuthStore((state) => state.session);
  const logout = useAuthStore((state) => state.logout);
  const device = session?.kind === 'device' ? session.device : null;
  const [settings, setSettings] = useState(device?.settings ?? null);
  const [mode, setMode] = useState<CheckType>(device?.settings.default_mode ?? 'check_in');
  const [captureError, setCaptureError] = useState<string | null>(null);
  const cameraRef = useRef<CameraViewHandle>(null);
  const resetTimerRef = useRef<number | null>(null);
  const { checkIn, checkOut, isLoading, result, error, reset } = useCheckIn();
  const resetRef = useRef(reset);

  useEffect(() => {
    resetRef.current = reset;
  }, [reset]);

  useEffect(() => {
    const heartbeat = async () => {
      const latest = await devicesApi.heartbeat();
      setSettings(latest);
      setMode((current) => {
        const enabled = current === 'check_in' ? latest.allow_check_in : latest.allow_check_out;
        return enabled ? current : latest.default_mode;
      });
    };
    void heartbeat().catch(() => undefined);
    const interval = window.setInterval(() => void heartbeat().catch(() => undefined), 60_000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (result === null) return;
    resetTimerRef.current = window.setTimeout(() => resetRef.current(), 5_000);
    return () => {
      if (resetTimerRef.current !== null) {
        window.clearTimeout(resetTimerRef.current);
        resetTimerRef.current = null;
      }
    };
  }, [result]);

  const handleReset = () => {
    if (resetTimerRef.current !== null) {
      window.clearTimeout(resetTimerRef.current);
      resetTimerRef.current = null;
    }
    setCaptureError(null);
    reset();
  };

  const handleAction = () => {
    if (isLoading) return;
    const imageData = cameraRef.current?.captureFrame() ?? null;
    if (imageData === null) {
      setCaptureError('The camera is not ready. Wait for the live preview, then try again.');
      return;
    }
    setCaptureError(null);
    const request = mode === 'check_in' ? checkIn(imageData) : checkOut(imageData);
    void request.catch(() => undefined);
  };

  const canToggle = settings?.allow_check_in === true && settings.allow_check_out === true;
  const toggleMode = () => {
    if (!canToggle) return;
    setMode((current) => (current === 'check_in' ? 'check_out' : 'check_in'));
    handleReset();
  };

  return (
    <div className="safe-top safe-bottom min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-lg flex-wrap items-center justify-between gap-3 px-4 py-3">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">FaceLogix</h1>
            {device !== null && <p className="text-sm text-gray-500">{device.name}</p>}
          </div>
          <div className="flex items-center gap-2">
            <LanguageSwitcher compact />
            {canToggle && (
              <Button type="button" variant="secondary" size="sm" onClick={toggleMode}>
                {mode === 'check_in' ? (
                  <><ArrowLeftOnRectangleIcon className="mr-2 h-4 w-4" />{t('Check Out')}</>
                ) : (
                  <><ArrowRightOnRectangleIcon className="mr-2 h-4 w-4" />{t('Check In')}</>
                )}
              </Button>
            )}
            <Button type="button" variant="ghost" size="sm" onClick={() => void logout()}>
              {t('Sign out')}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-lg px-4 py-6">
        <div className="mb-4 text-center">
          <span className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium ${
            mode === 'check_in' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
          }`}>
            {mode === 'check_in' ? <ArrowRightOnRectangleIcon className="h-5 w-5" /> : <ArrowLeftOnRectangleIcon className="h-5 w-5" />}
            {mode === 'check_in' ? t('Check In Mode') : t('Check Out Mode')}
          </span>
        </div>

        <div className="mb-6">
          <CameraView
            ref={cameraRef}
            showGuide={result === null}
            className="mx-auto aspect-[3/4] w-full max-w-sm"
            initialFacing={settings?.camera_facing}
          />
        </div>

        {captureError !== null && (
          <div className="mb-4 border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800" role="alert">{t(captureError)}</div>
        )}
        {error !== null && (
          <div className="mb-4 border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">{t(error.message)}</div>
        )}

        {!settings?.allow_check_in && !settings?.allow_check_out ? (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900" role="status">
            {t('Attendance actions are disabled for this kiosk.')}
          </div>
        ) : result !== null ? (
          <div className="mb-6">
            <StatusMessage result={result} />
            <Button type="button" variant="secondary" onClick={handleReset} className="mt-4 w-full" leftIcon={<ArrowPathIcon className="h-5 w-5" />}>
              {t('Reset')}
            </Button>
          </div>
        ) : (
          <Button
            type="button"
            variant={mode === 'check_in' ? 'success' : 'primary'}
            size="xl"
            onClick={handleAction}
            disabled={isLoading}
            isLoading={isLoading}
            loadingText={t('Processing')}
            className="w-full touch-manipulation select-none rounded-xl font-semibold"
            leftIcon={mode === 'check_in' ? <ArrowRightOnRectangleIcon className="h-6 w-6" /> : <ArrowLeftOnRectangleIcon className="h-6 w-6" />}
          >
            {mode === 'check_in' ? t('Check In') : t('Check Out')}
          </Button>
        )}

        <div className="mt-8 text-center text-sm text-gray-500">
          <p>{t('Position your face within the oval guide.')}</p>
          <p className="mt-1">{t('Use even lighting and keep the camera steady.')}</p>
        </div>
      </main>
    </div>
  );
}

export default CheckInPage;
