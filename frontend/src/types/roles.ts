export type UserRole = 'super_admin' | 'admin' | 'manager' | 'member';

export const OPERATOR_ROLES: readonly UserRole[] = ['super_admin', 'admin', 'manager'];
export const ADMIN_ROLES: readonly UserRole[] = ['super_admin', 'admin'];
