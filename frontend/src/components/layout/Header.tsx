import type { RefObject } from 'react';
import { useNavigate } from 'react-router';
import {
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  ChevronDownIcon,
  Cog6ToothIcon,
  UserCircleIcon,
} from '@heroicons/react/24/outline';
import { DisclosureMenu } from '@/components/ui/DisclosureMenu';
import { useAuthStore } from '@/stores/authStore';
import { LanguageSwitcher } from '@/components/ui/LanguageSwitcher';
import { translate as t } from '@/i18n';

interface HeaderProps {
  onOpenSidebar: () => void;
  menuButtonRef: RefObject<HTMLButtonElement | null>;
}

const menuItemClass =
  'flex min-h-11 w-full items-center px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 focus-visible:outline-none focus-visible:bg-gray-50';

export function Header({ onOpenSidebar, menuButtonRef }: HeaderProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    void navigate('/login');
  };

  return (
    <header className="sticky top-0 z-30 border-b border-gray-200 bg-white">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6">
        <button
          ref={menuButtonRef}
          type="button"
          onClick={onOpenSidebar}
          className="flex min-h-11 min-w-11 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 lg:hidden"
          aria-label={t('Open navigation')}
          aria-controls="mobile-navigation"
        >
          <Bars3Icon className="h-6 w-6" aria-hidden="true" />
        </button>

        <div className="ml-auto flex items-center gap-2">
          <LanguageSwitcher compact />
          <DisclosureMenu
            label={t('Open account menu')}
            width={224}
            triggerClassName="flex items-center gap-3 px-2 text-left transition-colors hover:bg-gray-100 motion-reduce:transition-none"
            trigger={
              <>
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-100 text-sm font-medium text-primary-700">
                  {user?.name.charAt(0) ?? 'U'}
                </span>
                <span className="hidden sm:block">
                  <span className="block text-sm font-medium text-gray-900">{user?.name}</span>
                  <span className="block text-xs capitalize text-gray-500">
                    {user === null ? '' : t(user.role)}
                  </span>
                </span>
                <ChevronDownIcon className="h-4 w-4 text-gray-400" aria-hidden="true" />
              </>
            }
          >
            {(close) => (
              <>
                <div className="border-b border-gray-100 px-4 py-3">
                  <p className="text-sm font-medium text-gray-900">{user?.name}</p>
                  <p className="truncate text-sm text-gray-500">{user?.email ?? t('No email')}</p>
                </div>
                <button
                  type="button"
                  role="menuitem"
                  className={menuItemClass}
                  onClick={() => {
                    close();
                    void navigate('/admin/profile');
                  }}
                >
                  <UserCircleIcon className="mr-3 h-5 w-5 text-gray-400" aria-hidden="true" />
                  {t('Your Profile')}
                </button>
                <button
                  type="button"
                  role="menuitem"
                  className={menuItemClass}
                  onClick={() => {
                    close();
                    void navigate('/admin/settings');
                  }}
                >
                  <Cog6ToothIcon className="mr-3 h-5 w-5 text-gray-400" aria-hidden="true" />
                  {t('Settings')}
                </button>
                <div className="my-1 border-t border-gray-100" />
                <button
                  type="button"
                  role="menuitem"
                  className={`${menuItemClass} text-red-600 hover:bg-red-50 focus-visible:bg-red-50`}
                  onClick={() => void handleLogout()}
                >
                  <ArrowRightOnRectangleIcon className="mr-3 h-5 w-5" aria-hidden="true" />
                  {t('Sign out')}
                </button>
              </>
            )}
          </DisclosureMenu>
        </div>
      </div>
    </header>
  );
}

export default Header;
