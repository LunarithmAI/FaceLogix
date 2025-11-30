import api from './api';
import type {
  User,
  CreateUserRequest,
  UpdateUserRequest,
  UserListParams,
  UserListResponse,
  EnrollFaceRequest,
  EnrollFaceResponse,
} from '@/types/user';

const USERS_BASE = '/users';

export const usersApi = {
  /**
   * Get paginated list of users
   */
  async list(params: UserListParams = {}): Promise<UserListResponse> {
    const response = await api.get<UserListResponse>(USERS_BASE, { params });
    return response.data;
  },

  /**
   * Get a single user by ID
   */
  async get(userId: string): Promise<User> {
    const response = await api.get<User>(`${USERS_BASE}/${userId}`);
    return response.data;
  },

  /**
   * Create a new user
   */
  async create(data: CreateUserRequest): Promise<User> {
    const response = await api.post<User>(USERS_BASE, data);
    return response.data;
  },

  /**
   * Update an existing user
   */
  async update(userId: string, data: UpdateUserRequest): Promise<User> {
    const response = await api.patch<User>(`${USERS_BASE}/${userId}`, data);
    return response.data;
  },

  /**
   * Delete a user
   */
  async delete(userId: string): Promise<void> {
    await api.delete(`${USERS_BASE}/${userId}`);
  },

  /**
   * Reset user password (admin only)
   */
  async resetPassword(userId: string, newPassword: string): Promise<void> {
    await api.post(`${USERS_BASE}/${userId}/reset-password`, {
      new_password: newPassword,
    });
  },

  /**
   * Activate a user
   */
  async activate(userId: string): Promise<User> {
    const response = await api.post<User>(`${USERS_BASE}/${userId}/activate`);
    return response.data;
  },

  /**
   * Deactivate a user
   */
  async deactivate(userId: string): Promise<User> {
    const response = await api.post<User>(`${USERS_BASE}/${userId}/deactivate`);
    return response.data;
  },

  /**
   * Enroll face embeddings for a user
   */
  async enrollFace(data: EnrollFaceRequest): Promise<EnrollFaceResponse> {
    const response = await api.post<EnrollFaceResponse>(
      `${USERS_BASE}/${data.user_id}/enroll-face`,
      { images: data.images }
    );
    return response.data;
  },

  /**
   * Delete face embeddings for a user
   */
  async deleteFaceEmbeddings(userId: string): Promise<void> {
    await api.delete(`${USERS_BASE}/${userId}/face-embeddings`);
  },

  /**
   * Get user's face enrollment status
   */
  async getFaceStatus(userId: string): Promise<{ has_face: boolean; embeddings_count: number }> {
    const response = await api.get<{ has_face: boolean; embeddings_count: number }>(
      `${USERS_BASE}/${userId}/face-status`
    );
    return response.data;
  },
};

export default usersApi;
