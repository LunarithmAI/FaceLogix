import { useEffect } from 'react';
import { ArrowPathRoundedSquareIcon } from '@heroicons/react/24/outline';
import { useCamera } from '@/hooks/useCamera';

interface CameraViewProps {
  onCapture?: (imageData: string) => void;
  showGuide?: boolean;
  autoStart?: boolean;
  className?: string;
}

export function CameraView({
  onCapture,
  showGuide = true,
  autoStart = true,
  className = '',
}: CameraViewProps) {
  const {
    videoRef,
    stream,
    isLoading,
    error,
    facing,
    hasMultipleCameras,
    startCamera,
    switchCamera,
  } = useCamera();

  useEffect(() => {
    if (autoStart) {
      startCamera();
    }
  }, [autoStart, startCamera]);

  // Expose capture function to parent via callback
  useEffect(() => {
    if (stream && videoRef.current) {
      const video = videoRef.current;
      
      const captureFrame = (): string | null => {
        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        const ctx = canvas.getContext('2d');
        if (!ctx) return null;
        
        if (facing === 'user') {
          ctx.translate(canvas.width, 0);
          ctx.scale(-1, 1);
        }
        
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL('image/jpeg', 0.9);
        
        // Call onCapture callback if provided
        if (onCapture) {
          onCapture(imageData);
        }
        
        // Also return the image data for direct access
        return imageData;
      };

      // Attach to window for parent access
      (window as unknown as { captureFrame?: () => string | null }).captureFrame = captureFrame;
      
      return () => {
        delete (window as unknown as { captureFrame?: () => string | null }).captureFrame;
      };
    }
  }, [onCapture, stream, facing, videoRef]);

  if (error) {
    return (
      <div className={`relative bg-gray-900 rounded-xl overflow-hidden ${className}`}>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-white p-6">
          <div className="text-center">
            <p className="text-red-400 mb-4">{error}</p>
            <button
              onClick={startCamera}
              className="btn-primary"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative bg-gray-900 rounded-xl overflow-hidden ${className}`}>
      {/* Video element */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={`w-full h-full object-cover ${facing === 'user' ? 'scale-x-[-1]' : ''}`}
      />

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-white border-t-transparent" />
        </div>
      )}

      {/* Face guide overlay */}
      {showGuide && stream && !isLoading && (
        <div className="face-guide">
          <div className="face-guide-oval" />
        </div>
      )}

      {/* Instruction text */}
      {stream && !isLoading && (
        <div className="absolute bottom-4 left-0 right-0 text-center">
          <p className="text-white text-sm bg-black/50 inline-block px-4 py-2 rounded-full">
            Position your face within the oval
          </p>
        </div>
      )}

      {/* Camera switch button */}
      {hasMultipleCameras && stream && (
        <button
          onClick={switchCamera}
          disabled={isLoading}
          className="absolute top-4 right-4 p-3 bg-black/50 rounded-full text-white hover:bg-black/70 transition-colors disabled:opacity-50"
          aria-label="Switch camera"
        >
          <ArrowPathRoundedSquareIcon className="w-6 h-6" />
        </button>
      )}
    </div>
  );
}

export default CameraView;
