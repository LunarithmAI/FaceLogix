import { lazy, Suspense } from 'react';
import type { ReactNode } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router';
import { AppLayout } from '@/components/layout/AppLayout';
import { Loading } from '@/components/ui/Loading';
import { CheckInPage } from '@/pages/CheckInPage';
import { LoginPage } from '@/pages/LoginPage';
import { useAuthStore } from '@/stores/authStore';
import { ADMIN_ROLES, OPERATOR_ROLES } from '@/types/roles';
import { translate as t } from '@/i18n';

const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const UsersPage = lazy(() => import('@/pages/UsersPage').then((module) => ({ default: module.UsersPage })));
const UnitsPage = lazy(() => import('@/pages/UnitsPage').then((module) => ({ default: module.UnitsPage })));
const ShiftsPage = lazy(() => import('@/pages/ShiftsPage').then((module) => ({ default: module.ShiftsPage })));
const CalendarPage = lazy(() => import('@/pages/CalendarPage').then((module) => ({ default: module.CalendarPage })));
const DevicesPage = lazy(() => import('@/pages/DevicesPage').then((module) => ({ default: module.DevicesPage })));
const AttendancePage = lazy(() => import('@/pages/AttendancePage').then((module) => ({ default: module.AttendancePage })));
const ReportsPage = lazy(() => import('@/pages/ReportsPage').then((module) => ({ default: module.ReportsPage })));
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then((module) => ({ default: module.SettingsPage })));
const ProfilePage = lazy(() => import('@/pages/ProfilePage').then((module) => ({ default: module.ProfilePage })));

function LoadingPage() {
  return <Loading size="lg" text={t('Loading page...')} />;
}

function HomeRedirect() {
  const session = useAuthStore((state) => state.session);
  if (session === null) return <Navigate to="/login" replace />;
  if (session.kind === 'device') return <Navigate to="/kiosk" replace />;
  return <Navigate to={OPERATOR_ROLES.includes(session.user.role) ? '/admin' : '/profile'} replace />;
}

function PublicRoute({ children }: { children: ReactNode }) {
  const session = useAuthStore((state) => state.session);
  return session === null ? <>{children}</> : <HomeRedirect />;
}

function KioskRoute({ children }: { children: ReactNode }) {
  const session = useAuthStore((state) => state.session);
  const location = useLocation();
  if (session === null) return <Navigate to="/login" state={{ from: location }} replace />;
  if (session.kind !== 'device') return <HomeRedirect />;
  return <>{children}</>;
}

function HumanRoute({ children }: { children: ReactNode }) {
  const session = useAuthStore((state) => state.session);
  const location = useLocation();
  if (session === null) return <Navigate to="/login" state={{ from: location }} replace />;
  if (session.kind !== 'user') return <Navigate to="/kiosk" replace />;
  return <Suspense fallback={<LoadingPage />}>{children}</Suspense>;
}

function OperatorRoute({ children }: { children: ReactNode }) {
  const session = useAuthStore((state) => state.session);
  const location = useLocation();
  if (session === null) return <Navigate to="/login" state={{ from: location }} replace />;
  if (session.kind !== 'user' || !OPERATOR_ROLES.includes(session.user.role)) {
    return <Navigate to="/profile" replace />;
  }
  return <AppLayout><Suspense fallback={<LoadingPage />}>{children}</Suspense></AppLayout>;
}

function AdminRoute({ children }: { children: ReactNode }) {
  const session = useAuthStore((state) => state.session);
  if (session?.kind !== 'user' || !ADMIN_ROLES.includes(session.user.role)) {
    return <HomeRedirect />;
  }
  return <OperatorRoute>{children}</OperatorRoute>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/kiosk" element={<KioskRoute><CheckInPage /></KioskRoute>} />
      <Route path="/profile" element={<HumanRoute><ProfilePage /></HumanRoute>} />
      <Route path="/admin" element={<OperatorRoute><DashboardPage /></OperatorRoute>} />
      <Route path="/admin/users" element={<OperatorRoute><UsersPage /></OperatorRoute>} />
      <Route path="/admin/units" element={<OperatorRoute><UnitsPage /></OperatorRoute>} />
      <Route path="/admin/shifts" element={<OperatorRoute><ShiftsPage /></OperatorRoute>} />
      <Route path="/admin/calendar" element={<OperatorRoute><CalendarPage /></OperatorRoute>} />
      <Route path="/admin/devices" element={<AdminRoute><DevicesPage /></AdminRoute>} />
      <Route path="/admin/attendance" element={<OperatorRoute><AttendancePage /></OperatorRoute>} />
      <Route path="/admin/reports" element={<OperatorRoute><ReportsPage /></OperatorRoute>} />
      <Route path="/admin/settings" element={<AdminRoute><SettingsPage /></AdminRoute>} />
      <Route path="/admin/profile" element={<OperatorRoute><ProfilePage /></OperatorRoute>} />
      <Route path="*" element={<HomeRedirect />} />
    </Routes>
  );
}
