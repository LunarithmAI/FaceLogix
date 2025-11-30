export type UserRole = 'admin' | 'manager' | 'member';

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
  limit?: number; // Alias for page_size
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
