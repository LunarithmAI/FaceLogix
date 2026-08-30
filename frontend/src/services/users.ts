import api from './api';
import type {
  CreateUserRequest,
  EnrollFaceRequest,
  EnrollFaceResponse,
  UpdateUserRequest,
  User,
  UserImportPreview,
  UserImportResolution,
  UserImportResult,
  UserListParams,
  UserListResponse,
} from '@/types/user';

const USERS_BASE = '/users';

export const usersApi = {
  async list(params: UserListParams = {}, signal?: AbortSignal): Promise<UserListResponse> {
    const response = await api.get<UserListResponse>(USERS_BASE, { params, signal });
    return response.data;
  },

  async create(data: CreateUserRequest): Promise<User> {
    const response = await api.post<User>(USERS_BASE, data);
    return response.data;
  },

  async update(userId: string, data: UpdateUserRequest): Promise<User> {
    const response = await api.patch<User>(`${USERS_BASE}/${userId}`, data);
    return response.data;
  },

  async delete(userId: string): Promise<void> {
    await api.delete(`${USERS_BASE}/${userId}`);
  },

  async enrollFace(data: EnrollFaceRequest): Promise<EnrollFaceResponse> {
    const response = await api.post<EnrollFaceResponse>(
      `${USERS_BASE}/${data.user_id}/enroll-face`,
      { images: data.images }
    );
    return response.data;
  },

  async previewImport(packageFile: File): Promise<UserImportPreview> {
    const formData = new FormData();
    formData.append('package', packageFile);
    const response = await api.post<UserImportPreview>(`${USERS_BASE}/import/preview`, formData);
    return response.data;
  },

  async importPackage(
    packageFile: File,
    packageSha256: string,
    resolutions: UserImportResolution[]
  ): Promise<UserImportResult> {
    const formData = new FormData();
    formData.append('package', packageFile);
    formData.append(
      'options',
      JSON.stringify({ package_sha256: packageSha256, resolutions })
    );
    const response = await api.post<UserImportResult>(`${USERS_BASE}/import`, formData);
    return response.data;
  },
};

export default usersApi;
