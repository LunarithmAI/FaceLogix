import { useState } from 'react';
import type { FormEvent } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import type { User, CreateUserRequest, UpdateUserRequest } from '@/types/user';
import type { UserRole } from '@/types/roles';
import { translate as t } from '@/i18n';

interface UserFormProps {
  user?: User;
  onSubmit: (data: CreateUserRequest | UpdateUserRequest) => Promise<void>;
  onCancel: () => void;
  canAssignElevatedRoles: boolean;
  isLoading?: boolean;
}

export function UserForm({
  user,
  onSubmit,
  onCancel,
  canAssignElevatedRoles,
  isLoading = false,
}: UserFormProps) {
  const [formData, setFormData] = useState({
    email: user?.email || '',
    name: user?.name || '',
    password: '',
    role: user?.role || 'member' as UserRole,
    external_id: user?.external_id || '',
    department: user?.department || '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrors({});

    // Validation
    const newErrors: Record<string, string> = {};
    if (!formData.name) newErrors.name = 'Name is required';
    if (!user && formData.password && formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    try {
      if (user) {
        // Update - only send changed fields
        const updateData: UpdateUserRequest = {};
        if (formData.email !== (user.email || '')) updateData.email = formData.email || undefined;
        if (formData.name !== user.name) updateData.name = formData.name;
        if (formData.role !== user.role) updateData.role = formData.role;
        if (formData.external_id !== (user.external_id || '')) updateData.external_id = formData.external_id || undefined;
        if (formData.department !== (user.department || '')) updateData.department = formData.department || undefined;
        await onSubmit(updateData);
      } else {
        // Create
        await onSubmit({
          name: formData.name,
          email: formData.email || undefined,
          password: formData.password || undefined,
          role: formData.role,
          external_id: formData.external_id || undefined,
          department: formData.department || undefined,
        });
      }
    } catch (error) {
      if (error instanceof Error) {
        setErrors({ submit: error.message });
      }
    }
  };

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="space-y-4">
      {errors.submit && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {t(errors.submit)}
        </div>
      )}

      <Input
        label={t('Name')}
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        error={errors.name === undefined ? undefined : t(errors.name)}
        placeholder="John Doe"
        required
      />

      <Input
        label={t('Email')}
        type="email"
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        error={errors.email}
        placeholder="john@example.com"
      />

      {!user && (
        <Input
          label={t('Password')}
          type="password"
          value={formData.password}
          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          error={errors.password === undefined ? undefined : t(errors.password)}
          placeholder={t('Minimum 8 characters (optional)')}
        />
      )}

      <div>
        <label htmlFor="user-role" className="block text-sm font-medium text-gray-700 mb-1">{t('Role')}</label>
        <select
          id="user-role"
          value={formData.role}
          onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
          className="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="member">{t('Member')}</option>
          {canAssignElevatedRoles && <option value="manager">{t('Manager')}</option>}
          {canAssignElevatedRoles && <option value="admin">{t('Admin')}</option>}
          {canAssignElevatedRoles && <option value="super_admin">{t('Super Admin')}</option>}
        </select>
      </div>

      <Input
        label={t('External ID')}
        value={formData.external_id}
        onChange={(e) => setFormData({ ...formData, external_id: e.target.value })}
        placeholder="EMP001"
      />

      <Input
        label={t('Department')}
        value={formData.department}
        onChange={(e) => setFormData({ ...formData, department: e.target.value })}
        placeholder={t('Engineering')}
      />

      <div className="flex justify-end gap-3 pt-4">
        <Button type="button" variant="secondary" onClick={onCancel}>
          {t('Cancel')}
        </Button>
        <Button type="submit" isLoading={isLoading}>
          {user ? t('Update User') : t('Create User')}
        </Button>
      </div>
    </form>
  );
}

export default UserForm;
