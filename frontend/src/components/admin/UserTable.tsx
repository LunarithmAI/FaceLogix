import {
  PencilIcon,
  TrashIcon,
  FaceSmileIcon,
  EllipsisVerticalIcon,
} from '@heroicons/react/24/outline';
import type { User } from '@/types/user';
import { Badge, RoleBadge, StatusBadge } from '@/components/ui/Badge';
import { formatSmartDate } from '@/utils/date';
import {
  DisclosureMenu,
  disclosureMenuItemClass,
} from '@/components/ui/DisclosureMenu';
import { translate as t } from '@/i18n';

interface UserTableProps {
  users: User[];
  isLoading?: boolean;
  onEdit?: (user: User) => void;
  onDelete?: (user: User) => void;
  onEnrollFace?: (user: User) => void;
  canManageElevatedUsers: boolean;
}

export function UserTable({
  users,
  isLoading = false,
  onEdit,
  onDelete,
  onEnrollFace,
  canManageElevatedUsers,
}: UserTableProps) {

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className="h-16 bg-gray-100 rounded-lg" />
        ))}
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>{t('No users found')}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500" role="region" aria-label={t('Users table')} tabIndex={0}>
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('User')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Role')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Status')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Face Enrolled')}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              {t('Last Activity')}
            </th>
            <th className="relative px-6 py-3">
              <span className="sr-only">{t('Actions')}</span>
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {users.map((user) => (
            <tr key={user.id} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  <div className="w-10 h-10 flex-shrink-0 bg-primary-100 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-primary-700">
                      {user.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div className="ml-4">
                    <div className="text-sm font-medium text-gray-900">
                      {user.name}
                    </div>
                    <div className="text-sm text-gray-500">{user.email || t('No email')}</div>
                  </div>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <RoleBadge role={user.role} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StatusBadge status={user.is_active ? 'active' : 'inactive'} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {user.enrolled_at ? (
                  <Badge variant="success" dot>
                    {t('Enrolled')}
                  </Badge>
                ) : (
                  <Badge variant="warning" dot>
                    {t('Not Enrolled')}
                  </Badge>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {user.enrolled_at ? formatSmartDate(user.enrolled_at) : t('Never')}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                {(canManageElevatedUsers || user.role === 'member') && (
                  <DisclosureMenu
                    label={t('Actions for {{name}}', { name: user.name })}
                    trigger={
                      <EllipsisVerticalIcon
                        className="mx-auto h-5 w-5 text-gray-500"
                        aria-hidden="true"
                      />
                    }
                  >
                    {(close) => (
                      <>
                        <button
                          type="button"
                          role="menuitem"
                          onClick={() => {
                            close();
                            onEdit?.(user);
                          }}
                          className={disclosureMenuItemClass}
                        >
                          <PencilIcon className="mr-3 h-4 w-4" aria-hidden="true" />
                          {t('Edit')}
                        </button>
                        <button
                          type="button"
                          role="menuitem"
                          onClick={() => {
                            close();
                            onEnrollFace?.(user);
                          }}
                          className={disclosureMenuItemClass}
                        >
                          <FaceSmileIcon className="mr-3 h-4 w-4" aria-hidden="true" />
                          {user.enrolled_at ? t('Re-enroll Face') : t('Enroll Face')}
                        </button>
                        <div className="my-1 border-t border-gray-100" />
                        <button
                          type="button"
                          role="menuitem"
                          onClick={() => {
                            close();
                            onDelete?.(user);
                          }}
                          className={`${disclosureMenuItemClass} text-red-600 hover:bg-red-50 focus-visible:bg-red-50`}
                        >
                          <TrashIcon className="mr-3 h-4 w-4" aria-hidden="true" />
                          {t('Delete')}
                        </button>
                      </>
                    )}
                  </DisclosureMenu>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default UserTable;
