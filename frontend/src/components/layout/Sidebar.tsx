import { useEffect, useRef } from 'react';
import { NavLink } from 'react-router';
import {
  BuildingOffice2Icon,
  CalendarDaysIcon,
  CameraIcon,
  ChartBarIcon,
  ClipboardDocumentListIcon,
  ClockIcon,
  Cog6ToothIcon,
  DeviceTabletIcon,
  HomeIcon,
  UsersIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { translate as t } from '@/i18n';
import { useAuthStore } from '@/stores/authStore';
import { ADMIN_ROLES } from '@/types/roles';

interface NavItem {
  name: string;
  href: string;
  icon: typeof HomeIcon;
  adminOnly?: boolean;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/admin', icon: HomeIcon },
  { name: 'Users', href: '/admin/users', icon: UsersIcon },
  { name: 'Units', href: '/admin/units', icon: BuildingOffice2Icon },
  { name: 'Shifts', href: '/admin/shifts', icon: ClockIcon },
  { name: 'Calendar', href: '/admin/calendar', icon: CalendarDaysIcon },
  { name: 'Devices', href: '/admin/devices', icon: DeviceTabletIcon, adminOnly: true },
  { name: 'Attendance', href: '/admin/attendance', icon: ClipboardDocumentListIcon },
  { name: 'Reports', href: '/admin/reports', icon: ChartBarIcon },
  { name: 'Settings', href: '/admin/settings', icon: Cog6ToothIcon, adminOnly: true },
];

interface SidebarProps {
  isMobileOpen: boolean;
  onClose: () => void;
}

function NavigationContent({ onNavigate }: { onNavigate?: () => void }) {
  const session = useAuthStore((state) => state.session);
  const isAdmin =
    session?.kind === 'user' && ADMIN_ROLES.includes(session.user.role);
  return (
    <>
      <div className="flex h-16 items-center gap-2.5 border-b border-gray-200 px-6">
        <img src="/favicon.svg" alt="" className="h-8 w-8" />
        <span className="text-xl font-bold tracking-tight text-gray-900">FaceLogix</span>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4" aria-label={t('Administration')}>
        {navigation.filter((item) => !item.adminOnly || isAdmin).map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            end={item.href === '/admin'}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex min-h-11 items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 motion-reduce:transition-none ${
                isActive
                  ? 'bg-primary-50 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <item.icon
                  className={`mr-3 h-5 w-5 ${isActive ? 'text-primary-600' : 'text-gray-400'}`}
                  aria-hidden="true"
                />
                {t(item.name)}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-gray-200 p-3">
        <NavLink
          to="/"
          onClick={onNavigate}
          className="flex min-h-11 items-center rounded-lg px-3 py-2.5 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-100 hover:text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 motion-reduce:transition-none"
        >
          <CameraIcon className="mr-3 h-5 w-5 text-gray-400" aria-hidden="true" />
          {t('Check-In Kiosk')}
        </NavLink>
      </div>
    </>
  );
}

export function Sidebar({ isMobileOpen, onClose }: SidebarProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!isMobileOpen) {
      return;
    }
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => closeButtonRef.current?.focus());
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isMobileOpen, onClose]);

  return (
    <>
      <aside className="fixed inset-y-0 hidden w-64 flex-col border-r border-gray-200 bg-white lg:flex">
        <NavigationContent />
      </aside>

      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        id="mobile-navigation"
        aria-label={t('Mobile navigation')}
        aria-hidden={!isMobileOpen}
        inert={!isMobileOpen}
        className={`fixed inset-y-0 left-0 z-50 flex w-64 transform flex-col bg-white shadow-xl transition-transform duration-300 motion-reduce:transition-none lg:hidden ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <button
          ref={closeButtonRef}
          type="button"
          onClick={onClose}
          className="absolute right-2 top-2 flex min-h-11 min-w-11 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
          aria-label={t('Close navigation')}
        >
          <XMarkIcon className="h-6 w-6" aria-hidden="true" />
        </button>
        <NavigationContent onNavigate={onClose} />
      </aside>
    </>
  );
}

export default Sidebar;
