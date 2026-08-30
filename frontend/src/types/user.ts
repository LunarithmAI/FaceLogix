import type { UserRole } from '@/types/roles';


export interface User {
  id: string;
  email: string | null;
  name: string;
  role: UserRole;
  org_id: string;
  is_active: boolean;
  enrolled_at: string | null;
  external_id?: string;
  department?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateUserRequest {
  email?: string;
  name: string;
  password?: string;
  role: UserRole;
  external_id?: string;
  department?: string;
}

export interface UpdateUserRequest {
  email?: string;
  name?: string;
  role?: UserRole;
  is_active?: boolean;
  external_id?: string;
  department?: string;
}

export interface UserListParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  department?: string;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface EnrollFaceRequest {
  user_id: string;
  images: string[]; // Base64 encoded images
}

export interface EnrollFaceResponse {
  user_id: string;
  embeddings_count: number;
  enrolled_at: string;
}


export type UserImportConflictAction = 'skip' | 'replace';

export interface UserImportError {
  row: number | null;
  code: string;
  message: string;
  field: string | null;
}

export interface UserImportConflict {
  row: number;
  external_id: string;
  email: string | null;
  name: string;
  existing_user_id: string;
  existing_name: string;
  allowed_actions: UserImportConflictAction[];
}

export interface UserImportPreview {
  package_sha256: string;
  total_rows: number;
  ready_count: number;
  conflict_count: number;
  error_count: number;
  conflicts: UserImportConflict[];
  errors: UserImportError[];
}

export interface UserImportResolution {
  row: number;
  action: UserImportConflictAction;
}

export interface UserImportResult {
  total_rows: number;
  created_count: number;
  replaced_count: number;
  skipped_count: number;
  embeddings_count: number;
}
