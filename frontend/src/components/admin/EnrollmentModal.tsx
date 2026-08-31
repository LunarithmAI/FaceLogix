import { useRef, useState } from 'react';
import { CameraIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import { CameraView } from '@/components/camera/CameraView';
import type { CameraViewHandle } from '@/components/camera/CameraView';
import { Button } from '@/components/ui/Button';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { usersApi } from '@/services/users';
import type { User } from '@/types/user';
import { translate as t } from '@/i18n';

interface EnrollmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User | null;
  onSuccess?: () => void;
}

const MIN_CAPTURES = 3;
const MAX_CAPTURES = 5;

export function EnrollmentModal({
  isOpen,
  onClose,
  user,
  onSuccess,
}: EnrollmentModalProps) {
  const [captures, setCaptures] = useState<string[]>([]);
  const [isEnrolling, setIsEnrolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const cameraRef = useRef<CameraViewHandle>(null);

  const handleCapture = () => {
    const imageData = cameraRef.current?.captureFrame() ?? null;
    if (imageData === null) {
      setError('The camera is not ready. Wait for the live preview, then try again.');
      return;
    }
    setError(null);
    setCaptures((current) => [...current, imageData].slice(0, MAX_CAPTURES));
  };

  const handleEnroll = async () => {
    if (user === null || captures.length < MIN_CAPTURES) {
      return;
    }
    setIsEnrolling(true);
    setError(null);
    try {
      await usersApi.enrollFace({ user_id: user.id, images: captures });
      setSuccess(true);
      onSuccess?.();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Face enrollment failed.');
    } finally {
      setIsEnrolling(false);
    }
  };

  const handleClose = () => {
    setCaptures([]);
    setError(null);
    setSuccess(false);
    onClose();
  };

  if (user === null) {
    return null;
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={t('Face Enrollment')}
      description={t('Capture {{min}}–{{max}} clear photos of {{name}}.', { min: MIN_CAPTURES, max: MAX_CAPTURES, name: user.name })}
      size="lg"
    >
      {success ? (
        <div className="py-8 text-center" role="status" aria-live="polite">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
            <CheckCircleIcon className="h-8 w-8 text-green-600" aria-hidden="true" />
          </div>
          <h3 className="mb-2 text-lg font-medium text-gray-900">{t('Face Enrolled Successfully')}</h3>
          <p className="text-gray-600">
            {t("{{name}}'s face was enrolled with {{count}} images.", { name: user.name, count: captures.length })}
          </p>
          <Button type="button" onClick={handleClose} className="mt-6">
            {t('Close')}
          </Button>
        </div>
      ) : (
        <>
          {error !== null && (
            <div
              className="mb-4 flex items-center rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
              role="alert"
            >
              <XCircleIcon className="mr-2 h-5 w-5 shrink-0" aria-hidden="true" />
              {t(error)}
            </div>
          )}

          <div className="mb-4">
            <CameraView
              ref={cameraRef}
              showGuide
              className="mx-auto aspect-[4/3] w-full max-w-md"
            />
          </div>

          <div className="mb-4 flex justify-center">
            <Button
              type="button"
              onClick={handleCapture}
              disabled={captures.length >= MAX_CAPTURES}
              leftIcon={<CameraIcon className="h-5 w-5" aria-hidden="true" />}
              size="lg"
            >
              {t('Capture ({{count}}/{{max}})', { count: captures.length, max: MAX_CAPTURES })}
            </Button>
          </div>

          {captures.length > 0 && (
            <div className="mb-4">
              <p className="mb-2 text-sm font-medium text-gray-700">{t('Captured Images')}</p>
              <div className="flex flex-wrap gap-3">
                {captures.map((capture, index) => (
                  <div key={capture} className="relative">
                    <img
                      src={capture}
                      alt={t('Capture {{number}}', { number: index + 1 })}
                      className="h-20 w-20 rounded-lg border border-gray-200 object-cover"
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setCaptures((current) => current.filter((_, itemIndex) => itemIndex !== index))
                      }
                      className="absolute -right-3 -top-3 flex min-h-11 min-w-11 items-center justify-center rounded-full bg-red-600 text-white hover:bg-red-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
                      aria-label={t('Remove image {{number}}', { number: index + 1 })}
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <ModalFooter>
            <Button type="button" variant="secondary" onClick={handleClose}>
              {t('Cancel')}
            </Button>
            <Button
              type="button"
              onClick={() => void handleEnroll()}
              disabled={captures.length < MIN_CAPTURES}
              isLoading={isEnrolling}
              loadingText={t('Enrolling')}
            >
              {t('Enroll Face')}
            </Button>
          </ModalFooter>
        </>
      )}
    </Modal>
  );
}

export default EnrollmentModal;
