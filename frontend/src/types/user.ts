export type UserRole = 'admin' | 'manager' | 'employee';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  organization_id: string;
  organization_name: string;
  is_active: boolean;
  has_face_enrolled: boolean;
  employee_id?: string;
  department?: string;
  phone?: string;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
  last_check_in?: string;
}

export interface CreateUserRequest {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
  employee_id?: string;
  department?: string;
  phone?: string;
}

export interface UpdateUserRequest {
  email?: string;
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
  employee_id?: string;
  department?: string;
  phone?: string;
}

export interface UserListParams {
  page?: number;
  limit?: number;
  search?: string;
  role?: UserRole;
  is_active?: boolean;
  has_face_enrolled?: boolean;
  department?: string;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface EnrollFaceRequest {
  user_id: string;
  images: string[]; // Base64 encoded images
}

export interface EnrollFaceResponse {
  success: boolean;
  message: string;
  embeddings_count: number;
}
