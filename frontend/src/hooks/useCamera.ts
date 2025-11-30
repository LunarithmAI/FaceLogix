import { useState, useCallback, useRef, useEffect } from 'react';

export type CameraFacing = 'user' | 'environment';

interface UseCameraOptions {
  initialFacing?: CameraFacing;
  width?: number;
  height?: number;
}

interface UseCameraReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  stream: MediaStream | null;
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
  const streamRef = useRef<MediaStream | null>(null);
  const isMountedRef = useRef(true);
  
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [facing, setFacing] = useState<CameraFacing>(initialFacing);
  const [hasMultipleCameras, setHasMultipleCameras] = useState(false);

  // Track mounted state
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  // Check for multiple cameras on mount
  useEffect(() => {
    const checkCameras = async () => {
      try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');
        if (isMountedRef.current) {
          setHasMultipleCameras(videoDevices.length > 1);
        }
      } catch {
        if (isMountedRef.current) {
          setHasMultipleCameras(false);
        }
      }
    };
    checkCameras();
  }, []);

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
      if (isMountedRef.current) {
        setStream(null);
        setIsReady(false);
      }
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }, []);

  const startCamera = useCallback(async () => {
    if (!isMountedRef.current) return;
    
    // Check if mediaDevices is available (requires HTTPS on non-localhost)
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('Camera access requires HTTPS. Please use a secure connection.');
      return;
    }
    
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
      
      // Check if component is still mounted after async operation
      if (!isMountedRef.current) {
        mediaStream.getTracks().forEach(track => track.stop());
        return;
      }
      
      streamRef.current = mediaStream;
      setStream(mediaStream);

      if (videoRef.current) {
        const video = videoRef.current;
        video.srcObject = mediaStream;
        
        // Wait for video metadata to load (important for iOS)
        await new Promise<void>((resolve, reject) => {
          const onLoadedMetadata = () => {
            video.removeEventListener('loadedmetadata', onLoadedMetadata);
            video.removeEventListener('error', onError);
            resolve();
          };
          const onError = () => {
            video.removeEventListener('loadedmetadata', onLoadedMetadata);
            video.removeEventListener('error', onError);
            reject(new Error('Video failed to load'));
          };
          
          // If already loaded, resolve immediately
          if (video.readyState >= 1) {
            resolve();
          } else {
            video.addEventListener('loadedmetadata', onLoadedMetadata);
            video.addEventListener('error', onError);
          }
        });
        
        try {
          await video.play();
          if (isMountedRef.current) {
            setIsReady(true);
          }
        } catch (playError) {
          // Ignore AbortError - happens when component unmounts during play
          if (playError instanceof Error && playError.name === 'AbortError') {
            console.log('Video play aborted - component likely unmounted');
            return;
          }
          throw playError;
        }
      }
    } catch (err) {
      // Don't set error state if unmounted
      if (!isMountedRef.current) return;
      
      const message = err instanceof Error ? err.message : 'Failed to access camera';
      if (message.includes('NotAllowedError') || message.includes('Permission')) {
        setError('Camera permission denied. Please allow camera access.');
      } else if (message.includes('NotFoundError')) {
        setError('No camera found on this device.');
      } else {
        setError(message);
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
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
      if (!isMountedRef.current) return;
      
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
        
        // Check if component is still mounted
        if (!isMountedRef.current) {
          mediaStream.getTracks().forEach(track => track.stop());
          return;
        }
        
        streamRef.current = mediaStream;
        setStream(mediaStream);

        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
          try {
            await videoRef.current.play();
          } catch (playError) {
            if (playError instanceof Error && playError.name === 'AbortError') {
              return;
            }
            throw playError;
          }
        }
      } catch (err) {
        if (!isMountedRef.current) return;
        const message = err instanceof Error ? err.message : 'Failed to switch camera';
        setError(message);
      } finally {
        if (isMountedRef.current) {
          setIsLoading(false);
        }
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
