import { useCallback, useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

export type CameraFacing = 'user' | 'environment';

interface UseCameraOptions {
  initialFacing?: CameraFacing;
  width?: number;
  height?: number;
}

interface UseCameraReturn {
  videoRef: RefObject<HTMLVideoElement | null>;
  isLoading: boolean;
  isReady: boolean;
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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const isMountedRef = useRef(true);
  const [isLoading, setIsLoading] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facing, setFacing] = useState<CameraFacing>(initialFacing);
  const [hasMultipleCameras, setHasMultipleCameras] = useState(false);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current !== null) {
      videoRef.current.srcObject = null;
    }
    if (isMountedRef.current) {
      setIsReady(false);
    }
  }, []);

  const openCamera = useCallback(
    async (targetFacing: CameraFacing) => {
      if (!navigator.mediaDevices?.getUserMedia) {
        setError('Camera access requires a secure connection and a supported browser.');
        return;
      }
      setIsLoading(true);
      setError(null);
      stopCamera();

      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: targetFacing,
            width: { ideal: width },
            height: { ideal: height },
          },
          audio: false,
        });
        if (!isMountedRef.current) {
          mediaStream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = mediaStream;
        const video = videoRef.current;
        if (video === null) {
          stopCamera();
          return;
        }
        video.srcObject = mediaStream;
        if (video.readyState < HTMLMediaElement.HAVE_METADATA) {
          await new Promise<void>((resolve, reject) => {
            const handleLoadedMetadata = () => {
              video.removeEventListener('loadedmetadata', handleLoadedMetadata);
              video.removeEventListener('error', handleVideoError);
              resolve();
            };
            const handleVideoError = () => {
              video.removeEventListener('loadedmetadata', handleLoadedMetadata);
              video.removeEventListener('error', handleVideoError);
              reject(new Error('Camera video could not be loaded.'));
            };
            video.addEventListener('loadedmetadata', handleLoadedMetadata);
            video.addEventListener('error', handleVideoError);
          });
        }
        await video.play();
        if (isMountedRef.current) {
          setIsReady(true);
          const devices = await navigator.mediaDevices.enumerateDevices();
          setHasMultipleCameras(
            devices.filter((device) => device.kind === 'videoinput').length > 1
          );
        }
      } catch (caughtError) {
        if (!isMountedRef.current) {
          return;
        }
        const errorName = caughtError instanceof DOMException ? caughtError.name : '';
        if (errorName === 'NotAllowedError' || errorName === 'SecurityError') {
          setError('Camera permission was denied. Allow camera access and try again.');
        } else if (errorName === 'NotFoundError' || errorName === 'OverconstrainedError') {
          setError('No usable camera was found on this device.');
        } else if (caughtError instanceof Error && caughtError.name === 'AbortError') {
          return;
        } else {
          setError(caughtError instanceof Error ? caughtError.message : 'Camera access failed.');
        }
      } finally {
        if (isMountedRef.current) {
          setIsLoading(false);
        }
      }
    },
    [height, stopCamera, width]
  );

  const startCamera = useCallback(() => openCamera(facing), [facing, openCamera]);

  const switchCamera = useCallback(async () => {
    const nextFacing = facing === 'user' ? 'environment' : 'user';
    setFacing(nextFacing);
    await openCamera(nextFacing);
  }, [facing, openCamera]);

  const captureFrame = useCallback((): string | null => {
    const video = videoRef.current;
    if (
      video === null ||
      streamRef.current === null ||
      !isReady ||
      video.videoWidth === 0 ||
      video.videoHeight === 0
    ) {
      return null;
    }

    const scale = Math.min(1, width / video.videoWidth, height / video.videoHeight);
    const captureWidth = Math.max(1, Math.floor(video.videoWidth * scale));
    const captureHeight = Math.max(1, Math.floor(video.videoHeight * scale));
    const canvas = canvasRef.current ?? document.createElement('canvas');
    canvasRef.current = canvas;
    canvas.width = captureWidth;
    canvas.height = captureHeight;
    const context = canvas.getContext('2d');
    if (context === null) {
      return null;
    }
    if (facing === 'user') {
      context.translate(captureWidth, 0);
      context.scale(-1, 1);
    }
    context.drawImage(video, 0, 0, captureWidth, captureHeight);
    return canvas.toDataURL('image/jpeg', 0.9);
  }, [facing, height, isReady, width]);

  useEffect(
    () => () => {
      stopCamera();
    },
    [stopCamera]
  );

  return {
    videoRef,
    isLoading,
    isReady,
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
