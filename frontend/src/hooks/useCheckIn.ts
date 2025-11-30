import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { attendanceApi } from '@/services/attendance';
import type { CheckInResult, CheckType } from '@/types/attendance';

interface UseCheckInOptions {
  deviceId?: string;
  onSuccess?: (result: CheckInResult) => void;
  onError?: (error: Error) => void;
}

interface UseCheckInReturn {
  checkIn: (imageData: string) => Promise<CheckInResult>;
  checkOut: (imageData: string) => Promise<CheckInResult>;
  isLoading: boolean;
  result: CheckInResult | null;
  error: Error | null;
  lastCheckType: CheckType | null;
  reset: () => void;
}

export function useCheckIn(options: UseCheckInOptions = {}): UseCheckInReturn {
  const { deviceId, onSuccess, onError } = options;

  const [result, setResult] = useState<CheckInResult | null>(null);
  const [lastCheckType, setLastCheckType] = useState<CheckType | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const checkInMutation = useMutation({
    mutationFn: (imageData: string) => attendanceApi.checkIn(imageData, deviceId),
    onSuccess: (data) => {
      setResult(data);
      setLastCheckType('check_in');
      setError(null);
      onSuccess?.(data);
    },
    onError: (err: Error) => {
      setError(err);
      setResult(null);
      onError?.(err);
    },
  });

  const checkOutMutation = useMutation({
    mutationFn: (imageData: string) => attendanceApi.checkOut(imageData, deviceId),
    onSuccess: (data) => {
      setResult(data);
      setLastCheckType('check_out');
      setError(null);
      onSuccess?.(data);
    },
    onError: (err: Error) => {
      setError(err);
      setResult(null);
      onError?.(err);
    },
  });

  const checkIn = useCallback(
    async (imageData: string): Promise<CheckInResult> => {
      return checkInMutation.mutateAsync(imageData);
    },
    [checkInMutation]
  );

  const checkOut = useCallback(
    async (imageData: string): Promise<CheckInResult> => {
      return checkOutMutation.mutateAsync(imageData);
    },
    [checkOutMutation]
  );

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setLastCheckType(null);
    checkInMutation.reset();
    checkOutMutation.reset();
  }, [checkInMutation, checkOutMutation]);

  const isLoading = checkInMutation.isPending || checkOutMutation.isPending;

  return {
    checkIn,
    checkOut,
    isLoading,
    result,
    error,
    lastCheckType,
    reset,
  };
}

export default useCheckIn;
