import { useState, useEffect, useCallback } from 'react';
import { PlusIcon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal, ConfirmModal } from '@/components/ui/Modal';
import { UserTable } from '@/components/admin/UserTable';
import { UserForm } from '@/components/admin/UserForm';
import { EnrollmentModal } from '@/components/admin/EnrollmentModal';
import { Loading } from '@/components/ui/Loading';
import { usersApi } from '@/services/users';
import type { User, CreateUserRequest, UpdateUserRequest, UserListResponse } from '@/types/user';

export function UsersPage() {
  const [users, setUsers] = useState<UserListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  // Modal states
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [isEnrollOpen, setIsEnrollOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadUsers = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await usersApi.list({ page, search, limit: 10 });
      setUsers(data);
    } catch (error) {
      console.error('Failed to load users:', error);
    } finally {
      setIsLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

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
    setIsSubmitting(true);
    try {
      if (selectedUser) {
        await usersApi.update(selectedUser.id, data as UpdateUserRequest);
      } else {
        await usersApi.create(data as CreateUserRequest);
      }
      setIsFormOpen(false);
      loadUsers();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!selectedUser) return;
    setIsSubmitting(true);
    try {
      await usersApi.delete(selectedUser.id);
      setIsDeleteOpen(false);
      loadUsers();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Users</h1>
            <p className="text-gray-500 mt-1">Manage user accounts and face enrollments</p>
          </div>
          <Button leftIcon={<PlusIcon className="w-5 h-5" />} onClick={handleCreate}>
            Add User
          </Button>
        </div>

        {/* Search and Filters */}
        <Card padding="sm">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <Input
                  type="search"
                  placeholder="Search users..."
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
          {isLoading ? (
            <div className="py-12">
              <Loading size="lg" text="Loading users..." />
            </div>
          ) : (
            <>
              <UserTable
                users={users?.items || []}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onEnrollFace={handleEnrollFace}
              />

              {/* Pagination */}
              {users && users.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
                  <p className="text-sm text-gray-500">
                    Page {users.page} of {users.pages} ({users.total} users)
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page === users.pages}
                    >
                      Next
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
        title={selectedUser ? 'Edit User' : 'Create User'}
        size="lg"
      >
        <UserForm
          user={selectedUser || undefined}
          onSubmit={handleFormSubmit}
          onCancel={() => setIsFormOpen(false)}
          isLoading={isSubmitting}
        />
      </Modal>

      {/* Delete Confirmation */}
      <ConfirmModal
        isOpen={isDeleteOpen}
        onClose={() => setIsDeleteOpen(false)}
        onConfirm={handleConfirmDelete}
        title="Delete User"
        message={`Are you sure you want to delete ${selectedUser?.full_name}? This action cannot be undone.`}
        confirmText="Delete"
        variant="danger"
        isLoading={isSubmitting}
      />

      {/* Face Enrollment Modal */}
      <EnrollmentModal
        isOpen={isEnrollOpen}
        onClose={() => setIsEnrollOpen(false)}
        user={selectedUser}
        onSuccess={loadUsers}
      />
    </>
  );
}

export default UsersPage;
