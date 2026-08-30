import axios from 'axios';

interface FastApiDetail {
  code?: unknown;
  message?: unknown;
  details?: unknown;
}

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(message: string, status: number, code: string, details?: unknown) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export function normalizeApiError(error: unknown): ApiClientError {
  if (error instanceof ApiClientError) {
    return error;
  }
  if (!axios.isAxiosError(error)) {
    return new ApiClientError('An unexpected error occurred', 500, 'UNKNOWN_ERROR', error);
  }
  if (!error.response) {
    return new ApiClientError(
      'Unable to reach the server. Check your connection and try again.',
      0,
      'NETWORK_ERROR',
      error.cause
    );
  }

  const status = error.response.status;
  const payload: unknown = error.response.data;
  if (typeof payload === 'object' && payload !== null && 'detail' in payload) {
    const detail: unknown = payload.detail;
    if (typeof detail === 'string') {
      return new ApiClientError(detail, status, 'REQUEST_FAILED');
    }
    if (typeof detail === 'object' && detail !== null) {
      const typedDetail = detail as FastApiDetail;
      return new ApiClientError(
        typeof typedDetail.message === 'string' ? typedDetail.message : 'Request failed',
        status,
        typeof typedDetail.code === 'string' ? typedDetail.code : 'REQUEST_FAILED',
        typedDetail.details ?? detail
      );
    }
  }
  return new ApiClientError(error.message || 'Request failed', status, 'REQUEST_FAILED', payload);
}
