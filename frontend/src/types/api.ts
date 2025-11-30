export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ApiError {
  status: number;
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface ApiValidationError extends ApiError {
  validation_errors: ValidationError[];
}

export interface RequestConfig {
  skipAuth?: boolean;
  timeout?: number;
}
