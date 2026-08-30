import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { UserForm } from '@/components/admin/UserForm';
import { ADMIN_ROLES, OPERATOR_ROLES } from '@/types/roles';

describe('role matrix', () => {
  it('allows every operator role through admin routes but reserves administration', () => {
    expect(OPERATOR_ROLES).toEqual(['super_admin', 'admin', 'manager']);
    expect(ADMIN_ROLES).toEqual(['super_admin', 'admin']);
  });

  it('prevents managers from selecting elevated roles', () => {
    render(
      <UserForm
        canAssignElevatedRoles={false}
        onSubmit={vi.fn().mockResolvedValue(undefined)}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByRole('combobox', { name: 'Role' })).toHaveValue('member');
    expect(screen.getByRole('option', { name: 'Member' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Manager' })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Admin' })).not.toBeInTheDocument();
  });

  it('gives administrators the full organization role form', () => {
    render(
      <UserForm
        canAssignElevatedRoles
        onSubmit={vi.fn().mockResolvedValue(undefined)}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByRole('option', { name: 'Super Admin' })).toBeInTheDocument();
  });
});
