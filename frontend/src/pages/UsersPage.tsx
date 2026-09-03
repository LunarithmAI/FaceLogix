import { useState } from 'react';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { ArrowUpTrayIcon, MagnifyingGlassIcon, PlusIcon } from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal, ConfirmModal } from '@/components/ui/Modal';
import { UserTable } from '@/components/admin/UserTable';
import { UserForm } from '@/components/admin/UserForm';
import { EnrollmentModal } from '@/components/admin/EnrollmentModal';
import { UserImportModal } from '@/components/admin/UserImportModal';
import { UserAssignmentsPanel } from '@/components/admin/UserAssignmentsPanel';
import { Loading } from '@/components/ui/Loading';
import { usersApi } from '@/services/users';
import { shiftsApi } from '@/services/shifts';
import { unitsApi } from '@/services/units';
import type { User, CreateUserRequest, UpdateUserRequest } from '@/types/user';
import { queryClient, queryKeys } from '@/lib/queryClient';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useAuthStore } from '@/stores/authStore';
import { ADMIN_ROLES } from '@/types/roles';
import { translate as t } from '@/i18n';

export function UsersPage() {
  const session = useAuthStore((state) => state.session);
  const currentUser = session?.kind === 'user' ? session.user : null;
  const canManageElevatedUsers =
    currentUser !== null && ADMIN_ROLES.includes(currentUser.role);
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search);
  const [page, setPage] = useState(1);

  // Modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isImportOpen, setIsImportOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isEnrollOpen, setIsEnrollOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const usersQuery = useQuery({
    queryKey: queryKeys.users({
      page,
      page_size: 10,
      search: debouncedSearch || undefined,
    }),
    queryFn: ({ signal }) =>
      usersApi.list(
        {
          page,
          page_size: 10,
          search: debouncedSearch || undefined,
        },
        signal
      ),
    placeholderData: keepPreviousData,
  });
  const unitsQuery = useQuery({
    queryKey: ['units', 'active'],
    queryFn: ({ signal }) => unitsApi.list(false, signal),
  });
  const shiftsQuery = useQuery({
    queryKey: ['shifts', 'active'],
    queryFn: ({ signal }) => shiftsApi.list(false, signal),
  });
  const saveMutation = useMutation({
    mutationFn: async (input: {
      userId?: string;
      data: CreateUserRequest | UpdateUserRequest;
    }) => {
      if (input.userId !== undefined) {
        return usersApi.update(input.userId, input.data as UpdateUserRequest);
      }
      return usersApi.create(input.data as CreateUserRequest);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: (userId: string) => usersApi.delete(userId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
  const users = usersQuery.data;
  const isSubmitting = saveMutation.isPending || deleteMutation.isPending;
  const actionError = deleteMutation.error;

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleCreate = () => {
    setSelectedUser(null);
    setIsFormOpen(true);
  };

  const handleEdit = (user: User) => {
    setSelectedUser(user);
    setIsFormOpen(true);
  };

  const handleDelete = (user: User) => {
    setSelectedUser(user);
    setIsDeleteOpen(true);
  };

  const handleEnrollFace = (user: User) => {
    setSelectedUser(user);
    setIsEnrollOpen(true);
  };

  const handleFormSubmit = async (data: CreateUserRequest | UpdateUserRequest) => {
    await saveMutation.mutateAsync({
      userId: selectedUser?.id,
      data,
    });
    setIsFormOpen(false);
  };

  const handleConfirmDelete = () => {
    if (selectedUser === null) {
      return;
    }
    deleteMutation.mutate(selectedUser.id, {
      onSuccess: () => setIsDeleteOpen(false),
    });
  };

  return (
    <>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{t('Users')}</h1>
            <p className="text-gray-500 mt-1">{t('Manage user accounts and face enrollments')}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button
              variant="secondary"
              leftIcon={<ArrowUpTrayIcon className="h-5 w-5" aria-hidden="true" />}
              onClick={() => setIsImportOpen(true)}
            >
              {t('Import People')}
            </Button>
            <Button
              leftIcon={<PlusIcon className="h-5 w-5" aria-hidden="true" />}
              onClick={handleCreate}
            >
              {t('Add User')}
            </Button>
          </div>
        </div>

        {actionError !== null && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-700" role="alert">
            {t(actionError.message)}
          </div>
        )}

        {/* Search and Filters */}
        <Card padding="sm">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <Input
                  type="search"
                  placeholder={t('Search users...')}
                  value={search}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Users Table */}
        <Card>
          {usersQuery.isPending ? (
            <div className="py-12">
              <Loading size="lg" text={t('Loading users...')} />
            </div>
          ) : usersQuery.error !== null ? (
            <div className="p-6 text-center text-red-700" role="alert">
              <p>{t(usersQuery.error.message)}</p>
              <Button
                variant="secondary"
                className="mt-4"
                onClick={() => void usersQuery.refetch()}
              >
                {t('Try again')}
              </Button>
            </div>
          ) : (
            <>
              <UserTable
                users={users?.items || []}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onEnrollFace={handleEnrollFace}
                canManageElevatedUsers={canManageElevatedUsers}
              />

              {/* Pagination */}
              {users && users.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                  <p className="text-sm text-gray-500">
                    {t('Page')} {users.page} {t('of')} {users.pages} ({users.total} {t('users')})
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                    >
                      {t('Previous')}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page === users.pages}
                    >
                      {t('Next')}
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </Card>
      </div>

      {/* User Form Modal */}
      <Modal
        isOpen={isFormOpen}
        onClose={() => setIsFormOpen(false)}
        title={selectedUser ? t('Edit User') : t('Create User')}
        size="lg"
      >
        <UserForm
          user={selectedUser || undefined}
          canAssignElevatedRoles={canManageElevatedUsers}
          units={unitsQuery.data ?? []}
          shifts={shiftsQuery.data ?? []}
          onSubmit={handleFormSubmit}
          onCancel={() => setIsFormOpen(false)}
          isLoading={isSubmitting}
        />
        {selectedUser && (
          <UserAssignmentsPanel
            user={selectedUser}
            units={unitsQuery.data ?? []}
            shifts={shiftsQuery.data ?? []}
            canManageScopes={canManageElevatedUsers}
            onUpdated={() => void queryClient.invalidateQueries({ queryKey: ['users'] })}
          />
        )}
      </Modal>

      {/* Delete Confirmation */}
      <ConfirmModal
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        onConfirm={handleConfirmDelete}
        title={t('Delete User')}
        message={t('Are you sure you want to delete {{name}}? This action cannot be undone.', { name: selectedUser?.name })}
        confirmText={t('Delete')}
        variant="danger"
        isLoading={isSubmitting}
      />

      {/* Face Enrollment Modal */}
      <EnrollmentModal
        isOpen={isEnrollOpen}
        onClose={() => setIsEnrollOpen(false)}
        user={selectedUser}
        onSuccess={() => void queryClient.invalidateQueries({ queryKey: ['users'] })}
      />

      <UserImportModal
        isOpen={isImportOpen}
        onClose={() => setIsImportOpen(false)}
        onSuccess={() => void queryClient.invalidateQueries({ queryKey: ['users'] })}
      />
    </>
  );
}

export default UsersPage;
