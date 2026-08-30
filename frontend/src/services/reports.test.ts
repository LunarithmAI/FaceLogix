import type { AxiosAdapter, AxiosResponse } from 'axios';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '@/services/api';
import { reportsApi } from '@/services/reports';

describe('attendance request serialization', () => {
  const originalAdapter = api.defaults.adapter;

  afterEach(() => {
    api.defaults.adapter = originalAdapter;
    vi.restoreAllMocks();
  });

  it('uses the canonical attendance filter names', async () => {
    let capturedUrl: string | undefined;
    let capturedParams: unknown;
    const adapter: AxiosAdapter = (config) => {
      capturedUrl = config.url;
      capturedParams = config.params;
      const result: AxiosResponse = {
        config,
        data: { items: [], total: 0, page: 1, page_size: 20, pages: 0 },
        headers: {},
        status: 200,
        statusText: 'OK',
      };
      return Promise.resolve(result);
    };
    api.defaults.adapter = adapter;

    await reportsApi.getAttendanceLogs({
      from_date: '2026-08-01',
      to_date: '2026-08-30',
      type: 'check_in',
      page: 1,
      page_size: 20,
    });

    expect(capturedUrl).toBe('/attendance');
    expect(capturedParams).toEqual({
      from_date: '2026-08-01',
      to_date: '2026-08-30',
      type: 'check_in',
      page: 1,
      page_size: 20,
    });
    expect(capturedParams).not.toHaveProperty('start_date');
    expect(capturedParams).not.toHaveProperty('end_date');
  });
});
