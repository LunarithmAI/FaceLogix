import { useState, useCallback } from 'react';
import { CameraIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import { Modal, ModalFooter } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { CameraView } from '@/components/camera/CameraView';
import type { User } from '@/types/user';
import { usersApi } from '@/services/users';

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

  const handleCapture = useCallback(() => {
    const captureFrame = (window as Window & { captureFrame?: () => string }).captureFrame;
    if (!captureFrame) return;

    const imageData = captureFrame();
    if (!imageData) return;

    setCaptures((prev) => [...prev, imageData].slice(0, MAX_CAPTURES));
  }, []);

  const handleRemoveCapture = (index: number) => {
    setCaptures((prev) => prev.filter((_, i) => i !== index));
  };

  const handleEnroll = async () => {
    if (!user || captures.length < MIN_CAPTURES) return;

    setIsEnrolling(true);
    setError(null);

    try {
      await usersApi.enrollFace({
        user_id: user.id,
        images: captures,
      });
      setSuccess(true);
      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to enroll face');
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

  if (!user) return null;

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Face Enrollment" size="lg">
      {success ? (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircleIcon className="w-8 h-8 text-green-600" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Face Enrolled Successfully
          </h3>
          <p className="text-gray-500">
            {user.full_name}'s face has been enrolled with {captures.length} images.
          </p>
          <Button onClick={handleClose} className="mt-6">
            Close
          </Button>
        </div>
      ) : (
        <>
          <div className="mb-4">
            <p className="text-sm text-gray-600">
              Enrolling face for <strong>{user.full_name}</strong>
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Capture {MIN_CAPTURES}-{MAX_CAPTURES} photos from different angles for best results.
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center text-red-600 text-sm">
              <XCircleIcon className="w-5 h-5 mr-2" />
              {error}
            </div>
          )}

          {/* Camera view */}
          <div className="mb-4">
            <CameraView
              onCapture={() => {}}
              showGuide={true}
              className="aspect-[4/3] w-full max-w-md mx-auto"
            />
          </div>

          {/* Capture button */}
          <div className="flex justify-center mb-4">
            <Button
              onClick={handleCapture}
              disabled={captures.length >= MAX_CAPTURES}
              leftIcon={<CameraIcon className="w-5 h-5" />}
              size="lg"
            >
              Capture ({captures.length}/{MAX_CAPTURES})
            </Button>
          </div>

          {/* Captured images */}
          {captures.length > 0 && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-2">
                Captured Images
              </p>
              <div className="flex gap-2 flex-wrap">
                {captures.map((capture, index) => (
                  <div key={index} className="relative">
                    <img
                      src={capture}
                      alt={`Capture ${index + 1}`}
                      className="w-20 h-20 object-cover rounded-lg border border-gray-200"
                    />
                    <button
                      onClick={() => handleRemoveCapture(index)}
                      className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-600"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <ModalFooter>
            <Button variant="secondary" onClick={handleClose}>
              Cancel
            </Button>
            <Button
              onClick={handleEnroll}
              disabled={captures.length < MIN_CAPTURES}
              isLoading={isEnrolling}
            >
              Enroll Face
            </Button>
          </ModalFooter>
        </>
      )}
    </Modal>
  );
}

export default EnrollmentModal;
