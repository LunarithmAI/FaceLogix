import { useState, useCallback, useRef, useEffect } from 'react';

export type CameraFacing = 'user' | 'environment';

interface UseCameraOptions {
  initialFacing?: CameraFacing;
  width?: number;
  height?: number;
}

interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement>;
  stream: MediaStream | null;
  isLoading: boolean;
  error: string | null;
  facing: CameraFacing;
  hasMultipleCameras: boolean;
  startCamera: () => Promise<void>;
  stopCamera: () => void;
  captureFrame: () => string | null;
  switchCamera: () => Promise<void>;
}

export function useCamera(options: UseCameraOptions = {}): UseCameraReturn {
  const { initialFacing = 'user', width = 640, height = 480 } = options;

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facing, setFacing] = useState<CameraFacing>(initialFacing);
  const [hasMultipleCameras, setHasMultipleCameras] = useState(false);

  // Check for multiple cameras on mount
  useEffect(() => {
    const checkCameras = async () => {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');
        setHasMultipleCameras(videoDevices.length > 1);
      } catch {
        setHasMultipleCameras(false);
      }
    };
    checkCameras();
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
      setStream(null);
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const startCamera = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    // Stop any existing stream
    stopCamera();

    try {
      const constraints: MediaStreamConstraints = {
        video: {
          facingMode: facing,
          width: { ideal: width },
          height: { ideal: height },
        },
        audio: false,
      };

      const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = mediaStream;
      setStream(mediaStream);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        await videoRef.current.play();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to access camera';
      if (message.includes('NotAllowedError') || message.includes('Permission')) {
        setError('Camera permission denied. Please allow camera access.');
      } else if (message.includes('NotFoundError')) {
        setError('No camera found on this device.');
      } else {
        setError(message);
      }
    } finally {
      setIsLoading(false);
    }
  }, [facing, width, height, stopCamera]);

  const captureFrame = useCallback((): string | null => {
    if (!videoRef.current || !stream) {
      return null;
    }

    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return null;
    }

    // Mirror the image for front camera
    if (facing === 'user') {
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Return base64 encoded JPEG
    return canvas.toDataURL('image/jpeg', 0.9);
  }, [stream, facing]);

  const switchCamera = useCallback(async () => {
    const newFacing = facing === 'user' ? 'environment' : 'user';
    setFacing(newFacing);
    
    // Restart camera with new facing mode
    if (stream) {
      setIsLoading(true);
      stopCamera();
      
      try {
        const constraints: MediaStreamConstraints = {
          video: {
            facingMode: newFacing,
            width: { ideal: width },
            height: { ideal: height },
          },
          audio: false,
        };

        const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
        streamRef.current = mediaStream;
        setStream(mediaStream);

        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          await videoRef.current.play();
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to switch camera';
        setError(message);
      } finally {
        setIsLoading(false);
      }
    }
  }, [facing, stream, width, height, stopCamera]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, [stopCamera]);

  return {
    videoRef,
    stream,
    isLoading,
    error,
    facing,
    hasMultipleCameras,
    startCamera,
    stopCamera,
    captureFrame,
    switchCamera,
  };
}

export default useCamera;
