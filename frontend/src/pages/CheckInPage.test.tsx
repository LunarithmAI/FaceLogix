import type * as ReactModule from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CameraViewHandle } from '@/components/camera/CameraView';
import { useCheckIn } from '@/hooks/useCheckIn';
import { CheckInPage } from '@/pages/CheckInPage';

const cameraState = vi.hoisted(() => ({ frame: null as string | null }));
vi.mock('@/components/camera/CameraView', async () => {
  const React = await vi.importActual<typeof ReactModule>('react');
  return {
    CameraView: React.forwardRef<CameraViewHandle>(function MockCameraView(_, ref) {
      React.useImperativeHandle(ref, () => ({ captureFrame: () => cameraState.frame }));
      return React.createElement('div', null, 'Live camera preview');
    }),
  };
});
vi.mock('@/hooks/useCheckIn', () => ({ useCheckIn: vi.fn() }));

describe('check-in page states', () => {
  beforeEach(() => {
    cameraState.frame = null;
    vi.mocked(useCheckIn).mockReturnValue({
      checkIn: vi.fn().mockResolvedValue({ status: 'success', message: 'Recorded' }),
      checkOut: vi.fn().mockResolvedValue({ status: 'success', message: 'Recorded' }),
      isLoading: false,
      result: null,
      error: null,
      lastCheckType: null,
      reset: vi.fn(),
    });
  });

  it('shows a visible error when no camera frame is ready', async () => {
    const user = userEvent.setup();
    render(<CheckInPage />);

    await user.click(screen.getByRole('button', { name: 'Check In' }));

    expect(screen.getByRole('alert')).toHaveTextContent('camera is not ready');
  });

  it('shows normalized request errors', () => {
    vi.mocked(useCheckIn).mockReturnValue({
      checkIn: vi.fn(),
      checkOut: vi.fn(),
      isLoading: false,
      result: null,
      error: new Error('Unable to reach the attendance service'),
      lastCheckType: null,
      reset: vi.fn(),
    });

    render(<CheckInPage />);

    expect(screen.getByRole('alert')).toHaveTextContent('Unable to reach the attendance service');
  });

  it('announces PAD rejection and does not expose periodic capture globals', () => {
    const intervalSpy = vi.spyOn(window, 'setInterval');
    vi.mocked(useCheckIn).mockReturnValue({
      checkIn: vi.fn(),
      checkOut: vi.fn(),
      isLoading: false,
      result: { status: 'spoof_detected', message: 'Liveness verification failed' },
      error: null,
      lastCheckType: 'check_in',
      reset: vi.fn(),
    });

    render(<CheckInPage />);

    expect(screen.getByRole('alert')).toHaveTextContent('Liveness verification failed');
    expect(intervalSpy).not.toHaveBeenCalled();
    expect('captureFrame' in window).toBe(false);
  });
});
