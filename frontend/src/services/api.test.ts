import axios, { AxiosError } from 'axios';
import type { AxiosAdapter, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '@/services/api';
import { ApiClientError, normalizeApiError } from '@/services/apiError';
import { useAuthStore } from '@/stores/authStore';

function response<T>(
  config: InternalAxiosRequestConfig,
  status: number,
  data: T
): AxiosResponse<T> {
  return {
    config,
    data,
    headers: {},
    status,
    statusText: status === 200 ? 'OK' : 'Unauthorized',
  };
}

describe('API client', () => {
  const originalApiAdapter = api.defaults.adapter;
  const originalAxiosAdapter = axios.defaults.adapter;

  afterEach(() => {
    api.defaults.adapter = originalApiAdapter;
    axios.defaults.adapter = originalAxiosAdapter;
    useAuthStore.getState().reset();
    vi.restoreAllMocks();
  });

  it('normalizes typed FastAPI detail responses', () => {
    const config = { headers: {} } as InternalAxiosRequestConfig;
    const backendResponse = response(config, 422, {
      detail: {
        code: 'INVALID_CAPTURE',
        message: 'Capture is not usable',
        details: { reason: 'blur' },
      },
    });
    const error = new AxiosError(
      'Request failed',
      'ERR_BAD_REQUEST',
      config,
      undefined,
      backendResponse
    );

    expect(normalizeApiError(error)).toEqual(
      new ApiClientError('Capture is not usable', 422, 'INVALID_CAPTURE', {
        reason: 'blur',
      })
    );
  });

  it('serializes concurrent refreshes and retries each request once', async () => {
    useAuthStore.setState({
      tokens: {
        access_token: 'expired-access',
        refresh_token: 'valid-refresh',
        token_type: 'bearer',
      },
      isAuthenticated: true,
    });
    let refreshCount = 0;
    let protectedCount = 0;

    const refreshAdapter: AxiosAdapter = async (config) => {
      refreshCount += 1;
      await Promise.resolve();
      return response(config, 200, {
        access_token: 'fresh-access',
        token_type: 'bearer',
      });
    };
    axios.defaults.adapter = refreshAdapter;
    const protectedAdapter: AxiosAdapter = (config) => {
      protectedCount += 1;
      if (config.headers.Authorization !== 'Bearer fresh-access') {
        const unauthorized = response(config, 401, { detail: 'Expired token' });
        throw new AxiosError(
          'Request failed with status code 401',
          'ERR_BAD_REQUEST',
          config,
          undefined,
          unauthorized
        );
      }
      return Promise.resolve(response(config, 200, { ok: true }));
    };
    api.defaults.adapter = protectedAdapter;

    const results = await Promise.all([
      api.get<{ ok: boolean }>('/first'),
      api.get<{ ok: boolean }>('/second'),
    ]);

    expect(results.map((result) => result.data)).toEqual([{ ok: true }, { ok: true }]);
    expect(refreshCount).toBe(1);
    expect(protectedCount).toBe(4);
    expect(useAuthStore.getState().tokens?.access_token).toBe('fresh-access');
  });
});
