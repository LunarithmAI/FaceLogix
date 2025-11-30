import { useState, FormEvent } from 'react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import type { User, CreateUserRequest, UpdateUserRequest, UserRole } from '@/types/user';

interface UserFormProps {
  user?: User;
  onSubmit: (data: CreateUserRequest | UpdateUserRequest) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export function UserForm({ user, onSubmit, onCancel, isLoading = false }: UserFormProps) {
  const [formData, setFormData] = useState({
    email: user?.email || '',
    full_name: user?.full_name || '',
    password: '',
    role: user?.role || 'employee' as UserRole,
    employee_id: user?.employee_id || '',
    department: user?.department || '',
    phone: user?.phone || '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrors({});

    // Validation
    const newErrors: Record<string, string> = {};
    if (!formData.email) newErrors.email = 'Email is required';
    if (!formData.full_name) newErrors.full_name = 'Full name is required';
    if (!user && !formData.password) newErrors.password = 'Password is required';
    if (!user && formData.password.length < 8) {
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
        if (formData.email !== user.email) updateData.email = formData.email;
        if (formData.full_name !== user.full_name) updateData.full_name = formData.full_name;
        if (formData.role !== user.role) updateData.role = formData.role;
        if (formData.employee_id !== user.employee_id) updateData.employee_id = formData.employee_id;
        if (formData.department !== user.department) updateData.department = formData.department;
        if (formData.phone !== user.phone) updateData.phone = formData.phone;
        await onSubmit(updateData);
      } else {
        // Create
        await onSubmit({
          email: formData.email,
          full_name: formData.full_name,
          password: formData.password,
          role: formData.role,
          employee_id: formData.employee_id || undefined,
          department: formData.department || undefined,
          phone: formData.phone || undefined,
        });
      }
    } catch (error) {
      if (error instanceof Error) {
        setErrors({ submit: error.message });
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {errors.submit && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
          {errors.submit}
        </div>
      )}

      <Input
        label="Full Name"
        value={formData.full_name}
        onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
        error={errors.full_name}
        placeholder="John Doe"
        required
      />

      <Input
        label="Email"
        type="email"
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        error={errors.email}
        placeholder="john@example.com"
        required
      />

      {!user && (
        <Input
          label="Password"
          type="password"
          value={formData.password}
          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
          error={errors.password}
          placeholder="Minimum 8 characters"
          required
        />
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
        <select
          value={formData.role}
          onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
          className="block w-full px-4 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        >
          <option value="employee">Employee</option>
          <option value="manager">Manager</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      <Input
        label="Employee ID"
        value={formData.employee_id}
        onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
        placeholder="EMP001"
      />

      <Input
        label="Department"
        value={formData.department}
        onChange={(e) => setFormData({ ...formData, department: e.target.value })}
        placeholder="Engineering"
      />

      <Input
        label="Phone"
        type="tel"
        value={formData.phone}
        onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
        placeholder="+1 234 567 8900"
      />

      <div className="flex justify-end gap-3 pt-4">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" isLoading={isLoading}>
          {user ? 'Update User' : 'Create User'}
        </Button>
      </div>
    </form>
  );
}

export default UserForm;
