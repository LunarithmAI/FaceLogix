import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { DashboardPage } from '@/pages/DashboardPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { reportsApi } from '@/services/reports';
import { settingsApi } from '@/services/settings';
import { useAuthStore } from '@/stores/authStore';

vi.mock('@/services/reports', () => ({
  reportsApi: { getDashboardStats: vi.fn() },
}));
vi.mock('@/services/settings', () => ({
  settingsApi: {
    getOrgSettings: vi.fn(),
    getSystemInfo: vi.fn(),
    updateOrgSettings: vi.fn(),
    testFaceService: vi.fn(),
  },
}));

function renderWithQueries(element: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{element}</QueryClientProvider>);
}

describe('server-state pages', () => {
  afterEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().reset();
  });

  it('renders a finite zero attendance percentage', async () => {
    vi.mocked(reportsApi).getDashboardStats.mockResolvedValue({
      total_users: 0,
      active_devices: 0,
      pending_enrollments: 0,
      recent_activity: [],
      today: {
        date: '2026-08-30',
        total_employees: 0,
        checked_in: 0,
        checked_out: 0,
        on_time: 0,
        late_arrivals: 0,
        absent: 0,
        average_check_in_time: null,
        average_check_out_time: null,
      },
    });

    renderWithQueries(<DashboardPage />);

    expect(await screen.findByText('0%')).toBeInTheDocument();
    expect(screen.queryByText(/NaN|Infinity/)).not.toBeInTheDocument();
  });

  it('renders explicit dashboard read errors', async () => {
    vi.mocked(reportsApi).getDashboardStats.mockRejectedValue(new Error('Dashboard unavailable'));

    renderWithQueries(<DashboardPage />);

    expect(await screen.findByText('Dashboard unavailable')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('makes manager organization settings read-only', async () => {
    useAuthStore.setState({
      session: {
        kind: 'user',
        user: {
          id: 'manager-id',
          org_id: 'org-id',
          name: 'Manager',
          role: 'manager',
        },
        tokens: {
          access_token: 'access',
          refresh_token: 'refresh',
          token_type: 'bearer',
        },
      },
    });
    vi.mocked(settingsApi).getOrgSettings.mockResolvedValue({
      id: 'org-id',
      name: 'Example Org',
      slug: 'example',
      timezone: 'UTC',
      is_active: true,
      settings: {
        require_liveness: true,
        liveness_threshold: 0.8,
        face_match_threshold: 0.75,
      },
      created_at: '2026-08-01T00:00:00Z',
      updated_at: '2026-08-30T00:00:00Z',
    });
    vi.mocked(settingsApi).getSystemInfo.mockResolvedValue({
      version: '1.0.0',
      environment: 'test',
      face_service_status: 'online',
      database_status: 'connected',
      total_users: 0,
      total_devices: 0,
      uptime_hours: 0,
    });

    renderWithQueries(<SettingsPage />);

    const threshold = await screen.findByLabelText('Liveness Threshold (80%)');
    expect(threshold).toHaveValue('0.8');
    expect(threshold).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Save Changes' })).not.toBeInTheDocument();
  });
});
