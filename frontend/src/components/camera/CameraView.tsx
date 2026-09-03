import { forwardRef, useEffect, useImperativeHandle } from 'react';
import { ArrowPathRoundedSquareIcon } from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/Button';
import { Loading } from '@/components/ui/Loading';
import { useCamera } from '@/hooks/useCamera';
import { translate as t } from '@/i18n';

export interface CameraViewHandle {
  captureFrame: () => string | null;
}

interface CameraViewProps {
  showGuide?: boolean;
  autoStart?: boolean;
  className?: string;
  initialFacing?: 'user' | 'environment';
}

export const CameraView = forwardRef<CameraViewHandle, CameraViewProps>(
  ({ showGuide = true, autoStart = true, className = '', initialFacing = 'user' }, ref) => {
    const {
      videoRef,
      isLoading,
      isReady,
      error,
      facing,
      hasMultipleCameras,
      startCamera,
      captureFrame,
      switchCamera,
    } = useCamera({ initialFacing });

    useImperativeHandle(ref, () => ({ captureFrame }), [captureFrame]);

    useEffect(() => {
      if (autoStart) {
        void startCamera();
      }
    }, [autoStart, startCamera]);

    if (error !== null) {
      return (
        <div
          className={`flex items-center justify-center overflow-hidden rounded-xl bg-gray-900 p-6 ${className}`}
          role="alert"
        >
          <div className="text-center">
            <p className="mb-4 text-red-300">{t(error)}</p>
            <Button type="button" onClick={() => void startCamera()}>
              {t('Try Again')}
            </Button>
          </div>
        </div>
      );
    }

    return (
      <div className={`relative overflow-hidden rounded-xl bg-gray-900 ${className}`}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          aria-label={t('Live camera preview')}
          className={`h-full w-full object-cover ${facing === 'user' ? '-scale-x-100' : ''}`}
        />

        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/60">
            <Loading size="lg" text={t('Starting camera')} color="gray" />
          </div>
        )}

        {showGuide && isReady && !isLoading && (
          <div className="face-guide" aria-hidden="true">
            <div className="face-guide-oval" />
          </div>
        )}

        {isReady && !isLoading && (
          <div className="absolute inset-x-0 bottom-4 text-center" role="status">
            <p className="inline-block rounded-full bg-black/60 px-4 py-2 text-sm text-white">
              {t('Camera ready — position your face within the oval')}
            </p>
          </div>
        )}

        {hasMultipleCameras && isReady && (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => void switchCamera()}
            disabled={isLoading}
            className="absolute right-3 top-3 min-w-11 rounded-full bg-black/60 px-2 text-white hover:bg-black/80"
            aria-label={t('Switch camera')}
          >
            <ArrowPathRoundedSquareIcon className="h-6 w-6" aria-hidden="true" />
          </Button>
        )}
      </div>
    );
  }
);

CameraView.displayName = 'CameraView';

export default CameraView;
