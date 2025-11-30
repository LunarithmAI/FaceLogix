import { useState, useRef, useCallback } from 'react';
import { 
  ArrowRightOnRectangleIcon, 
  ArrowLeftOnRectangleIcon,
  ArrowPathIcon 
} from '@heroicons/react/24/solid';
import { CameraView } from '@/components/camera/CameraView';
import { StatusMessage } from '@/components/attendance/StatusMessage';
import { useCheckIn } from '@/hooks/useCheckIn';
import { useAuthStore } from '@/stores/authStore';
import type { CheckType } from '@/types/attendance';

export function CheckInPage() {
  const { user } = useAuthStore();
  const [mode, setMode] = useState<CheckType>('check_in');
  const captureRef = useRef<(() => string | null) | null>(null);
  
  const { checkIn, checkOut, isLoading, result, reset } = useCheckIn({
    onSuccess: () => {
      // Auto-reset after 5 seconds
      setTimeout(() => {
        reset();
      }, 5000);
    },
  });

  const handleCapture = useCallback((imageData: string) => {
    captureRef.current = () => imageData;
  }, []);

  const handleAction = async () => {
    // Access the capture function from window (set by CameraView)
    const captureFrame = (window as unknown as { captureFrame?: () => string }).captureFrame;
    if (!captureFrame) return;

    const imageData = captureFrame();
    if (!imageData) return;

    if (mode === 'check_in') {
      await checkIn(imageData);
    } else {
      await checkOut(imageData);
    }
  };

  const toggleMode = () => {
    setMode(mode === 'check_in' ? 'check_out' : 'check_in');
    reset();
  };

  return (
    <div className="min-h-screen bg-gray-50 safe-top safe-bottom">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-lg mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-gray-900">FaceLogix</h1>
              {user && (
                <p className="text-sm text-gray-500">{user.name}</p>
              )}
            </div>
            <button
              onClick={toggleMode}
              className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              {mode === 'check_in' ? (
                <>
                  <ArrowLeftOnRectangleIcon className="w-4 h-4" />
                  Switch to Check Out
                </>
              ) : (
                <>
                  <ArrowRightOnRectangleIcon className="w-4 h-4" />
                  Switch to Check In
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-lg mx-auto px-4 py-6">
        {/* Mode Indicator */}
        <div className="mb-4 text-center">
          <span
            className={`
              inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium
              ${mode === 'check_in' 
                ? 'bg-green-100 text-green-800' 
                : 'bg-blue-100 text-blue-800'
              }
            `}
          >
            {mode === 'check_in' ? (
              <>
                <ArrowRightOnRectangleIcon className="w-5 h-5" />
                Check In Mode
              </>
            ) : (
              <>
                <ArrowLeftOnRectangleIcon className="w-5 h-5" />
                Check Out Mode
              </>
            )}
          </span>
        </div>

        {/* Camera View */}
        <div className="mb-6">
          <CameraView
            onCapture={handleCapture}
            showGuide={!result}
            className="aspect-[3/4] w-full max-w-sm mx-auto"
          />
        </div>

        {/* Result Display */}
        {result && (
          <div className="mb-6">
            <StatusMessage result={result} />
            <button
              onClick={reset}
              className="mt-4 w-full btn-secondary flex items-center justify-center gap-2"
            >
              <ArrowPathIcon className="w-5 h-5" />
              Try Again
            </button>
          </div>
        )}

        {/* Action Button */}
        {!result && (
          <button
            onClick={handleAction}
            disabled={isLoading}
            className={`
              w-full btn-xl rounded-xl font-semibold
              ${mode === 'check_in' ? 'btn-success' : 'btn-primary'}
            `}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-3">
                <svg
                  className="animate-spin h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Processing...
              </span>
            ) : mode === 'check_in' ? (
              <span className="flex items-center justify-center gap-3">
                <ArrowRightOnRectangleIcon className="w-6 h-6" />
                Check In
              </span>
            ) : (
              <span className="flex items-center justify-center gap-3">
                <ArrowLeftOnRectangleIcon className="w-6 h-6" />
                Check Out
              </span>
            )}
          </button>
        )}

        {/* Instructions */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>Position your face within the oval guide</p>
          <p className="mt-1">Ensure good lighting for best results</p>
        </div>
      </main>
    </div>
  );
}

export default CheckInPage;
